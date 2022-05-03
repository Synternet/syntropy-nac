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


def test_configure_networks(runner, test_yaml, config_mock, login_mock):
    runner.invoke(ctl.configure, ["test.yaml"], catch_exceptions=False)
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


def test_configure_networks__dry_run(runner, test_yaml, config_mock, login_mock):
    runner.invoke(ctl.configure, ["--dry-run", "test.yaml"])
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
    runner,
    api_agents_get,
    api_connections,
    api_services,
    with_pagination,
    with_batched_filter,
    login_mock,
):
    result = runner.invoke(ctl.export, catch_exceptions=False)
    assert "connections" in result.output
    assert "P2M" in result.output
    assert "topology" in result.output
    assert "state" in result.output
    assert "present" in result.output
    assert "endpoints" in result.output
    assert "nats-streaming" in result.output
