from unittest import mock

import pytest
import syntropy_sdk as sdk

from syntropynac import exceptions, resolve


@pytest.fixture
def api(index_agents_stub, connection_services_stub):
    api = mock.Mock(spec=sdk.PlatformApi)
    api.index_agents = mock.Mock(
        spec=sdk.PlatformApi.index_agents,
        side_effect=index_agents_stub,
    )
    api.get_connection_services = mock.Mock(
        spec=sdk.PlatformApi.get_connection_services,
        side_effect=connection_services_stub,
    )
    return api


def test_resolve_present_absent(config_connections):
    agents = {f"agent {i}": i for i in range(5)}
    config_connections = list(config_connections.items())
    present = [
        (config_connections[0], config_connections[1]),
        (config_connections[0], config_connections[2]),
        (config_connections[3], config_connections[4]),
    ]
    absent = [
        (config_connections[0], config_connections[2]),
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


def test_expand_agents_tags__present(api):
    config = {
        "test": {
            "type": "tag",
            "state": "present",
        },
    }
    assert resolve.expand_agents_tags(api, config) == {
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


def test_expand_agents_tags__present_services(api):
    config = {
        "test": {
            "type": "tag",
            "state": "present",
            "services": ["a", "b"],
        },
    }
    assert resolve.expand_agents_tags(api, config) == {
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


def test_expand_agents_tags__except_one(api):
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
    assert resolve.expand_agents_tags(api, config) == {
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


def test_expand_agents_tags__except_tag(api):
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

    def index_agents(filter=None, take=None):
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

    api.index_agents.side_effect = index_agents
    assert resolve.expand_agents_tags(api, config) == {
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


def test_resolve_p2p_connections(api):
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
    assert resolve.resolve_p2p_connections(api, connections) == (
        [[1, 2], [3, 4]],
        [[4, 1], [2, 4]],
        [
            resolve.ConnectionServices(1, 2, ["a", "b"], []),
            resolve.ConnectionServices(3, 4, [], ["nginx"]),
        ],
    )


def test_resolve_p2m_connections(api):
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
    assert resolve.resolve_p2m_connections(api, connections) == (
        [[1, 2], [1, 3]],
        [[1, 4], [2, 5], [2, 6]],
        [
            resolve.ConnectionServices(1, 2, ["nginx"], ["postgre"]),
            resolve.ConnectionServices(1, 3, ["nginx"], []),
        ],
    )


def test_resolve_p2m_connections__tags(api):
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
    assert resolve.resolve_p2m_connections(api, connections) == (
        [[1, 160], [1, 161], [1, 162]],
        [[2, 170], [2, 171], [2, 172]],
        [
            resolve.ConnectionServices(1, 160, ["nginx"], ["a", "b"]),
            resolve.ConnectionServices(1, 161, ["nginx"], ["a", "b"]),
            resolve.ConnectionServices(1, 162, ["nginx"], ["a", "b"]),
        ],
    )


def test_resolve_p2m_connections__tags_not_found(api):
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
        assert resolve.resolve_p2m_connections(api, connections) == (
            [],
            [],
            [],
        )
        the_mock.assert_called_once()


def test_resolve_mesh_connections(api):
    connections = {
        "agent1": {"services": "a"},
        "agent2": {"services": "b"},
        "3": {"type": "id", "services": "c"},
        "agent4": {"state": "absent"},
    }
    assert resolve.resolve_mesh_connections(api, connections) == (
        [[1, 2], [1, 3], [2, 3]],
        [[1, 4], [2, 4], [3, 4]],
        [
            resolve.ConnectionServices(1, 2, ["a"], ["b"]),
            resolve.ConnectionServices(1, 3, ["a"], ["c"]),
            resolve.ConnectionServices(2, 3, ["b"], ["c"]),
        ],
    )


def test_resolve_mesh_connections__tag(api):
    connections = {
        "tag1": {"type": "tag"},
        "iot": {"type": "tag"},
    }
    assert resolve.resolve_mesh_connections(api, connections) == (
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


def test_resolve_mesh_connections__tags_not_found(api):
    connections = {
        "tag1": {"type": "tag"},
        "iot": {"type": "tag"},
    }
    with mock.patch(
        "syntropynac.resolve.expand_agents_tags", autospec=True, return_value=None
    ) as the_mock:
        assert resolve.resolve_mesh_connections(api, connections) == (
            [],
            [],
            [],
        )
        the_mock.assert_called_once()
