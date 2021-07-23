from unittest import mock

import pytest
import syntropy_sdk as sdk

from syntropynac import configure, exceptions, resolve, transform


@pytest.fixture
def config_mock():
    with mock.patch(
        "syntropynac.configure.configure_connections",
        autospec=True,
        return_value=(1, 3),
    ) as the_mock:
        yield the_mock


@pytest.fixture
def validate_connections_mock():
    with mock.patch(
        "syntropynac.resolve.validate_connections", autospec=True, return_value=True
    ) as the_mock:
        yield the_mock


@pytest.fixture
def delete_config():
    return {
        "name": "test1",
        "topology": "p2p",
        "state": "absent",
        "connections": {
            "agent1": {
                "connect_to": {
                    "agent2": {},
                },
                "state": "absent",
            },
            "agent3": {
                "state": "absent",
                "connect_to": {
                    "agent4": {},
                },
            },
            "agent5": {"connect_to": {"agent6": {}}},
        },
    }


@pytest.fixture
def networks():
    return [
        {
            "network_id": 1,
            "network_name": "test1",
            "network_disable_sdn_connections": False,
            "network_metadata": {
                "network_type": "P2P",
            },
        },
        {
            "network_id": 2,
            "network_name": "test2",
            "network_disable_sdn_connections": False,
            "network_metadata": {
                "network_type": "P2M",
            },
        },
        {
            "network_id": 3,
            "network_name": "test3",
            "network_disable_sdn_connections": False,
            "network_metadata": {
                "network_type": "MESH",
            },
        },
    ]


@pytest.fixture
def connections_stub():
    def stub(*args, **kwargs):
        connections = [
            {
                "agent_connection_id": 0,
                "network": {"network_id": 1},
                "agent_1": {"agent_id": 1, "agent_name": "agent1"},
                "agent_2": {"agent_id": 2, "agent_name": "agent2"},
            },
            {
                "agent_connection_id": 1,
                "network": {"network_id": 2},
                "agent_1": {"agent_id": 1, "agent_name": "agent1"},
                "agent_2": {"agent_id": 2, "agent_name": "agent2"},
            },
            {
                "agent_connection_id": 2,
                "network": {"network_id": 2},
                "agent_1": {"agent_id": 3, "agent_name": "agent3"},
                "agent_2": {"agent_id": 4, "agent_name": "agent4"},
            },
            {
                "agent_connection_id": 3,
                "network": {"network_id": 123},
                "agent_1": {"agent_id": 123, "agent_name": "agent123"},
                "agent_2": {"agent_id": 321, "agent_name": "agent321"},
            },
            {
                "agent_connection_id": 4,
                "network": {"network_id": 3},
                "agent_1": {"agent_id": 1, "agent_name": "agent1"},
                "agent_2": {"agent_id": 2, "agent_name": "agent2"},
            },
            {
                "agent_connection_id": 5,
                "network": {"network_id": 3},
                "agent_1": {"agent_id": 3, "agent_name": "agent3"},
                "agent_2": {"agent_id": 4, "agent_name": "agent4"},
            },
            {
                "agent_connection_id": 6,
                "network": {"network_id": 3},
                "agent_1": {"agent_id": 2, "agent_name": "agent2"},
                "agent_2": {"agent_id": 3, "agent_name": "agent3"},
            },
        ]

        if "filter" in kwargs:
            net = int(kwargs["filter"][len("networks[]:") :])
            return {
                "data": [
                    {
                        "agent_connection_id": i["agent_connection_id"],
                        "agent_1": i["agent_1"],
                        "agent_2": i["agent_2"],
                    }
                    for i in connections
                    if i["network"]["network_id"] == net
                ]
            }
        return {"data": connections}

    return stub


def test_create_connections(api, created_connections):
    api.platform_connection_index.side_effect = lambda *args, **kwargs: {
        "data": created_connections
    }

    result = configure.create_connections(api, [(13, 11), (14, 13)], True)
    assert api.platform_connection_create_p2p.call_args_list == [
        mock.call(
            body={
                "agent_ids": [
                    {"agent_1_id": 13, "agent_2_id": 11},
                    {"agent_1_id": 14, "agent_2_id": 13},
                ],
            },
        ),
    ]
    assert result == [
        {
            "agent_1": {"agent_id": 13, "agent_name": "iot_mqtt"},
            "agent_2": {"agent_id": 11, "agent_name": "iot_device2"},
            "agent_connection_id": 7,
        },
        {
            "agent_1": {"agent_id": 13, "agent_name": "iot_mqtt"},
            "agent_2": {"agent_id": 14, "agent_name": "iot_device2"},
            "agent_connection_id": 8,
        },
    ]


def test_delete_connections(api):
    result = configure.delete_connections(
        api,
        [(13, 11), (14, 13)],
    )
    assert api.platform_connection_destroy.call_args_list == [
        mock.call(
            body=[
                {"agent_1_id": 13, "agent_2_id": 11},
                {"agent_1_id": 14, "agent_2_id": 13},
            ],
        ),
    ]


@pytest.mark.parametrize(
    "config, result",
    [
        [resolve.ConnectionServices(9, 22, [], []), ((23, False), (24, False))],
        [
            resolve.ConnectionServices(9, 22, ["nats-streaming"], []),
            ((21, True), (22, True), (23, False), (24, False)),
        ],
        [resolve.ConnectionServices(9, 22, [], ["sdn-pgadmin"]), ((23, False),)],
        [
            resolve.ConnectionServices(9, 22, ["sdn-bi"], ["streaming"]),
            ((24, False), (25, True)),
        ],
        [
            resolve.ConnectionServices(9, 22, ["missing-subnet"], []),
            ((23, False), (24, False), (123, True)),
        ],
        [
            resolve.ConnectionServices(9, 22, [], ["missing-subnet"]),
            ((23, False), (24, False)),
        ],
        [
            resolve.ConnectionServices(9, 22, ["no-such-service"], ["no-such-service"]),
            ((23, False), (24, False)),
        ],
    ],
)
def test_configure_connection(
    api, config, result, connection_services, agent_connection_subnets_2
):
    connection = {
        **connection_services,
        "agent_connection_subnets": agent_connection_subnets_2,
    }
    assert configure.configure_connection(api, config, connection, silent=False) == len(
        result
    )
    assert api.platform_connection_service_update.call_args_list[-1] == mock.call(
        body={
            "connectionId": 169,
            "changes": [
                {"agentServiceSubnetId": id, "isEnabled": en} for id, en in result
            ],
        }
    )


def test_configure_network__validation_fail(api, validate_connections_mock):
    config = {
        "name": "test",
        "topology": "p2p",
        "state": "present",
        "connections": {"a": {}, "b": {}},
    }
    validate_connections_mock.return_value = False
    with pytest.raises(exceptions.ConfigureNetworkError):
        configure.configure_network(api, config, "False", silent="silent")
    validate_connections_mock.assert_called_once_with(
        config["connections"], silent="silent"
    )


def test_configure_network__create(api, validate_connections_mock):
    config = {"name": "test", "topology": "P2P", "state": "present"}
    with mock.patch(
        "syntropynac.configure.configure_network_create",
        autospec=True,
        return_value="changed",
    ) as the_mock:
        assert (
            configure.configure_network(api, config, "False", silent="silent")
            == "changed"
        )
        the_mock.assert_called_once_with(api, config, "False", silent="silent")
        validate_connections_mock.assert_called_once_with({}, silent="silent")


def test_configure_network__delete(api, validate_connections_mock):
    config = {"name": "test2", "topology": "p2p", "state": "absent"}
    assert configure.configure_network(api, config, "False", silent="silent") == False


def test_create_network__dry_run(api):
    config = {
        "name": "test",
        "topology": "P2P",
        "state": "present",
        "connections": {
            "agent-1": {
                "type": "endpoint",
                "connect_to": {
                    "agent-2": {
                        "type": "endpoint",
                    }
                },
            },
        },
    }
    with mock.patch(
        "syntropynac.resolve.resolve_p2p_connections",
        autospec=True,
        return_value=[[1, 2], [3, 4], []],
    ) as the_mock:
        assert configure.configure_network_create(api, config, True) == False
        assert api.platform_connection_create.call_count == 0


def test_create_network__p2p(api, config_mock):
    config = {
        "topology": "P2P",
        "state": "present",
        "connections": {
            "agent-1": {
                "type": "endpoint",
                "connect_to": {
                    "agent-2": {
                        "type": "endpoint",
                    }
                },
            },
            "agent-3": {
                "type": "endpoint",
                "connect_to": {
                    "agent-4": {
                        "type": "endpoint",
                    }
                },
            },
        },
    }
    with mock.patch(
        "syntropynac.resolve.resolve_p2p_connections",
        autospec=True,
        return_value=([[1, 2], [3, 4]], [], []),
    ) as the_mock:
        assert configure.configure_network_create(api, config, False) == True
        the_mock.assert_called_once()

        assert api.platform_connection_create_p2p.call_args_list == [
            mock.call(
                body={
                    "agent_ids": [
                        {"agent_1_id": 1, "agent_2_id": 2},
                        {"agent_1_id": 3, "agent_2_id": 4},
                    ],
                },
            )
        ]


def test_create_network__p2m(api, config_mock):
    config = {
        "topology": "p2m",
        "state": "present",
        "connections": {
            "agent-1": {
                "type": "endpoint",
                "connect_to": {
                    "agent-2": {
                        "type": "endpoint",
                    },
                    "agent-4": {
                        "type": "endpoint",
                    },
                    "agent-3": {
                        "type": "endpoint",
                    },
                },
            },
        },
    }
    with mock.patch(
        "syntropynac.resolve.resolve_p2m_connections",
        autospec=True,
        return_value=([[1, 2], [3, 4]], [], []),
    ) as the_mock:
        assert configure.configure_network_create(api, config, False) == True

        assert api.platform_connection_create_p2p.call_args_list == [
            mock.call(
                body={
                    "agent_ids": [
                        {"agent_1_id": 1, "agent_2_id": 2},
                        {"agent_1_id": 3, "agent_2_id": 4},
                    ],
                },
            )
        ]


def test_create_network__mesh(api, config_mock):
    config = {
        "name": "test",
        "id": None,
        "topology": "mesh",
        "state": "present",
        "connections": {
            "agent-2": {
                "type": "endpoint",
                "id": None,
            },
            "agent-4": {
                "type": "endpoint",
            },
            "agent-3": {
                "type": "endpoint",
            },
        },
    }
    with mock.patch(
        "syntropynac.resolve.resolve_mesh_connections",
        autospec=True,
        return_value=([[1, 2], [1, 4], [2, 4]], [], []),
    ) as the_mock:
        assert configure.configure_network_create(api, config, False) == True

        assert api.platform_connection_create_p2p.call_args_list == [
            mock.call(
                body={
                    "agent_ids": [
                        {"agent_1_id": 1, "agent_2_id": 2},
                        {"agent_1_id": 1, "agent_2_id": 4},
                        {"agent_1_id": 2, "agent_2_id": 4},
                    ],
                },
            )
        ]


def test_create_network__mesh__fail_with_id(api, config_mock):
    config = {
        "topology": "mesh",
        "state": "present",
        "connections": {
            "agent-2": {
                "type": "endpoint",
            },
            "agent-4": {
                "type": "endpoint",
            },
            "agent-3": {
                "type": "endpoint",
            },
        },
    }
    with pytest.raises(exceptions.ConfigureNetworkError):
        configure.configure_network_create(api, config, False, silent=True)
    assert api.platform_connection_create_p2p.call_count == 0


def test_delete_network__dry_run(networks, api, delete_config):
    assert configure.configure_network_delete(api, delete_config, True) == False
    assert api.platform_connection_destroy.call_count == 0


def test_delete_network(api, networks, delete_config):
    assert configure.configure_network_delete(api, delete_config, False) == True
    assert api.platform_connection_destroy.call_args_list == [
        mock.call(
            body=[
                {
                    "agent_1_id": 1,
                    "agent_2_id": 2,
                },
                {
                    "agent_1_id": 3,
                    "agent_2_id": 4,
                },
            ]
        )
    ]
