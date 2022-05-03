from unittest import mock

import pytest
import syntropy_sdk as sdk
from syntropy_sdk import models

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


def test_create_connections(api_connections, with_pagination, created_connections):
    sdk.ConnectionsApi.v1_network_connections_get.side_effect = (
        lambda *args, **kwargs: models.V1NetworkConnectionsGetResponse(
            data=created_connections
        )
    )

    result = configure.create_connections(
        mock.Mock(spec=sdk.ApiClient), [(13, 11), (14, 13)], True
    )
    assert sdk.ConnectionsApi.v1_network_connections_create_p2_p.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsCreateP2PRequest(
                agent_pairs=[
                    models.V1NetworkConnectionsCreateP2PRequestAgentPairs(
                        agent_1_id=13,
                        agent_2_id=11,
                    ),
                    models.V1NetworkConnectionsCreateP2PRequestAgentPairs(
                        agent_1_id=14,
                        agent_2_id=13,
                    ),
                ],
            ),
            _preload_content=False,
        ),
    ]
    assert result == [
        {
            "agent_1": {"agent_id": 13, "agent_name": "iot_mqtt"},
            "agent_2": {"agent_id": 11, "agent_name": "iot_device2"},
            "agent_connection_group_id": 7,
        },
        {
            "agent_1": {"agent_id": 13, "agent_name": "iot_mqtt"},
            "agent_2": {"agent_id": 14, "agent_name": "iot_device2"},
            "agent_connection_group_id": 8,
        },
    ]


def test_delete_connections(api_connections):
    result = configure.delete_connections(
        mock.Mock(spec=sdk.ApiClient),
        [(13, 11), (14, 13)],
    )
    sdk.ConnectionsApi.v1_network_connections_remove.assert_called_once()
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsRemoveRequest(
                agent_connection_group_ids=[1, 2],
            ),
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
    api_connections,
    api_services,
    with_batched,
    config,
    result,
    connection_services,
    agent_connection_subnets_2,
):
    connection = {
        **connection_services,
        "agent_connection_subnets": agent_connection_subnets_2,
    }
    assert configure.configure_connection(
        mock.Mock(spec=sdk.ApiClient), config, connection, silent=False
    ) == len(result)
    assert sdk.ConnectionsApi.v1_network_connections_services_update.call_args_list[
        -1
    ] == mock.call(
        mock.ANY,
        body=models.V1NetworkConnectionsServicesUpdateRequest(
            agent_connection_group_id=169,
            changes=[
                models.AgentServicesUpdateChanges(
                    agent_service_subnet_id=id, is_enabled=en
                )
                for id, en in result
            ],
        ),
    )


def test_configure_network__validation_fail(
    api_connections,
    api_agents_search,
    api_services,
    with_pagination,
    validate_connections_mock,
):
    config = {
        "name": "test",
        "topology": "p2p",
        "state": "present",
        "connections": {"a": {}, "b": {}},
    }
    validate_connections_mock.return_value = False
    with pytest.raises(exceptions.ConfigureNetworkError):
        configure.configure_network(
            mock.Mock(spec=sdk.ApiClient), config, "False", silent="silent"
        )
    validate_connections_mock.assert_called_once_with(
        config["connections"], silent="silent"
    )


def test_configure_network__create(validate_connections_mock):
    config = {"name": "test", "topology": "P2P", "state": "present"}
    with mock.patch(
        "syntropynac.configure.configure_network_update",
        autospec=True,
        return_value="changed",
    ) as the_mock:
        assert (
            configure.configure_network(
                mock.Mock(spec=sdk.ApiClient), config, "False", silent="silent"
            )
            == "changed"
        )
        the_mock.assert_called_once_with(mock.ANY, config, "False", silent="silent")
        validate_connections_mock.assert_called_once_with({}, silent="silent")


def test_configure_network__delete(validate_connections_mock):
    config = {"name": "test2", "topology": "p2p", "state": "absent"}
    assert (
        configure.configure_network(
            mock.Mock(spec=sdk.ApiClient), config, "False", silent="silent"
        )
        == False
    )


def test_delete_network__dry_run(
    networks, api_agents_search, api_connections, delete_config
):
    assert (
        configure.configure_network_delete(
            mock.Mock(spec=sdk.ApiClient), delete_config, True
        )
        == False
    )
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_count == 0


def test_delete_network(
    networks, api_agents_search, api_connections, with_pagination, delete_config
):
    assert (
        configure.configure_network_delete(
            mock.Mock(spec=sdk.ApiClient), delete_config, False
        )
        == True
    )
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsRemoveRequest(
                agent_connection_group_ids=[1, 2],
            ),
        )
    ]


def test_update_network__p2p_dry_run(
    api_agents_search, api_agents_get, with_pagination, api_connections
):
    config = {
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
        configure.configure_network_update(mock.Mock(spec=sdk.ApiClient), config, True)
        == False
    )
    assert sdk.ConnectionsApi.v1_network_connections_get.call_count == 1
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_count == 0
    assert sdk.ConnectionsApi.v1_network_connections_create_p2_p.call_count == 0


def test_update_network__p2p(
    api_agents_search, api_agents_get, api_connections, with_pagination, config_mock
):
    config = {
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
        configure.configure_network_update(mock.Mock(spec=sdk.ApiClient), config, False)
        == True
    )
    assert sdk.ConnectionsApi.v1_network_connections_get.call_count == 2
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsRemoveRequest(
                agent_connection_group_ids=[1, 2],
            ),
        ),
    ]
    assert sdk.ConnectionsApi.v1_network_connections_create_p2_p.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsCreateP2PRequest(
                agent_pairs=[
                    models.V1NetworkConnectionsCreateP2PRequestAgentPairs(
                        agent_1_id=5,
                        agent_2_id=6,
                    ),
                ],
            ),
            _preload_content=False,
        )
    ]


def test_update_network__p2m_dry_run(
    api_agents_search, api_agents_get, with_pagination, api_connections
):
    config = {
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
        configure.configure_network_update(mock.Mock(spec=sdk.ApiClient), config, True)
        == False
    )
    assert sdk.ConnectionsApi.v1_network_connections_get.call_count == 1
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_count == 0
    assert sdk.ConnectionsApi.v1_network_connections_create_p2_p.call_count == 0


def test_update_network__p2m(
    api_agents_search, api_agents_get, api_connections, with_pagination, config_mock
):
    config = {
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
        configure.configure_network_update(mock.Mock(spec=sdk.ApiClient), config, False)
        == True
    )
    assert sdk.ConnectionsApi.v1_network_connections_get.call_count == 2
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsRemoveRequest(
                agent_connection_group_ids=[1, 2],
            ),
        ),
    ]
    assert sdk.ConnectionsApi.v1_network_connections_create_p2_p.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsCreateP2PRequest(
                agent_pairs=[
                    models.V1NetworkConnectionsCreateP2PRequestAgentPairs(
                        agent_1_id=1,
                        agent_2_id=3,
                    ),
                    models.V1NetworkConnectionsCreateP2PRequestAgentPairs(
                        agent_1_id=1,
                        agent_2_id=4,
                    ),
                    models.V1NetworkConnectionsCreateP2PRequestAgentPairs(
                        agent_1_id=5,
                        agent_2_id=6,
                    ),
                ],
            ),
            _preload_content=False,
        )
    ]


def test_update_network__mesh_dry_run(
    api_agents_search, api_agents_get, with_pagination, api_connections
):
    config = {
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
        configure.configure_network_update(mock.Mock(spec=sdk.ApiClient), config, True)
        == False
    )
    assert sdk.ConnectionsApi.v1_network_connections_get.call_count == 1
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_count == 0
    assert sdk.ConnectionsApi.v1_network_connections_create_p2_p.call_count == 0


def test_update_network__mesh(
    api_agents_search, api_agents_get, api_connections, with_pagination, config_mock
):
    config = {
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
        configure.configure_network_update(mock.Mock(spec=sdk.ApiClient), config, False)
        == True
    )
    assert sdk.ConnectionsApi.v1_network_connections_get.call_count == 2
    assert sdk.ConnectionsApi.v1_network_connections_remove.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsRemoveRequest(
                agent_connection_group_ids=[1, 2],
            ),
        ),
    ]
    assert sdk.ConnectionsApi.v1_network_connections_create_p2_p.call_args_list == [
        mock.call(
            mock.ANY,
            body=models.V1NetworkConnectionsCreateP2PRequest(
                agent_pairs=[
                    models.V1NetworkConnectionsCreateP2PRequestAgentPairs(
                        agent_1_id=1,
                        agent_2_id=5,
                    ),
                    models.V1NetworkConnectionsCreateP2PRequestAgentPairs(
                        agent_1_id=3,
                        agent_2_id=5,
                    ),
                ],
            ),
            _preload_content=False,
        )
    ]
