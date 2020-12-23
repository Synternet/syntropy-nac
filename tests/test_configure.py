from unittest import mock

import pytest
import syntropy_sdk as sdk

from syntropynac import configure, resolve, transform


@pytest.fixture
def config_mock():
    with mock.patch(
        "syntropynac.configure.configure_connections",
        autospec=True,
        return_value=(1, 3),
    ) as the_mock:
        yield the_mock


@pytest.fixture
def networks():
    return [
        {
            "network_id": 1,
            "network_name": "test1",
            "network_type": "POINT_TO_POINT",
            "network_disable_sdn_connections": False,
            "network_metadata": {
                "network_type": "P2P",
            },
        },
        {
            "network_id": 2,
            "network_name": "test2",
            "network_type": "POINT_TO_POINT",
            "network_disable_sdn_connections": False,
            "network_metadata": {
                "network_type": "P2M",
            },
        },
        {
            "network_id": 3,
            "network_name": "test3",
            "network_type": "POINT_TO_POINT",
            "network_disable_sdn_connections": False,
            "network_metadata": {
                "network_type": "MESH",
            },
        },
    ]


@pytest.fixture
def connections():
    return [
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


@pytest.fixture
def api(
    networks,
    connections,
    created_connections,
    platform_agent_index_stub,
    connection_services_stub,
):
    api = mock.Mock(spec=sdk.PlatformApi)
    api.platform_network_index = mock.Mock(
        spec=sdk.PlatformApi.platform_network_index, return_value={"data": networks}
    )
    api.platform_connection_index = mock.Mock(
        spec=sdk.PlatformApi.platform_connection_index,
        return_value={"data": connections},
    )
    api.platform_network_create = mock.Mock(
        spec=sdk.PlatformApi.platform_network_create,
        return_value={"data": {"network_id": 321}},
    )
    api.platform_connection_create = mock.Mock(
        spec=sdk.PlatformApi.platform_connection_create,
        return_value={"data": created_connections},
    )
    api.platform_connection_destroy = mock.Mock(
        spec=sdk.PlatformApi.platform_connection_destroy
    )
    api.platform_network_destroy = mock.Mock(
        spec=sdk.PlatformApi.platform_network_destroy
    )
    api.platform_agent_index = mock.Mock(
        spec=sdk.PlatformApi.platform_agent_index, side_effect=platform_agent_index_stub
    )
    api.platform_connection_service_show = mock.Mock(
        spec=sdk.PlatformApi.platform_connection_service_show,
        side_effect=connection_services_stub,
    )
    api.platform_connection_service_update = mock.Mock(
        spec=sdk.PlatformApi.platform_connection_service_update,
    )
    return api


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


def test_configure_network__create(api):
    config = {"name": "test", "state": "present"}
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


def test_configure_network__delete(api):
    config = {"name": "test2", "state": "absent"}
    with mock.patch(
        "syntropynac.configure.configure_network_delete",
        autospec=True,
        return_value="changed",
    ) as the_mock:
        assert (
            configure.configure_network(api, config, "False", silent="silent")
            == "changed"
        )
        the_mock.assert_called_once_with(
            api,
            {
                "name": "test2",
                "id": 2,
                "topology": "P2M",
                "use_sdn": True,
                "state": "present",
            },
            "False",
            silent="silent",
        )


def test_configure_network__update(networks, api):
    config = {"name": "test2", "state": "present"}
    with mock.patch(
        "syntropynac.configure.configure_network_update",
        autospec=True,
        return_value="changed",
    ) as the_mock:
        assert (
            configure.configure_network(api, config, "False", silent="silent")
            == "changed"
        )
        the_mock.assert_called_once_with(
            api,
            transform.transform_network(networks[1]),
            config,
            "False",
            silent="silent",
        )


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
        assert api.platform_network_create.call_count == 0
        assert api.platform_connection_create.call_count == 0


def test_create_network__p2p(api, config_mock):
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
        assert api.platform_network_create.call_args_list == [
            mock.call(
                body={
                    "network_name": "test",
                    "network_type": "POINT_TO_POINT",
                    "network_disable_sdn_connections": True,
                    "network_metadata": {
                        "network_created_by": "CONFIG",
                        "network_type": "P2P",
                    },
                }
            )
        ]
        assert api.platform_connection_create.call_args_list == [
            mock.call(
                body={
                    "network_id": 321,
                    "agent_ids": [[1, 2], [3, 4]],
                    "network_update_by": "CONFIG",
                }
            )
        ]


def test_create_network__p2m(api, config_mock):
    config = {
        "name": "test",
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
        assert api.platform_network_create.call_args_list == [
            mock.call(
                body={
                    "network_name": "test",
                    "network_type": "POINT_TO_POINT",
                    "network_disable_sdn_connections": True,
                    "network_metadata": {
                        "network_created_by": "CONFIG",
                        "network_type": "P2M",
                    },
                }
            )
        ]
        assert api.platform_connection_create.call_args_list == [
            mock.call(
                body={
                    "network_id": 321,
                    "agent_ids": [[1, 2], [3, 4]],
                    "network_update_by": "CONFIG",
                }
            )
        ]


def test_create_network__mesh(api, config_mock):
    config = {
        "name": "test",
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
    with mock.patch(
        "syntropynac.resolve.resolve_mesh_connections",
        autospec=True,
        return_value=([[1, 2], [1, 4], [2, 4]], [], []),
    ) as the_mock:
        assert configure.configure_network_create(api, config, False) == True
        assert api.platform_network_create.call_args_list == [
            mock.call(
                body={
                    "network_name": "test",
                    "network_type": "POINT_TO_POINT",
                    "network_disable_sdn_connections": True,
                    "network_metadata": {
                        "network_created_by": "CONFIG",
                        "network_type": "MESH",
                    },
                }
            )
        ]
        assert api.platform_connection_create.call_args_list == [
            mock.call(
                body={
                    "network_id": 321,
                    "agent_ids": [[1, 2], [1, 4], [2, 4]],
                    "network_update_by": "CONFIG",
                }
            )
        ]


def test_delete_network__dry_run(networks, api):
    assert (
        configure.configure_network_delete(
            api, transform.transform_network(networks[1]), True
        )
        == False
    )
    assert api.platform_network_destroy.call_count == 0
    assert api.platform_connection_destroy.call_count == 0


def test_delete_network(api, networks):
    assert (
        configure.configure_network_delete(
            api, transform.transform_network(networks[1]), False
        )
        == True
    )
    assert api.platform_network_destroy.call_args_list == [mock.call(2)]
    assert api.platform_connection_destroy.call_args_list == [
        mock.call(1),
        mock.call(2),
    ]


def test_update_network__p2p_dry_run(api, networks):
    config = {
        "name": "test1",
        "topology": "p2p",
        "state": "present",
        "connections": {
            "agent1": {
                "connect_to": {
                    "agent2": {},
                }
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
    assert (
        configure.configure_network_update(
            api, transform.transform_network(networks[0]), config, True
        )
        == False
    )
    assert api.platform_connection_index.call_count == 1
    assert api.platform_network_create.call_count == 0
    assert api.platform_connection_destroy.call_count == 0
    assert api.platform_connection_create.call_count == 0


def test_update_network__p2p(api, networks, config_mock):
    config = {
        "name": "test1",
        "topology": "p2p",
        "state": "present",
        "connections": {
            "agent1": {
                "state": "absent",
                "connect_to": {
                    "agent2": {},
                },
            },
            "agent5": {"connect_to": {"agent6": {}}},
        },
    }
    assert (
        configure.configure_network_update(
            api, transform.transform_network(networks[0]), config, False
        )
        == True
    )
    assert api.platform_connection_index.call_count == 1
    assert api.platform_network_create.call_count == 0
    assert api.platform_connection_destroy.call_args_list == [
        mock.call(0),
    ]
    assert api.platform_connection_create.call_args_list == [
        mock.call(
            body={
                "network_id": 1,
                "agent_ids": [[5, 6]],
                "network_update_by": "CONFIG",
            },
            update_type=sdk.UpdateType.APPEND_NEW,
        )
    ]


def test_update_network__p2m_dry_run(api, networks):
    config = {
        "name": "test2",
        "topology": "p2m",
        "state": "present",
        "connections": {
            "agent1": {
                "connect_to": {
                    "agent2": {"state": "absent"},
                    "agent3": {},
                    "agent4": {},
                }
            },
            "agent5": {"connect_to": {"agent6": {}}},
        },
    }
    assert (
        configure.configure_network_update(
            api, transform.transform_network(networks[1]), config, True
        )
        == False
    )
    assert api.platform_connection_index.call_count == 1
    assert api.platform_network_create.call_count == 0
    assert api.platform_connection_destroy.call_count == 0
    assert api.platform_connection_create.call_count == 0


def test_update_network__p2m(api, networks, config_mock):
    config = {
        "name": "test2",
        "topology": "p2m",
        "state": "present",
        "connections": {
            "agent1": {
                "connect_to": {
                    "agent2": {"state": "absent"},
                    "agent3": {},
                    "agent4": {},
                }
            },
            "agent5": {"connect_to": {"agent6": {}}},
        },
    }
    assert (
        configure.configure_network_update(
            api, transform.transform_network(networks[1]), config, False
        )
        == True
    )
    assert api.platform_connection_index.call_count == 1
    assert api.platform_network_create.call_count == 0
    assert api.platform_connection_destroy.call_args_list == [
        mock.call(1),
    ]
    assert api.platform_connection_create.call_args_list == [
        mock.call(
            body={
                "network_id": 2,
                "agent_ids": [[1, 3], [1, 4], [5, 6]],
                "network_update_by": "CONFIG",
            },
            update_type=sdk.UpdateType.APPEND_NEW,
        )
    ]


def test_update_network__mesh_dry_run(api, networks):
    config = {
        "name": "test3",
        "topology": "mesh",
        "state": "present",
        "connections": {
            "agent1": {
                "state": "present",
            },
            "agent2": {
                "state": "absent",
            },
            "agent3": {
                "state": "present",
            },
            "agent4": {
                "state": "present",
            },
        },
    }
    assert (
        configure.configure_network_update(
            api, transform.transform_network(networks[2]), config, True
        )
        == False
    )
    assert api.platform_connection_index.call_count == 1
    assert api.platform_network_create.call_count == 0
    assert api.platform_connection_destroy.call_count == 0
    assert api.platform_connection_create.call_count == 0


def test_update_network__mesh(api, networks, config_mock):
    config = {
        "name": "test3",
        "topology": "mesh",
        "state": "present",
        "connections": {
            "agent1": {
                "state": "present",
            },
            "agent2": {
                "state": "absent",
            },
            "agent3": {
                "state": "present",
            },
            "agent5": {
                "state": "present",
            },
        },
    }
    assert (
        configure.configure_network_update(
            api, transform.transform_network(networks[2]), config, False
        )
        == True
    )
    assert api.platform_connection_index.call_count == 1
    assert api.platform_network_create.call_count == 0
    assert api.platform_connection_destroy.call_args_list == [
        mock.call(4),
        mock.call(6),
    ]
    assert api.platform_connection_create.call_args_list == [
        mock.call(
            body={
                "network_id": 3,
                "agent_ids": [[1, 5], [3, 5]],
                "network_update_by": "CONFIG",
            },
            update_type=sdk.UpdateType.APPEND_NEW,
        )
    ]
