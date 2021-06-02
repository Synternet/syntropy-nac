from collections import defaultdict

import syntropy_sdk as sdk
from syntropy_sdk.utils import MAX_QUERY_FIELD_SIZE

from syntropynac import fields, transform


def get_network_connections(api, network):
    connections_filter = f"networks[]:{network['id']}"
    connections = sdk.utils.WithRetry(api.platform_connection_index)(
        filter=connections_filter, take=sdk.utils.TAKE_MAX_ITEMS_PER_CALL
    )["data"]
    return connections


def get_agents_connections(api, agents):
    ids = list(agents.keys())
    connections = sdk.utils.BatchedRequestFilter(
        api.platform_connection_index,
        max_query_size=MAX_QUERY_FIELD_SIZE,
        filter_name="agent_ids",
        filter_data=ids,
    )(take=sdk.utils.TAKE_MAX_ITEMS_PER_CALL,)["data"]
    return connections


def export_connections(api, all_agents, network, net_agents, connections, topology):
    ids = [connection["agent_connection_id"] for connection in connections]
    if ids:
        connections_services = sdk.utils.BatchedRequestQuery(
            api.platform_connection_service_show,
            max_query_size=sdk.utils.MAX_QUERY_FIELD_SIZE,
        )(ids)["data"]
        connection_services = {
            connection["agent_connection_id"]: connection
            for connection in connections_services
        }
    net_connections = [
        {
            **connection,
            "agent_connection_services": connection_services.get(
                connection["agent_connection_id"], {}
            ),
        }
        for connection in connections
    ]
    transformed_connections = transform.transform_connections(
        all_agents,
        net_connections,
        topology if topology else network[fields.ConfigFields.TOPOLOGY],
    )
    if transformed_connections:
        network[fields.ConfigFields.CONNECTIONS] = transformed_connections
    if topology:
        if network[fields.ConfigFields.TOPOLOGY] != topology:
            network[fields.ConfigFields.IGNORE_NETWORK_TOPOLOGY] = True
        network[fields.ConfigFields.TOPOLOGY] = topology

    # NOTE: Currently, SDN is disabled.
    if fields.ConfigFields.USE_SDN in network:
        del network[fields.ConfigFields.USE_SDN]

    # Filter out unused endpoints
    used_endpoints = [
        con[agent]["agent_id"]
        for con in net_connections
        for agent in ("agent_1", "agent_2")
    ]
    unused_endpoints = [id for id in net_agents if id not in used_endpoints]

    if unused_endpoints:
        agents_services = sdk.utils.BatchedRequestQuery(
            api.platform_agent_service_index,
            max_query_size=sdk.utils.MAX_QUERY_FIELD_SIZE,
        )(unused_endpoints)["data"]
        agent_services = defaultdict(list)
        for agent in agents_services:
            agent_services[agent["agent_id"]].append(agent)

        network[fields.ConfigFields.ENDPOINTS] = {
            all_agents[id]["agent_name"]: {
                fields.ConfigFields.ID: id,
                fields.ConfigFields.SERVICES: [
                    service["agent_service_name"] for service in agent_services[id]
                ],
                fields.ConfigFields.TAGS: [
                    tag["agent_tag_name"]
                    for tag in all_agents[id].get("agent_tags", [])
                ],
            }
            for id in unused_endpoints
        }

    return network


def export_network(api, all_agents, network, topology):
    """Generate a network configuration structure from network and connections either
    using specified topology or inferred topology.
    Currently, default topology is P2M.

    Args:
        api (PlatformApi): Instance of PlatformApi.
        all_agents (dict[int, dict]): A mapping of all user agents ids to agent objects.
        network (dict): A dictionary describing a network to be exported.
        topology (str): One of MetadataNetworkType.

    Returns:
        dict: A network configuration structure.
    """
    net = transform.transform_network(network)

    connections = (
        get_network_connections(api, net)
        if network is not None
        else get_agents_connections(api, all_agents)
    )

    if network is not None:
        net_agents = [
            agent["agent_id"]
            for _, agent in all_agents.items()
            if any(
                agent_net["network_id"] == net[fields.ConfigFields.ID]
                for agent_net in agent["networks"]
            )
        ]
    else:
        net_agents = [agent["agent_id"] for _, agent in all_agents.items()]

    return export_connections(api, all_agents, net, net_agents, connections, topology)
