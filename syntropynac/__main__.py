#!/usr/bin/env python
import json

import click
import syntropy_sdk as sdk
import yaml

from syntropynac import configure as configure_module
from syntropynac import fields, transform, utils
from syntropynac.decorators import syntropy_api


@click.group()
def apis():
    """Syntropy Network As Code Command Line Interface."""


@apis.command()
@click.argument("config")
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
    help="Imports configuration from JSON instead of YAML.",
)
@syntropy_api
def configure(config, dry_run, from_json, api):
    """Configure connections using a configuration YAML/JSON file.

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
    try:
        with open(config, "rb") as cfg_file:
            if from_json:
                config = json.load(cfg_file)
                config = config if isinstance(config, list) else [config]
            else:
                config = list(yaml.safe_load_all(cfg_file))
    except FileNotFoundError:
        click.secho(f"Could not find {config} file.", err=True, fg="red")
        return
    except json.decoder.JSONDecodeError:
        click.secho(f"Could not parse {config} file as JSON.", err=True, fg="red")
        return
    except yaml.YAMLError:
        click.secho(f"Could not parse {config} file as YAML.", err=True, fg="red")
        return

    for index, net in enumerate(config):
        if any(i not in net for i in ("topology", "state")):
            click.secho(
                f"Skipping {index} entry as no name, topology or state found.",
                fg="yellow",
            )
            continue
        configure_module.configure_network(api, net, dry_run)

    click.secho("Done", fg="green")


@apis.command()
@click.option("--topology", default=None, type=str, help="Override network topology.")
@click.option(
    "--json",
    "-j",
    "to_json",
    is_flag=True,
    default=False,
    help="Outputs a JSON instead of YAML.",
)
@syntropy_api
def export(topology, to_json, api):
    """Exports existing connections to configuration YAML/JSON file.

    If exact topology export is required - use P2P topology.
    """
    all_agents = sdk.utils.WithPagination(sdk.AgentsApi(api).platform_agent_index)(
        _preload_content=False
    )["data"]
    all_agents = {agent["agent_id"]: agent for agent in all_agents}

    network = utils.export_network(api, all_agents, topology)
    if to_json:
        click.echo(json.dumps(network, indent=4))
    else:
        click.echo(yaml.dump_all([network]))


def main():
    apis(prog_name="syntropynac")


if __name__ == "__main__":
    main()
