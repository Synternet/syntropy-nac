from unittest import mock

import pytest
import syntropy_sdk as sdk

from syntropynac import __main__ as ctl


@pytest.fixture
def config_mock():
    with mock.patch(
        "syntropynac.configure.configure_network", autospec=True
    ) as the_mock:
        yield the_mock


@pytest.fixture
def test_yaml(runner, test_yaml):
    with runner.isolated_filesystem():
        with open("test.yaml", "w") as f:
            f.write(test_yaml)

        yield


def test_configure_networks(runner, test_yaml, config_mock):
    runner.invoke(ctl.configure_networks, ["test.yaml"])
    config_mock.assert_called_once_with(
        mock.ANY,
        {
            "name": "edge_to_lb",
            "state": "present",
            "use_sdn": True,
            "use_public": False,
            "sdn_path_count": 3,
            "latency_threshold": 10,
            "pl_threshold": 1,
            "topology": "p2m",
            "connections": {
                "de-aws-lb01": {
                    "type": "endpoint",
                    "services": ["haproxy", "mqtt"],
                    "connect_to": {"iot_device": {"type": "tag", "services": "ssh"}},
                }
            },
        },
        False,
    )


def test_configure_networks__dry_run(runner, test_yaml, config_mock):
    runner.invoke(ctl.configure_networks, ["--dry-run", "test.yaml"])
    config_mock.assert_called_once_with(
        mock.ANY,
        {
            "name": "edge_to_lb",
            "state": "present",
            "use_sdn": True,
            "use_public": False,
            "sdn_path_count": 3,
            "latency_threshold": 10,
            "pl_threshold": 1,
            "topology": "p2m",
            "connections": {
                "de-aws-lb01": {
                    "type": "endpoint",
                    "services": ["haproxy", "mqtt"],
                    "connect_to": {"iot_device": {"type": "tag", "services": "ssh"}},
                }
            },
        },
        True,
    )


def test_export_networks(
    runner, index_networks, p2p_connections, index_agents_ex, p2p_connection_services
):
    with mock.patch.object(
        sdk.PlatformApi,
        "index_networks",
        autospec=True,
        return_value=index_networks,
    ) as index_net, mock.patch.object(
        sdk.PlatformApi,
        "index_connections",
        autospec=True,
        return_value={"data": p2p_connections},
    ) as index_conn, mock.patch.object(
        sdk.PlatformApi,
        "index_agents",
        autospec=True,
        return_value=index_agents_ex,
    ) as index_ag, mock.patch.object(
        sdk.PlatformApi,
        "get_connection_services",
        autospec=True,
        return_value={"data": p2p_connection_services},
    ) as services_mock:
        result = runner.invoke(ctl.export_networks)
        assert "skip" in result.output
        assert "test" in result.output
        assert "nats-streaming" in result.output
