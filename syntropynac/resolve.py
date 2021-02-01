import functools
from dataclasses import dataclass
from itertools import combinations

import click
from syntropy_sdk import utils

from syntropynac.exceptions import ConfigureNetworkError
from syntropynac.fields import ALLOWED_PEER_TYPES, ConfigFields, PeerState, PeerType


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
        for agent in utils.WithRetry(api.platform_agent_index)(
            filter=f"name:'{name}'", load_relations=False
        )["data"]
    ]


@functools.lru_cache(maxsize=None)
def get_all_agents(api, silent=False):
    all_agents = utils.WithRetry(api.platform_agent_index)(
        take=utils.TAKE_MAX_ITEMS_PER_CALL
    )["data"]
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
        if link not in absent_ids
        and link[::-1] not in absent_ids
        and link[0] != link[1]
    ]
    return (
        [
            link
            for link in present_ids
            if link not in absent_ids
            and link[::-1] not in absent_ids
            and link[0] != link[1]
        ],
        [i for i in absent_ids if i[0] != i[1]],
        services,
    )


def validate_connections(connections, silent=False, level=0):
    """Check if the connections structure makes any sense.
    Recursively goes inside 'connect_to' dictionary up to 1 level.

    Args:
        connections (dict): A dictionary describing connections.
        silent (bool, optional): Indicates whether to suppress output to stderr.
            Raises ConfigureNetworkError instead. Defaults to False.
        level (int, optional): Recursion level depth. Defaults to 0.

    Raises:
        ConfigureNetworkError: If silent==True, then raise an exception in case of irrecoverable error.

    Returns:
        bool: Returns False in case of invalid connections structure.
    """
    if level > 1:
        silent or click.secho(
            (
                f"Field {ConfigFields.CONNECT_TO} found at level {level + 1}. This will be ignored, "
                "however, please double check your configuration file."
            )
        )
        return True

    for name, con in connections.items():
        if not name or not isinstance(name, (str, int)):
            error = f"Invalid endpoint name found."
            if not silent:
                click.secho(error, err=True, fg="red")
                return False
            else:
                raise ConfigureNetworkError(error)

        if not isinstance(con, dict):
            error = f"Entry '{name}' in {ConfigFields.CONNECT_TO} must be a dictionary, but found {con.__class__.__name__}."
            if not silent:
                click.secho(error, err=True, fg="red")
                return False
            else:
                raise ConfigureNetworkError(error)

        if ConfigFields.PEER_TYPE not in con:
            error = f"Endpoint '{name}' {ConfigFields.PEER_TYPE} must be present."
            if not silent:
                click.secho(error, err=True, fg="red")
                return False
            else:
                raise ConfigureNetworkError(error)

        if con[ConfigFields.PEER_TYPE] not in ALLOWED_PEER_TYPES:
            error = f"Endpoint '{name}' {ConfigFields.PEER_TYPE} '{con[ConfigFields.PEER_TYPE]}' is not allowed."
            if not silent:
                click.secho(error, err=True, fg="red")
                return False
            else:
                raise ConfigureNetworkError(error)

        probably_an_id = False
        try:
            name_as_id = int(name)
            probably_an_id = True
        except ValueError:
            name_as_id = name
        if probably_an_id and con[ConfigFields.PEER_TYPE] == PeerType.ENDPOINT:
            click.secho(
                (
                    f"Endpoint '{name}' {ConfigFields.PEER_TYPE} is {PeerType.ENDPOINT}, however, "
                    f"it appears to be an {PeerType.ID}."
                ),
                err=True,
                fg="yellow",
            )
        if not probably_an_id and con[ConfigFields.PEER_TYPE] == PeerType.ID:
            error = (
                f"Endpoint '{name}' {ConfigFields.PEER_TYPE} is {PeerType.ID}, however, "
                f"it appears to be an {PeerType.ENDPOINT}."
            )
            if not silent:
                click.secho(error, err=True, fg="red")
                return False
            else:
                raise ConfigureNetworkError(error)

        if ConfigFields.ID in con and con[ConfigFields.ID] is not None:
            try:
                _ = int(con[ConfigFields.ID])
                id_valid = True
            except ValueError:
                id_valid = False
            if (
                not isinstance(con[ConfigFields.ID], (str, int))
                or not con[ConfigFields.ID]
                or not id_valid
            ):
                error = f"Endpoint '{name}' {ConfigFields.ID} is invalid."
                if not silent:
                    click.secho(error, err=True, fg="red")
                    return False
                else:
                    raise ConfigureNetworkError(error)

            if (
                con[ConfigFields.PEER_TYPE] == PeerType.ID
                and int(con[ConfigFields.ID]) != name_as_id
            ):
                error = f"Endpoint '{name}' {ConfigFields.ID} field does not match endpoint id."
                if not silent:
                    click.secho(error, err=True, fg="red")
                    return False
                else:
                    raise ConfigureNetworkError(error)

        if ConfigFields.SERVICES in con:
            if not isinstance(con[ConfigFields.SERVICES], (list, tuple)):
                error = (
                    f"Endpoint '{name}' {ConfigFields.SERVICES} must be a "
                    f"list, but found {con[ConfigFields.SERVICES].__class__.__name__}."
                )
                if not silent:
                    click.secho(error, err=True, fg="red")
                    return False
                else:
                    raise ConfigureNetworkError(error)

            for service in con[ConfigFields.SERVICES]:
                if not isinstance(service, (str, int)):
                    error = (
                        f"Endpoint '{name}' service must be a string"
                        f", but found {service.__class__.__name__}."
                    )
                    if not silent:
                        click.secho(error, err=True, fg="red")
                        return False
                    else:
                        raise ConfigureNetworkError(error)

        if ConfigFields.CONNECT_TO in con:
            if not validate_connections(
                con[ConfigFields.CONNECT_TO], silent, level + 1
            ):
                return False

    return True


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
        dst_dict (dict): Connections dictionary that contain tags as endpoints.
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

        agents = utils.WithRetry(api.platform_agent_index)(
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
