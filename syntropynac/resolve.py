import functools
from dataclasses import dataclass
from itertools import combinations

import click
from syntropy_sdk import utils

from syntropynac.exceptions import ConfigureNetworkError
from syntropynac.fields import ConfigFields, PeerState, PeerType


@dataclass
class ConnectionServices:
    agent_1: int
    agent_2: int
    agent_1_service_names: list
    agent_2_service_names: list

    @classmethod
    def create(cls, link, endpoints):
        endpoint_1, endpoint_2 = endpoints
        return cls(
            link[0],
            link[1],
            cls._get_services(endpoint_1),
            cls._get_services(endpoint_2),
        )

    @staticmethod
    def _get_services(endpoint):
        service_names = endpoint[1].get(ConfigFields.SERVICES)
        if service_names is None:
            return []
        if isinstance(service_names, str):
            return [service_names]
        if not isinstance(service_names, list) or any(
            not isinstance(name, str) for name in service_names
        ):
            raise ConfigureNetworkError(
                f"Services parameter must be a list of service names for endpoint {endpoint[0]}"
            )
        return service_names

    def get_subnets(self, endpoint_id, agents):
        agent_id = getattr(self, f"agent_{endpoint_id}")
        service_names = getattr(self, f"agent_{endpoint_id}_service_names")
        agent = agents[agent_id]

        return [
            subnet["agent_service_subnet_id"]
            for service in agent["agent_services"]
            for subnet in service["agent_service_subnets"]
            if service["agent_service_name"] in service_names
        ]


@functools.lru_cache(maxsize=None)
def resolve_agent_by_name(api, name, silent=False):
    return [
        agent["agent_id"]
        for agent in utils.WithRetry(api.index_agents)(
            filter=f"id|name:{name}", load_relations=False
        )["data"]
    ]


@functools.lru_cache(maxsize=None)
def get_all_agents(api, silent=False):
    all_agents = utils.WithRetry(api.index_agents)(take=utils.TAKE_MAX_ITEMS_PER_CALL)[
        "data"
    ]
    return {agent["agent_id"]: agent for agent in all_agents}


def resolve_agents(api, agents, silent=False):
    """Resolves endpoint names to ids inplace.

    Args:
        api (PlatformApi): API object to communicate with the platform.
        agents (dict): A dictionary containing endpoints.
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.
    """
    for name, id in agents.items():
        if id is not None:
            continue
        result = resolve_agent_by_name(api, name, silent=silent)
        if len(result) != 1:
            error = f"Could not resolve endpoint name {name}, found: {result}."
            if not silent:
                click.secho(
                    error,
                    err=True,
                    fg="red",
                )
                continue
            else:
                raise ConfigureNetworkError(error)
        agents[name] = result[0]


def get_peer_id(peer_name, peer_config):
    peer_type = peer_config.get(ConfigFields.PEER_TYPE, PeerType.ENDPOINT)
    if peer_type == PeerType.ENDPOINT:
        return peer_config.get(ConfigFields.ID)
    elif peer_type == PeerType.ID:
        try:
            return int(peer_name)
        except ValueError:
            return None
    else:
        return None


def resolve_present_absent(agents, present, absent):
    """Resolves agent connections by objects into agent connections by ids.
    Additionally removes any present connections if they were already added to absent.

    Present connections are the connections that appear as "present" in the config
    and will be added to the network.
    Absent connections are the connections that appear as "absent" in the config and
    will be removed from the existing network.
    Services is a list of service names assigned to the connection's corresponding endpoints.

    Args:
        agents (dict[str, int]): Agent map from name to id.
        present (list): A list of connections that are marked as present in the config.
        absent (list): A list of connections that are marked as absent in the config.

    Returns:
        tuple: Three items that correspond to present/absent connections and a list
            of ConnectionServices objects that correspond to present connections.

            Present/absent connections is a list of lists of two elements, where
            elements are agent ids.
    """
    present_ids = [[agents[src[0]], agents[dst[0]]] for src, dst in present]
    absent_ids = [[agents[src[0]], agents[dst[0]]] for src, dst in absent]
    services = [
        ConnectionServices.create(link, conn)
        for link, conn in zip(present_ids, present)
        if link not in absent_ids and link[::-1] not in absent_ids
    ]
    return (
        [
            link
            for link in present_ids
            if link not in absent_ids and link[::-1] not in absent_ids
        ],
        absent_ids,
        services,
    )


def resolve_p2p_connections(api, connections, silent=False):
    """Resolves configuration connections for Point to Point topology.

    Args:
        api (PlatformApi): API object to communicate with the platform.
        connections (dict): A dictionary containing connections as described in the config file.
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.

    Returns:
        list: A list of two item lists describing endpoint to endpoint connections.
    """
    present = []
    absent = []
    agents = {}

    for src in connections.items():
        dst = src[1].get(ConfigFields.CONNECT_TO)
        if dst is None or len(dst.keys()) == 0:
            continue
        dst = list(dst.items())[0]

        agents[src[0]] = get_peer_id(*src)
        agents[dst[0]] = get_peer_id(*dst)

        if (
            src[1].get(ConfigFields.STATE) == PeerState.ABSENT
            or dst[1].get(ConfigFields.STATE) == PeerState.ABSENT
        ):
            absent.append((src, dst))
        elif (
            src[1].get(ConfigFields.STATE, PeerState.PRESENT) == PeerState.PRESENT
            or dst[1].get(ConfigFields.STATE, PeerState.PRESENT) == PeerState.PRESENT
        ):
            present.append((src, dst))
        else:
            error = f"Invalid state for agents {src[0]} or {dst[0]}"
            if not silent:
                click.secho(error, fg="red", err=True)
            else:
                raise ConfigureNetworkError(error)

    resolve_agents(api, agents, silent=silent)
    if any(id is None for id in agents.keys()):
        return resolve_present_absent({}, [], [])

    return resolve_present_absent(agents, present, absent)


def expand_agents_tags(api, dst_dict, silent=False):
    """Expand tag endpoints into individual endpoints.

    Args:
        api (PlatformApi): API object to communicate with the platform.
        dst_dict ([type]): [description]
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.

    Raises:
        ConfigureNetworkError: In case of any errors

    Returns:
        Union[dict, None]: Dictionary with expanded endpoints where key is the name and value is the config(id, state, type).
    """
    items = {}

    # First expand tags
    for name, dst in dst_dict.items():
        if dst.get(ConfigFields.PEER_TYPE) != PeerType.TAG:
            continue

        agents = utils.WithRetry(api.index_agents)(
            filter=f"tags_names[]:{name}", take=utils.TAKE_MAX_ITEMS_PER_CALL
        )["data"]
        if not agents:
            error = f"Could not find endpoints by the tag {name}"
            if not silent:
                click.secho(error, err=True, fg="red")
                return
            else:
                raise ConfigureNetworkError(error)

        tag_state = dst.get(ConfigFields.STATE, PeerState.PRESENT)
        for agent in agents:
            agent_name = agent["agent_name"]
            if agent_name not in items or (
                tag_state == PeerState.ABSENT
                and items[agent_name][ConfigFields.STATE] == PeerState.PRESENT
            ):
                items[agent_name] = {
                    ConfigFields.ID: agent["agent_id"],
                    ConfigFields.STATE: tag_state,
                    ConfigFields.PEER_TYPE: PeerType.ENDPOINT,
                    ConfigFields.SERVICES: dst.get(ConfigFields.SERVICES),
                }

    # Then override with explicit configs
    for name, dst in dst_dict.items():
        if dst.get(ConfigFields.PEER_TYPE) != PeerType.TAG:
            items[name] = dst
            continue

    return items


def resolve_p2m_connections(api, connections, silent=False):
    """Resolves configuration connections for Point to Multipoint topology. Also, expands tags.

    Args:
        api (PlatformApi): API object to communicate with the platform.
        connections (dict): A dictionary containing connections as described in the config file.
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.

    Returns:
        list: A list of two item lists describing endpoint to endpoint connections.
    """
    present = []
    absent = []
    agents = {}

    for src in connections.items():
        dst_dict = src[1].get(ConfigFields.CONNECT_TO)
        if dst_dict is None or len(dst_dict.keys()) == 0:
            continue
        dst_dict = expand_agents_tags(api, dst_dict)
        if dst_dict is None:
            return resolve_present_absent({}, [], [])

        agents[src[0]] = get_peer_id(*src)
        for dst in dst_dict.items():
            agents[dst[0]] = get_peer_id(*dst)
            if (
                src[1].get(ConfigFields.STATE) == PeerState.ABSENT
                or dst[1].get(ConfigFields.STATE) == PeerState.ABSENT
            ):
                absent.append((src, dst))
            elif (
                src[1].get(ConfigFields.STATE, PeerState.PRESENT) == PeerState.PRESENT
                or dst[1].get(ConfigFields.STATE, PeerState.PRESENT)
                == PeerState.PRESENT
            ):
                present.append((src, dst))
            else:
                error = f"Invalid state for agents {src[0]} or {dst[0]}"
                if not silent:
                    click.secho(error, fg="red", err=True)
                else:
                    raise ConfigureNetworkError(error)

    resolve_agents(api, agents, silent=silent)
    if any(id is None for id in agents.keys()):
        return resolve_present_absent({}, [], [])

    return resolve_present_absent(agents, present, absent)


def resolve_mesh_connections(api, connections, silent=False):
    """Resolves configuration connections for mesh topology. Also, expands tags.

    Args:
        api (PlatformApi): API object to communicate with the platform.
        connections (dict): A dictionary containing connections.
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.

    Returns:
        list: A list of two item lists describing endpoint to endpoint connections.
    """
    present = []
    absent = []

    connections = expand_agents_tags(api, connections)
    if connections is None:
        return resolve_present_absent({}, [], [])

    agents = {
        name: get_peer_id(name, connection) for name, connection in connections.items()
    }

    # NOTE: Assuming connections are bidirectional
    for src, dst in combinations(connections.items(), 2):
        if (
            src[1].get(ConfigFields.STATE) == PeerState.ABSENT
            or dst[1].get(ConfigFields.STATE) == PeerState.ABSENT
        ):
            absent.append((src, dst))
        elif (
            src[1].get(ConfigFields.STATE, PeerState.PRESENT) == PeerState.PRESENT
            or dst[1].get(ConfigFields.STATE, PeerState.PRESENT) == PeerState.PRESENT
        ):
            present.append((src, dst))
        else:
            error = f"Invalid state for agents {src[0]} or {dst[0]}"
            if not silent:
                click.secho(error, fg="red", err=True)
            else:
                raise ConfigureNetworkError(error)

    resolve_agents(api, agents, silent=silent)
    if any(id is None for id in agents.keys()):
        return resolve_present_absent({}, [], [])

    return resolve_present_absent(agents, present, absent)
