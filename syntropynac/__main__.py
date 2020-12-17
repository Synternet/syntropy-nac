#!/usr/bin/env python
import json

import click
import syntropy_sdk as sdk
import yaml

from syntropynac import configure, fields, transform
from syntropynac.decorators import syntropy_platform


@click.group()
def apis():
    """Syntropy Network As Code cli tool"""


@apis.command()
@click.argument("config")
@click.option(
    "--network",
    default=None,
    type=str,
    help="Filter configuration file networks by name",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Perform a dry run without configuring anything.",
)
@click.option(
    "--json",
    "-j",
    "from_json",
    is_flag=True,
    default=False,
    help="Imports configuration from JSON instead of YAML",
)
@syntropy_platform
def configure_networks(config, network, dry_run, from_json, platform):
    """Configure networks using a configuration YAML/JSON file.

    \b
    Example YAML file:
        name: test-network
        state: present
        topology: P2M
        connections:
            gateway-endpoint:
                state: present
                type: endpoint
                services:
                - postgres
                - redis
                connect_to:
                    endpoint-1:
                        type: endpoint
                        services:
                        - app
                    endpoint2:
                        state: present
                        type: endpoint
                        services:
                        - app
    """
    with open(config, "rb") as cfg_file:
        if from_json:
            config = json.load(cfg_file)
            config = config if isinstance(config, list) else [config]
        else:
            config = list(yaml.safe_load_all(cfg_file))

    for index, net in enumerate(config):
        if any(i not in net for i in ("name", "topology", "state")):
            click.secho(
                f"Skipping {index} entry as no name, topology or state found.",
                fg="yellow",
            )
            continue
        if (network and network in net["name"]) or not network:
            configure.configure_network(platform, net, dry_run)

    click.secho("Done", fg="green")


@apis.command()
@click.option("--network", default=None, type=str, help="Filter networks by name or ID")
@click.option("--skip", default=0, type=int, help="Skip N networks")
@click.option("--take", default=42, type=int, help="Take N networks")
@click.option("--topology", default=None, type=str, help="Override network topology")
@click.option(
    "--json",
    "-j",
    "to_json",
    is_flag=True,
    default=False,
    help="Outputs a JSON instead of YAML",
)
@syntropy_platform
def export_networks(network, skip, take, topology, to_json, platform):
    """Exports existing networks to configuration YAML/JSON file.

    If the network was created via UI or manually with complex topology in order
    to get full export, you might want to override the topology.

    If exact topology export is required - use P2P topology.

    By default this command will retrieve up to 42 networks. You can use --take parameter to get more networks.
    """
    if topology:
        topology = topology.upper()
        if topology not in sdk.utils.ALLOWED_NETWORK_TOPOLOGIES:
            click.secho(
                f"Network topology {topology} not supported. Skipping.",
                err=True,
                fg="red",
            )
            return

    networks = [
        transform.transform_network(net)
        for net in platform.index_networks(
            filter=f"id|name:{network}" if network else None,
            skip=skip,
            take=take,
        )["data"]
    ]
    if not networks:
        return

    all_agents = sdk.utils.WithRetry(platform.index_agents)(
        take=sdk.utils.TAKE_MAX_ITEMS_PER_CALL
    )["data"]
    all_agents = {agent["agent_id"]: agent for agent in all_agents}

    for net in networks:
        connections_filter = f"networks[]:{net['id']}"
        connections = sdk.utils.WithRetry(platform.index_connections)(
            filter=connections_filter, take=sdk.utils.TAKE_MAX_ITEMS_PER_CALL
        )["data"]
        ids = [connection["agent_connection_id"] for connection in connections]
        if ids:
            connections_services = sdk.utils.BatchedRequest(
                platform.get_connection_services,
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
            if connection["network"]["network_id"] == net["id"]
        ]
        transformed_connections = transform.transform_connections(
            all_agents,
            net_connections,
            topology if topology else net[fields.ConfigFields.TOPOLOGY],
        )
        if transformed_connections:
            net[fields.ConfigFields.CONNECTIONS] = transformed_connections
        if topology:
            net["topology"] = topology
        del net["use_sdn"]

    if to_json:
        click.echo(json.dumps(networks, indent=4))
    else:
        click.echo(yaml.dump_all(networks))


def main():
    apis(prog_name="syntropynac")


if __name__ == "__main__":
    main()
