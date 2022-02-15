import click
import syntropy_sdk as sdk
from syntropy_sdk import utils

from syntropynac import resolve, transform
from syntropynac.exceptions import ConfigureNetworkError
from syntropynac.fields import ALLOWED_TOPOLOGIES, ConfigFields, PeerState, Topology


def create_connections(api, peers, silent=False):
    body = {
        "agent_ids": [{"agent_1_id": a, "agent_2_id": b} for a, b in peers],
    }

    utils.BatchedRequestBody(
        sdk.ConnectionsApi(api).platform_connection_create_p2p,
        translator=utils._default_translator("agent_ids"),
        max_payload_size=utils.MAX_PAYLOAD_SIZE,
    )(body=body)

    connections = utils.WithPagination(
        sdk.ConnectionsApi(api).platform_connection_groups_index
    )(_preload_content=False)["data"]

    frozen_peers = [frozenset(peer) for peer in peers]
    connections = [
        con
        for con in connections
        if frozenset((con["agent_1"]["agent_id"], con["agent_2"]["agent_id"]))
        in frozen_peers
    ]

    not silent and click.echo(f"Created {len(connections)} connections")

    return connections


def delete_connections(api, absent):
    body = [
        {
            "agent_1_id": a,
            "agent_2_id": b,
        }
        for a, b in absent
    ]

    utils.BatchedRequestBody(
        sdk.ConnectionsApi(api).platform_connections_destroy_deprecated,
        translator=lambda body, data: body[:] if data is None else data[:],
        max_payload_size=utils.MAX_PAYLOAD_SIZE,
    )(body=body)


def configure_connection(api, config, connection, silent=False):
    agents = {
        connection["agent_1"]["agent_id"]: connection["agent_1"],
        connection["agent_2"]["agent_id"]: connection["agent_2"],
    }

    enabled_subnets = set(config.get_subnets(1, agents) + config.get_subnets(2, agents))
    current_subnets = {
        subnet["agent_service_subnet_id"]: subnet["agent_connection_subnet_is_enabled"]
        for subnet in connection["agent_connection_subnets"]
    }

    # First collect all the changes to the original configured subnets
    changes = [
        {
            "agentServiceSubnetId": id,
            "isEnabled": id in enabled_subnets,
        }
        for id, enabled in current_subnets.items()
        if (id in enabled_subnets) != enabled
    ]
    # Then configure any missing subnets
    changes += [
        {
            "agentServiceSubnetId": id,
            "isEnabled": True,
        }
        for id in enabled_subnets
        if id not in current_subnets
    ]

    if not changes:
        return 0

    body = {
        "connectionGroupId": connection["agent_connection_group_id"],
        "changes": changes,
    }
    utils.BatchedRequestBody(
        sdk.ServicesApi(api).platform_connection_service_update,
        max_payload_size=utils.MAX_PAYLOAD_SIZE,
        translator=utils._default_translator("changes"),
    )(body=body)
    return len(changes)


def configure_connections(api, services_config, connections, silent=False):
    ids = [connection["agent_connection_group_id"] for connection in connections]
    if not ids:
        return 0, 0
    connections_services = utils.BatchedRequestQuery(
        sdk.ServicesApi(api).platform_connection_service_show,
        max_query_size=utils.MAX_QUERY_FIELD_SIZE,
    )(ids, _preload_content=False)["data"]

    # Build a map of connections so that it would be quicker to resolve them to subnets
    services_map = {}
    for conn in connections_services:
        services_map[
            frozenset((conn["agent_1"]["agent_id"], conn["agent_2"]["agent_id"]))
        ] = conn

    updated_connections = 0
    updated_subnets = 0
    # Update subnets with connection subnets
    for config in services_config:
        key = frozenset((config.agent_1, config.agent_2))
        if key not in services_map:
            not silent and click.secho(
                f"Warning: Connection from {config.agent_1} to {config.agent_2} was not created.",
                fg="yellow",
                err=True,
            )
            continue

        updated_connections += 1
        updated_subnets += configure_connection(
            api, config, services_map[key], silent=silent
        )

    return updated_connections, updated_subnets


def configure_network_update(api, config, dry_run, silent=False):
    """Updates existing network's connection.
    NOTE: This will ignore any preconfigured connections that are not
    explicitly specified in the config dictionary.

    Example config dictionary:
    {
        "topology": `P2P|P2M|MESH`,
        "use_sdn": `True|False`,
        "state": "present|absent",
        "connections": {
            # Connection for P2P
            "endpoint-name-1": {
                "type": "endpoint|tag|id",
                "id": 1,
                "state": "present|absent",
                "services": ["service1", "service2"],
                "connect_to": {
                    "endpoint-name-2": {
                        "type": "endpoint",
                        "id": 2,
                        "services": ["service3", "service4"],
                    },
                },
            },

            # Connection for P2M
            "source-endpoint": {
                "type": "endpoint",
                "id": 1,
                "state": "present",
                "connect_to": {
                    "destination-1": {
                        "state": "present",
                        "id": 10,
                        "type": "endpoint",
                    },
                    "destination-2": {
                        "state": "present",
                        "id": 11,
                        "type": "endpoint",
                    },
                    "destination-3": {
                        "state": "present",
                        "id": 12,
                        "type": "endpoint",
                    },
                },
            },

            # MESH network - all endpoints interconnected
            "endpoint-1": {
                "type": "endpoint",
                "state": "present",
                "id": 10,
            },
            "endpoint-2": {
                "type": "endpoint",
                "state": "present",
                "id": 11,
            },
            "endpoint-3": {
                "type": "endpoint",
                "state": "present",
                "id": 12,
            },
            "endpoint-4": {
                "type": "endpoint",
                "state": "present",
                "id": 13,
            },
        }
    }

    Args:
        api (PlatformApi): Instance of the platform API.
        config (dict): Configuration dictionary.
        dry_run (bool): Indicates whether to perform a dry run (without any configuration).
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.
    Returns:
        (bool): True if any changes were made and False otherwise
    """
    topology = config[ConfigFields.TOPOLOGY].upper()
    connections = utils.WithPagination(
        sdk.ConnectionsApi(api).platform_connection_groups_index
    )(_preload_content=False)["data"]
    all_agents = resolve.get_all_agents(api, silent)
    resolved_connections = transform.transform_connections(
        all_agents,
        connections,
        topology,
        group_tags=False,
        silent=silent,
    )
    current_connections = {
        frozenset(
            (connection["agent_1"]["agent_id"], connection["agent_2"]["agent_id"])
        ): connection
        for connection in connections
    }
    config_connections = config.get(ConfigFields.CONNECTIONS, {})

    if topology == Topology.P2P:
        present, absent, services = resolve.resolve_p2p_connections(
            api, config_connections, silent=silent
        )
    elif topology == Topology.P2M:
        present, absent, services = resolve.resolve_p2m_connections(
            api, config_connections, silent=silent
        )
    else:
        present, absent, services = resolve.resolve_mesh_connections(
            api, config_connections, silent=silent
        )
    if topology == Topology.P2P:
        current, _, _ = resolve.resolve_p2p_connections(
            api, resolved_connections, silent=silent
        )
    elif topology == Topology.P2M:
        current, _, _ = resolve.resolve_p2m_connections(
            api, resolved_connections, silent=silent
        )
    else:
        current, _, _ = resolve.resolve_mesh_connections(
            api, resolved_connections, silent=silent
        )

    present = [frozenset(i) for i in present]
    absent = [frozenset(i) for i in absent]
    current = [frozenset(i) for i in current]

    to_add = [list(link) for link in present if link not in current]

    if dry_run:
        not silent and click.echo(f"Would remove {len(absent)} connections.")
    else:
        delete_connections(api, absent)
        not silent and click.echo(f"Removed {len(absent)} connections.")

    added_connections = []
    if dry_run:
        not silent and click.echo(f"Would create {len(to_add)} connections.")
    elif to_add:
        added_connections = create_connections(api, to_add, silent)

    to_remove = [
        conn["agent_connection_group_id"]
        for link, conn in current_connections.items()
        if link in absent
    ]
    connections = [
        connection
        for connection in connections + added_connections
        if connection["agent_connection_group_id"] not in to_remove
    ]

    if dry_run:
        not silent and click.echo(f"Would configure {len(connections)} connections.")
    else:
        updated_connections, updated_subnets = configure_connections(
            api, services, connections, silent=silent
        )
        not silent and click.echo(
            f"Configured {updated_connections} connections and {updated_subnets} subnets"
        )
        return True
    return False


def configure_network_delete(api, config, dry_run, silent=False):
    """Deletes existing network's connections and the network itself.

    Args:
        api (PlatformApi): Instance of the platform API.
        network (dict): Dictionary containing id and name keys.
        dry_run (bool): Indicates whether to perform a dry run (without any configuration).
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.

    Returns:
        (bool): True if any changes were made and False otherwise
    """
    config_connections = config.get(ConfigFields.CONNECTIONS, {})
    topology = config[ConfigFields.TOPOLOGY].upper()

    if topology == Topology.P2P:
        _, absent, _ = resolve.resolve_p2p_connections(
            api, config_connections, silent=silent
        )
    elif topology == Topology.P2M:
        _, absent, _ = resolve.resolve_p2m_connections(
            api, config_connections, silent=silent
        )
    else:
        _, absent, _ = resolve.resolve_mesh_connections(
            api, config_connections, silent=silent
        )

    if dry_run:
        not silent and click.echo(f"Would delete {len(absent)} connections...")
        return False
    else:
        delete_connections(api, absent)
        return True


def configure_network(api, config, dry_run, silent=False):
    """Configures Syntropy Network based on the current state and the requested state.

    Args:
        api (PlatformApi): Instance of the platform API.
        config (dict): Configuration dictionary.
        dry_run (bool): Indicates whether to perform a dry run (without any configuration).
        silent (bool, optional): Indicates whether to suppress messages - used with Ansible. Defaults to False.

    Returns:
        (bool): True if any changes were made and False otherwise
    """
    if not all(i in config for i in (ConfigFields.TOPOLOGY, ConfigFields.STATE)):
        error = f"{ConfigFields.TOPOLOGY} and {ConfigFields.STATE} must be present"
        if not silent:
            click.secho(error, err=True, fg="red")
        else:
            raise ConfigureNetworkError(error)
        return False

    state = config[ConfigFields.STATE]
    if state not in (PeerState.PRESENT, PeerState.ABSENT):
        error = f"Invalid state {state}"
        if not silent:
            click.secho(error, fg="red", err=True)
            return False
        else:
            raise ConfigureNetworkError(error)

    if not resolve.validate_connections(
        config.get(ConfigFields.CONNECTIONS, {}), silent
    ):
        error = f"Invalid {ConfigFields.CONNECTIONS} format."
        if not silent:
            click.secho(error, fg="red", err=True)
            return False
        else:
            raise ConfigureNetworkError(error)

    not silent and click.secho(f"Configuring network", fg="green")

    if state == PeerState.PRESENT:
        return configure_network_update(api, config, dry_run, silent=silent)
    elif state == PeerState.ABSENT:
        return configure_network_delete(api, config, dry_run, silent=silent)
    return False
