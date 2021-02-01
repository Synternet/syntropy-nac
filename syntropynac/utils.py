from collections import defaultdict

import syntropy_sdk as sdk

from syntropynac import fields, transform


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
    connections_filter = f"networks[]:{net['id']}"
    connections = sdk.utils.WithRetry(api.platform_connection_index)(
        filter=connections_filter, take=sdk.utils.TAKE_MAX_ITEMS_PER_CALL
    )["data"]
    ids = [connection["agent_connection_id"] for connection in connections]
    if ids:
        connections_services = sdk.utils.BatchedRequest(
            api.platform_connection_service_show,
            max_payload_size=sdk.utils.MAX_QUERY_FIELD_SIZE,
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
        topology if topology else net[fields.ConfigFields.TOPOLOGY],
    )
    if transformed_connections:
        net[fields.ConfigFields.CONNECTIONS] = transformed_connections
    if topology:
        if net[fields.ConfigFields.TOPOLOGY] != topology:
            net[fields.ConfigFields.IGNORE_NETWORK_TOPOLOGY] = True
        net[fields.ConfigFields.TOPOLOGY] = topology
    del net[fields.ConfigFields.USE_SDN]

    # Filter out unused endpoints
    used_endpoints = [
        con[agent]["agent_id"]
        for con in net_connections
        for agent in ("agent_1", "agent_2")
    ]
    net_endpoints = [
        agent["agent_id"]
        for id, agent in all_agents.items()
        if any(net["network_id"] == network["network_id"] for net in agent["networks"])
    ]
    unused_endpoints = [id for id in net_endpoints if id not in used_endpoints]

    if unused_endpoints:
        agents_services = sdk.utils.BatchedRequest(
            api.platform_agent_service_index,
            max_payload_size=sdk.utils.MAX_QUERY_FIELD_SIZE,
        )(unused_endpoints)["data"]
        agent_services = defaultdict(list)
        for agent in agents_services:
            agent_services[agent["agent_id"]].append(agent)

        net[fields.ConfigFields.ENDPOINTS] = {
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

    return net
