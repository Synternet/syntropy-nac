from collections import defaultdict

import click
import syntropy_sdk as sdk

from syntropynac.exceptions import ConfigureNetworkError
from syntropynac.fields import ConfigFields, PeerState, PeerType, Topology


def get_enabled_connection_subnets(connection):
    """Retrieve configured as enabled subnets for given connection.

    Args:
        connection (dict): A connection object that has agent_connection_services injected.

    Returns:
        set: A set of enabled agent service subnet ids
    """
    return {
        subnet["agent_service_subnet_id"]
        for subnet in connection.get("agent_connection_services", {}).get(
            "agent_connection_subnets", []
        )
        if subnet["agent_connection_subnet_is_enabled"]
    }


def transform_connection_agent_services(enabled_subnets, agent_ref, connection):
    """Transforms enabled connection service subnets to a set of service names.

    Args:
        enabled_subnets (iterable): A set of enabled subnets for the given connection.
        agent_ref (str): One of "agent_1" or "agent_2".
        connection (dict): A connection object that has agent_connection_services injected.

    Returns:
        set: A set of enabled agent service names
    """
    return {
        service["agent_service_name"]
        for service in connection.get("agent_connection_services", {})
        .get(agent_ref, {})
        .get("agent_services", [])
        if any(
            subnet["agent_service_subnet_id"] in enabled_subnets
            for subnet in service["agent_service_subnets"]
        )
    }


def transform_connection_services(connection):
    """Retrieve enabled service names for each agent in the connection.

    Args:
        connection (dict): A connection object that has agent_connection_services injected.

    Returns:
        tuple: A tuple consisting of two elements, where the first one corresponds to
            agent_1 and the second one to agent_2.
    """
    enabled_subnets = get_enabled_connection_subnets(connection)
    return (
        transform_connection_agent_services(enabled_subnets, "agent_1", connection),
        transform_connection_agent_services(enabled_subnets, "agent_2", connection),
    )


def transform_p2p_connections(
    all_agents, connections, reference=None, group_tags=False
):
    """Transforms connections assuming One to One topology(Point to Point).

    Args:
        connections (List[AgentConnectionObject]): A list of connections that are assigned to the provided network.
        reference (dict): A dictionary describing reference connections configuration.

    Returns:
        dict: A dictionary with keys as endpoints and values as dicts explaining the endpoint(state, type).
    """
    transformed_connections = {}
    for connection in connections:
        agent_1, agent_2 = connection["agent_1"], connection["agent_2"]
        agent_1_services, agent_2_services = transform_connection_services(connection)
        agent_1_name = agent_1["agent_name"]
        agent_1_type = PeerType.ENDPOINT
        # We must swap A and B agents if we have already made a connection from A->*
        # so that it would be B->A.
        if agent_1["agent_name"] in transformed_connections:
            agent_1, agent_2 = agent_2, agent_1
            agent_1_name = agent_1["agent_name"]
            agent_1_services, agent_2_services = agent_2_services, agent_1_services
        # Fallback to id instead of name if we already have B->*
        if agent_1_name in transformed_connections:
            agent_1_name = agent_1["agent_id"]
            agent_1_type = PeerType.ID
        # Try second agent id instead
        if agent_1_name in transformed_connections:
            agent_1, agent_2 = agent_2, agent_1
            agent_1_services, agent_2_services = agent_2_services, agent_1_services
            agent_1_name = agent_1["agent_id"]
        # Sadly we're out of options here even though it shouldn't happen
        if agent_1_name in transformed_connections:
            click.secho(
                (
                    f"Could not represent connections from {agent_1['agent_name']} to {agent_2['agent_name']} "
                    f"using P2P topology. Consider overriding to P2M or MESH."
                ),
                err=True,
                fg="yellow",
            )
            continue

        transformed_connections[agent_1_name] = {
            ConfigFields.ID: agent_1["agent_id"],
            ConfigFields.PEER_TYPE: agent_1_type,
            ConfigFields.STATE: PeerState.PRESENT,
            ConfigFields.SERVICES: list(agent_1_services),
            ConfigFields.CONNECT_TO: {
                agent_2["agent_name"]: {
                    ConfigFields.ID: agent_2["agent_id"],
                    ConfigFields.PEER_TYPE: PeerType.ENDPOINT,
                    ConfigFields.SERVICES: list(agent_2_services),
                }
            },
        }
    return transformed_connections


def _group_agents_by_tags(agents):
    """A helper method to group agents by tags. Will return a dictionary of tag id as keys and a set of agent ids.

    Args:
        agents (dict): A dictionary containing agents as {agent_id: agent, ...}

    Returns:
        dict: A dictionary containing agents grouped by tags as {tag_name: set(agent_ids)}
    """
    tags = defaultdict(list)
    # Group agents by tags.
    for _, agent in agents.items():
        agent_tags = agent.get("agent_tags", [])
        for tag in agent_tags:
            tags[tag["agent_tag_name"]].append(agent["agent_id"])
        if not agent_tags:
            tags[None].append(agent["agent_id"])

    return {tag: set(agent_ids) for tag, agent_ids in tags.items()}


def group_agents_by_tags(agents, endpoints):
    """Will group endpoints using the same tag and returns the group.

    Args:
        agents (List[AgentConnectionObject]): A list of all agents.
        endpoints (dict): Endpoints configured for a network.

    Returns:
        dict: A dictionary with keys as endpoints and values as dicts explaining the endpoint(state, type).
    """
    tags = _group_agents_by_tags(agents)
    endpoint_tags = _group_agents_by_tags(
        {
            endpoint[ConfigFields.ID]: agents[endpoint[ConfigFields.ID]]
            for endpoint in endpoints.values()
        }
    )
    services = {
        endpoint[ConfigFields.ID]: endpoint.get(ConfigFields.SERVICES, [])
        for endpoint in endpoints.values()
    }

    grouped_endpoints = {}
    # Create a new dictionary with tags
    for tag, endpoints in endpoint_tags.items():
        if tag is None or tags[tag] != endpoints:
            grouped_endpoints.update(
                {
                    agents[endpoint_id]["agent_name"]: {
                        ConfigFields.PEER_TYPE: PeerType.ENDPOINT,
                        ConfigFields.ID: endpoint_id,
                        ConfigFields.STATE: PeerState.PRESENT,
                        ConfigFields.SERVICES: services[endpoint_id],
                    }
                    for endpoint_id in endpoints
                }
            )
        elif tags[tag] == endpoints:
            grouped_endpoints[tag] = {
                ConfigFields.PEER_TYPE: PeerType.TAG,
                ConfigFields.STATE: PeerState.PRESENT,
                ConfigFields.SERVICES: list(
                    set(sum((services[endpoint_id] for endpoint_id in endpoints), []))
                ),
            }

    # Cleanup endpoints that fall into any tags
    result = {
        name: endpoint
        for name, endpoint in grouped_endpoints.items()
        if endpoint[ConfigFields.PEER_TYPE] == PeerType.TAG
        or not any(
            endpoint[ConfigFields.ID] in endpoint_tags[tag]
            for tag, _endpoint in grouped_endpoints.items()
            if _endpoint[ConfigFields.PEER_TYPE] == PeerType.TAG
        )
    }

    return result


def transform_p2m_connections(all_agents, connections, reference=None, group_tags=True):
    """Transforms connections assuming One to many topology(Point to Multipoint). Also, groups agents by tags.

    Args:
        connections (List[AgentConnectionObject]): A list of connections that are assigned to the provided network.
        reference (dict): A dictionary describing reference connections configuration.

    Returns:
        dict: A dictionary with keys as endpoints and values as dicts explaining the endpoint(state, type).
    """
    transformed_connections = {}
    agent_links = defaultdict(dict)
    agents = {}
    services = {}
    # First make agent_id->agent and link->services maps, so that we could
    # find them faster.
    for connection in connections:
        agent_1, agent_2 = connection["agent_1"], connection["agent_2"]
        # We need to map connections in both ways, since it can be either
        # A->Many or Many->A as we get it from the API.
        agents[agent_1["agent_id"]], agents[agent_2["agent_id"]] = agent_1, agent_2
        agent_links[agent_1["agent_id"]][agent_2["agent_id"]] = True
        agent_links[agent_2["agent_id"]][agent_1["agent_id"]] = True
        transformed_services = transform_connection_services(connection)
        services[(agent_1["agent_id"], agent_2["agent_id"])] = transformed_services
        services[(agent_2["agent_id"], agent_1["agent_id"])] = transformed_services[
            ::-1
        ]

    for src, dst in agent_links.items():
        # NOTE: We expect 1 agent to have connections to N other agents, however,
        # sometimes we have N agents that connect to 1 agent, so we have to filter those out.
        dst_first_key = list(dst.keys())[0]
        if (
            len(dst) == 1
            and dst_first_key in agent_links
            and len(agent_links[dst_first_key]) > 1
        ):
            continue
        agent_1 = agents[src]

        connect_to = {
            agent["agent_name"]: {
                ConfigFields.ID: agent["agent_id"],
                ConfigFields.PEER_TYPE: PeerType.ENDPOINT,
                ConfigFields.STATE: PeerState.PRESENT,
                ConfigFields.SERVICES: list(
                    services[(agent_1["agent_id"], agent["agent_id"])][1]
                ),
            }
            for agent in (agents[i] for i in dst.keys())
        }
        agent_services = set()
        for agent in (agents[i] for i in dst.keys()):
            agent_services.update(services[(agent_1["agent_id"], agent["agent_id"])][0])
        # NOTE: This place might be problematic since it will overwrite
        # A->Many if we have OtherMany->A... However, the first if in this loop
        # should filter out these cases.
        transformed_connections[agent_1["agent_name"]] = {
            ConfigFields.ID: agent_1["agent_id"],
            ConfigFields.PEER_TYPE: PeerType.ENDPOINT,
            ConfigFields.STATE: PeerState.PRESENT,
            ConfigFields.SERVICES: list(agent_services),
            ConfigFields.CONNECT_TO: group_agents_by_tags(all_agents, connect_to)
            if group_tags
            else connect_to,
        }
    return transformed_connections


def transform_mesh_connections(
    all_agents, connections, reference=None, group_tags=True
):
    """Transforms connections assuming MESH topology. Also, groups agents by tags.

    NOTE: Even though some connections are missing, this method assumes that every
    endpoint is connected to every other endpoint.

    Args:
        connections (List[AgentConnectionObject]): A list of connections that are assigned to a network.
        reference (dict): A dictionary describing reference connections configuration.

    Returns:
        dict: A dictionary with keys as endpoints and values as dicts explaining the endpoint(state, type).
    """
    transformed_connections = {}
    agents = {}
    services = defaultdict(set)
    for connection in connections:
        agent_1, agent_2 = connection["agent_1"], connection["agent_2"]
        agents[agent_1["agent_id"]], agents[agent_2["agent_id"]] = agent_1, agent_2
        agent_1_services, agent_2_services = transform_connection_services(connection)
        services[agent_1["agent_id"]].update(agent_1_services)
        services[agent_2["agent_id"]].update(agent_2_services)

    # NOTE: Assumes that all peers are interconnected. Will result in all peers being interconnected
    # if we apply the resulting configuration export.
    # Also, it will enable all services for a given endpoint for all connections even if
    # those services are partially enabled to some other endpoints.
    for id, agent in agents.items():
        transformed_connections[agent["agent_name"]] = {
            ConfigFields.ID: id,
            ConfigFields.PEER_TYPE: PeerType.ENDPOINT,
            ConfigFields.STATE: PeerState.PRESENT,
            ConfigFields.SERVICES: list(services[id]),
        }
    return (
        group_agents_by_tags(all_agents, transformed_connections)
        if group_tags
        else transformed_connections
    )


def transform_connections(
    all_agents, connections, topology, reference=None, group_tags=True, silent=False
):
    """Transform Platform's NetworkObject into internal representation that is being used for export and configuration.

    Args:
        connections (List[AgentConnectionObject]): A list of connections that are assigned to the provided network.
        topology (str): Network topology to assume while transforming connections.
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.

    Raises:
        ConfigureNetworkError: In case of any errors.

    Returns:
        dict: Returns a dictionary that can be used for network export and/or configuration.
    """
    topology_map = {
        Topology.P2P: transform_p2p_connections,
        Topology.P2M: transform_p2m_connections,
        Topology.MESH: transform_mesh_connections,
    }
    if topology not in topology_map:
        error = f"Network topology {topology} not supported. Skipping."
        if not silent:
            click.secho(error, err=True, fg="yellow")
        else:
            raise ConfigureNetworkError(error)
        return
    return topology_map[topology](
        all_agents, connections, reference=reference, group_tags=group_tags
    )
