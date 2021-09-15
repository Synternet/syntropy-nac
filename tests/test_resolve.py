from unittest import mock

import pytest
import syntropy_sdk as sdk

from syntropynac import exceptions, resolve


@pytest.fixture
def api_agents(platform_agent_index_stub):
    with mock.patch.object(
        sdk.AgentsApi,
        "platform_agent_index",
        autospec=True,
        side_effect=platform_agent_index_stub,
    ):
        yield


@pytest.fixture
def api_services(
    connection_services_stub,
):
    with mock.patch.object(
        sdk.ServicesApi,
        "platform_connection_service_show",
        autospec=True,
        side_effect=connection_services_stub,
    ):
        yield


def test_resolve_present_absent(config_connections):
    agents = {f"agent {i}": i for i in range(5)}
    config_connections = list(config_connections.items())
    present = [
        (config_connections[0], config_connections[0]),
        (config_connections[0], config_connections[1]),
        (config_connections[0], config_connections[2]),
        (config_connections[2], config_connections[2]),
        (config_connections[3], config_connections[4]),
    ]
    absent = [
        (config_connections[0], config_connections[2]),
        (config_connections[1], config_connections[1]),
        (config_connections[3], config_connections[3]),
    ]
    assert resolve.resolve_present_absent(agents, present, absent) == (
        [[0, 1], [3, 4]],
        [[0, 2]],
        [
            resolve.ConnectionServices(0, 1, ["a", "b"], ["b", "c"]),
            resolve.ConnectionServices(3, 4, ["f", "g"], ["h", "i"]),
        ],
    )


def test_resolve_present_absent__no_services():
    agents = {f"agent {i}": i for i in range(5)}
    present = [
        (
            ("agent 0", {}),
            ("agent 1", {"services": None}),
        ),
    ]
    absent = []
    assert resolve.resolve_present_absent(agents, present, absent) == (
        [[0, 1]],
        [],
        [resolve.ConnectionServices(0, 1, [], [])],
    )


def test_resolve_present_absent__str_services():
    agents = {f"agent {i}": i for i in range(5)}
    present = [
        (
            ("agent 0", {}),
            ("agent 1", {"services": "nginx"}),
        ),
    ]
    absent = []
    assert resolve.resolve_present_absent(agents, present, absent) == (
        [[0, 1]],
        [],
        [resolve.ConnectionServices(0, 1, [], ["nginx"])],
    )


def test_resolve_present_absent__bad_services():
    agents = {f"agent {i}": i for i in range(5)}
    present = [
        (
            ("agent 0", {}),
            ("agent 1", {"services": {}}),
        ),
    ]
    absent = []
    with pytest.raises(exceptions.ConfigureNetworkError):
        resolve.resolve_present_absent(agents, present, absent)


def test_expand_agents_tags__present(api_agents, with_pagination):
    config = {
        "test": {
            "type": "tag",
            "state": "present",
        },
    }
    assert resolve.expand_agents_tags(mock.Mock(spec=sdk.ApiClient), config) == {
        "filter - tags_names[]:test 0": {
            "type": "endpoint",
            "state": "present",
            "id": 170,
            "services": None,
        },
        "filter - tags_names[]:test 1": {
            "type": "endpoint",
            "state": "present",
            "id": 171,
            "services": None,
        },
        "filter - tags_names[]:test 2": {
            "type": "endpoint",
            "state": "present",
            "id": 172,
            "services": None,
        },
    }


VALIDATE_CONNECTIONS_TESTS = (
    {"": {"type": "endpoint"}},
    {"a": {"type": "id"}},
    {123: {"type": "id", "id": 321}},
    {"123": {"type": "id", "id": 321}},
    {"a": ""},
    {"a": {}},
    {"a": {"type": "id", "id": ""}},
    {"b": {"type": "id", "id": "b"}},
    {"a": {"type": "id", "connect_to": {"b": ""}}},
    {"a": {"type": "id", "connect_to": {"b": {"type": "fail"}}}},
    {"a": {"type": "fail"}},
    {"a": {"type": "id", "services": {}}},
    {"a": {"type": "id", "services": [{"a": 1}]}},
)


@pytest.mark.parametrize("connections", VALIDATE_CONNECTIONS_TESTS)
def test_validate_connections__fail_cli(connections):
    assert not resolve.validate_connections(connections)


@pytest.mark.parametrize("connections", VALIDATE_CONNECTIONS_TESTS)
def test_validate_connections__fail_ansible(connections):
    with pytest.raises(exceptions.ConfigureNetworkError):
        resolve.validate_connections(connections, silent=True)


@pytest.mark.parametrize(
    "connections",
    (
        {"13": {"type": "id"}},
        {13: {"type": "id"}},
        {13: {"type": "id", "id": 13}},
        {13: {"type": "id", "id": "13"}},
        {"13": {"type": "id", "id": 13}},
        {"a": {"type": "endpoint"}},
        {"a": {"type": "endpoint", "id": None}},
        {"a": {"type": "tag"}},
        {"12": {"type": "id", "connect_to": {"1": {"type": "id"}}}},
        {"1": {"type": "id", "connect_to": {"b": {"type": "endpoint"}}}},
        {"1": {"type": "id", "connect_to": {"b": {"type": "tag"}}}},
        {"a": {"type": "endpoint", "connect_to": {"1": {"type": "id"}}}},
        {"a": {"type": "endpoint", "connect_to": {"b": {"type": "endpoint"}}}},
        {"a": {"type": "endpoint", "connect_to": {"b": {"type": "tag"}}}},
        {"a": {"type": "tag", "connect_to": {"1": {"type": "id"}}}},
        {"a": {"type": "tag", "connect_to": {"b": {"type": "endpoint"}}}},
        {"a": {"type": "tag", "connect_to": {"b": {"type": "tag"}}}},
        {"1": {"type": "id", "services": ["a", "b", 1]}},
    ),
)
def test_validate_connections__success(connections):
    assert resolve.validate_connections(connections)


def test_expand_agents_tags__present_services(api_agents, with_pagination):
    config = {
        "test": {
            "type": "tag",
            "state": "present",
            "services": ["a", "b"],
        },
    }
    assert resolve.expand_agents_tags(mock.Mock(spec=sdk.ApiClient), config) == {
        "filter - tags_names[]:test 0": {
            "type": "endpoint",
            "state": "present",
            "id": 170,
            "services": ["a", "b"],
        },
        "filter - tags_names[]:test 1": {
            "type": "endpoint",
            "state": "present",
            "id": 171,
            "services": ["a", "b"],
        },
        "filter - tags_names[]:test 2": {
            "type": "endpoint",
            "state": "present",
            "id": 172,
            "services": ["a", "b"],
        },
    }


def test_expand_agents_tags__except_one(api_agents, with_pagination):
    config = {
        "test": {
            "type": "tag",
            "state": "present",
            "services": ["a", "b"],
        },
        "filter - tags_names[]:test 1": {
            "type": "endpoint",
            "state": "absent",
            "services": ["c", "d"],
        },
    }
    assert resolve.expand_agents_tags(mock.Mock(spec=sdk.ApiClient), config) == {
        "filter - tags_names[]:test 0": {
            "type": "endpoint",
            "state": "present",
            "services": ["a", "b"],
            "id": 170,
        },
        "filter - tags_names[]:test 1": {
            "type": "endpoint",
            "state": "absent",
            "services": ["c", "d"],
        },
        "filter - tags_names[]:test 2": {
            "type": "endpoint",
            "state": "present",
            "services": ["a", "b"],
            "id": 172,
        },
    }


def test_expand_agents_tags__except_tag(api_agents, with_pagination):
    config = {
        "test": {
            "type": "tag",
            "state": "present",
            "services": ["a", "b"],
        },
        "test1": {
            "type": "tag",
            "state": "absent",
            "services": ["c", "d"],
        },
    }

    def platform_agent_index(
        _, filter=None, take=None, skip=None, _preload_content=None
    ):
        if "test1" in filter:
            return {
                "data": [
                    {
                        "agent_name": f"test {i}",
                        "agent_id": i,
                    }
                    for i in range(3)
                ]
            }
        else:
            return {
                "data": [
                    {
                        "agent_name": f"test {i}",
                        "agent_id": i,
                    }
                    for i in range(2, 5)
                ]
            }

    sdk.AgentsApi.platform_agent_index.side_effect = platform_agent_index
    assert resolve.expand_agents_tags(mock.Mock(spec=sdk.ApiClient), config) == {
        "test 0": {
            "type": "endpoint",
            "state": "absent",
            "id": 0,
            "services": ["c", "d"],
        },
        "test 1": {
            "type": "endpoint",
            "state": "absent",
            "id": 1,
            "services": ["c", "d"],
        },
        "test 2": {
            "type": "endpoint",
            "state": "absent",
            "id": 2,
            "services": ["c", "d"],
        },
        "test 3": {
            "type": "endpoint",
            "state": "present",
            "id": 3,
            "services": ["a", "b"],
        },
        "test 4": {
            "type": "endpoint",
            "state": "present",
            "id": 4,
            "services": ["a", "b"],
        },
    }


def test_resolve_p2p_connections(api_connections, api_agents, with_pagination):
    connections = {
        "agent1": {
            "connect_to": {
                "agent2": {},
                "services": None,
            },
            "services": ["a", "b"],
        },
        "agent3": {"connect_to": {"4": {"type": "id", "services": "nginx"}}},
        "agent4": {"state": "absent", "connect_to": {"agent1": {}}},
        "2": {"type": "id", "connect_to": {"agent4": {"state": "absent"}}},
    }
    assert resolve.resolve_p2p_connections(
        mock.Mock(spec=sdk.ApiClient), connections
    ) == (
        [[1, 2], [3, 4]],
        [[4, 1], [2, 4]],
        [
            resolve.ConnectionServices(1, 2, ["a", "b"], []),
            resolve.ConnectionServices(3, 4, [], ["nginx"]),
        ],
    )


def test_resolve_p2m_connections(api_connections, api_agents, with_pagination):
    connections = {
        "agent1": {
            "connect_to": {
                "agent2": {"services": "postgre"},
                "agent3": {},
                "agent4": {"state": "absent"},
            },
            "services": "nginx",
        },
        "2": {
            "state": "absent",
            "type": "id",
            "connect_to": {
                "agent5": {},
                "6": {"type": "id"},
            },
        },
    }
    assert resolve.resolve_p2m_connections(
        mock.Mock(spec=sdk.ApiClient), connections
    ) == (
        [[1, 2], [1, 3]],
        [[1, 4], [2, 5], [2, 6]],
        [
            resolve.ConnectionServices(1, 2, ["nginx"], ["postgre"]),
            resolve.ConnectionServices(1, 3, ["nginx"], []),
        ],
    )


def test_resolve_p2m_connections__tags(api_connections, api_agents, with_pagination):
    connections = {
        "agent1": {
            "connect_to": {
                "tag": {"type": "tag", "services": ["a", "b"]},
            },
            "services": "nginx",
        },
        "agent2": {
            "connect_to": {
                "tag1": {"type": "tag", "state": "absent"},
            }
        },
    }
    assert resolve.resolve_p2m_connections(
        mock.Mock(spec=sdk.ApiClient), connections
    ) == (
        [[1, 160], [1, 161], [1, 162]],
        [[2, 170], [2, 171], [2, 172]],
        [
            resolve.ConnectionServices(1, 160, ["nginx"], ["a", "b"]),
            resolve.ConnectionServices(1, 161, ["nginx"], ["a", "b"]),
            resolve.ConnectionServices(1, 162, ["nginx"], ["a", "b"]),
        ],
    )


def test_resolve_p2m_connections__tags_not_found(
    api_connections, api_agents, with_pagination
):
    connections = {
        "agent1": {
            "connect_to": {
                "tag": {"type": "tag"},
            }
        },
        "agent2": {
            "connect_to": {
                "tag1": {"type": "tag", "state": "absent"},
            }
        },
    }
    with mock.patch(
        "syntropynac.resolve.expand_agents_tags", autospec=True, return_value=None
    ) as the_mock:
        assert resolve.resolve_p2m_connections(
            mock.Mock(spec=sdk.ApiClient), connections
        ) == (
            [],
            [],
            [],
        )
        the_mock.assert_called_once()


def test_resolve_mesh_connections(api_connections, api_agents, with_pagination):
    connections = {
        "agent1": {"services": "a"},
        "agent2": {"services": "b"},
        "3": {"type": "id", "services": "c"},
        "agent4": {"state": "absent"},
    }
    assert resolve.resolve_mesh_connections(
        mock.Mock(spec=sdk.ApiClient), connections
    ) == (
        [[1, 2], [1, 3], [2, 3]],
        [[1, 4], [2, 4], [3, 4]],
        [
            resolve.ConnectionServices(1, 2, ["a"], ["b"]),
            resolve.ConnectionServices(1, 3, ["a"], ["c"]),
            resolve.ConnectionServices(2, 3, ["b"], ["c"]),
        ],
    )


def test_resolve_mesh_connections__tag(api_connections, api_agents, with_pagination):
    connections = {
        "tag1": {"type": "tag"},
        "iot": {"type": "tag"},
    }
    assert resolve.resolve_mesh_connections(
        mock.Mock(spec=sdk.ApiClient), connections
    ) == (
        [
            [170, 171],
            [170, 172],
            [170, 160],
            [170, 161],
            [170, 162],
            [171, 172],
            [171, 160],
            [171, 161],
            [171, 162],
            [172, 160],
            [172, 161],
            [172, 162],
            [160, 161],
            [160, 162],
            [161, 162],
        ],
        [],
        mock.ANY,
    )


def test_resolve_mesh_connections__tags_not_found(api_connections):
    connections = {
        "tag1": {"type": "tag"},
        "iot": {"type": "tag"},
    }
    with mock.patch(
        "syntropynac.resolve.expand_agents_tags", autospec=True, return_value=None
    ) as the_mock:
        assert resolve.resolve_mesh_connections(
            mock.Mock(spec=sdk.ApiClient), connections
        ) == (
            [],
            [],
            [],
        )
        the_mock.assert_called_once()
