from collections import defaultdict

import syntropy_sdk as sdk
from syntropy_sdk import models
from syntropy_sdk.utils import MAX_QUERY_FIELD_SIZE

from syntropynac import fields, transform
from syntropynac.fields import ConfigFields, PeerState, PeerType, Topology


def get_agents_connections(api, agents):
    ids = list(agents.keys())
    connections = (
        sdk.ConnectionsApi(api)
        .v1_network_connections_search(
            body=models.V1NetworkConnectionsSearchRequest(
                filter=models.V1ConnectionFilter(agent_id=ids),
            ),
        )
        .to_dict()["data"]
    )
    return connections


def export_connections(api, all_agents, network, net_agents, connections, topology):
    topology = Topology.P2M if not topology else topology.upper()
    ids = [connection["agent_connection_group_id"] for connection in connections]
    if ids:
        connections_services = sdk.utils.BatchedRequestFilter(
            sdk.ConnectionsApi(api).v1_network_connections_services_get,
            MAX_QUERY_FIELD_SIZE,
        )(filter=ids, _preload_content=False)["data"]

        connection_services = {
            connection["agent_connection_group_id"]: connection
            for connection in connections_services
        }
    net_connections = [
        {
            **connection,
            "agent_connection_services": connection_services.get(
                connection["agent_connection_group_id"], {}
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
        agents_services = sdk.utils.BatchedRequestFilter(
            sdk.AgentsApi(api).v1_network_agents_services_get,
            MAX_QUERY_FIELD_SIZE,
        )(filter=unused_endpoints, _preload_content=False)["data"]

        agent_services = defaultdict(list)
        for agent_id, agent in zip(unused_endpoints, agents_services):
            id = (
                agent["agent_id"]
                if "agent_id" in agent and agent["agent_id"]
                else agent_id
            )
            agent_services[id].append(agent)

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


def export_network(api, all_agents, topology):
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
    net = {
        ConfigFields.TOPOLOGY: Topology.P2M,
        ConfigFields.STATE: PeerState.PRESENT,
    }

    connections = get_agents_connections(api, all_agents)

    net_agents = [agent["agent_id"] for _, agent in all_agents.items()]

    return export_connections(api, all_agents, net, net_agents, connections, topology)
