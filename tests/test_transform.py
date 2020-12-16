import pytest

from syntropynac import transform
from tests.utils import EqualSets, update_all_tags


def testGetEnabledConnectionSubnets1(connection_services, agent_connection_subnets_1):
    connection = {
        "agent_connection_services": {
            **connection_services,
            "agent_connection_subnets": agent_connection_subnets_1,
        }
    }
    assert transform.get_enabled_connection_subnets(connection) == {21, 23, 24, 25}


def testGetEnabledConnectionSubnets2(connection_services, agent_connection_subnets_2):
    connection = {
        "agent_connection_services": {
            **connection_services,
            "agent_connection_subnets": agent_connection_subnets_2,
        }
    }
    assert transform.get_enabled_connection_subnets(connection) == {23, 24}


def testTransformConnectionServices(connection_services, agent_connection_subnets_1):
    connection = {
        "agent_connection_services": {
            **connection_services,
            "agent_connection_subnets": agent_connection_subnets_1,
        }
    }
    assert transform.transform_connection_services(connection) == (
        {"sdn-bi", "nats-streaming"},
        {"sdn-pgadmin", "streaming"},
    )


def testTransformNetwork(index_networks):
    assert transform.transform_network(index_networks["data"][0]) == {
        "name": "skip",
        "id": 321,
        "topology": "P2P",
        "use_sdn": True,
        "state": "present",
    }


def testTransformNetworkTopologyMesh(index_networks):
    assert transform.transform_network(index_networks["data"][1]) == {
        "name": "test",
        "id": 123,
        "topology": "MESH",
        "use_sdn": True,
        "state": "present",
    }


def testTransformNetworkTypeMesh(index_networks):
    assert transform.transform_network(index_networks["data"][2]) == {
        "name": "test",
        "id": 456,
        "topology": "MESH",
        "use_sdn": True,
        "state": "present",
    }


def testTransformConnectionsP2P(all_agents, p2p_connections):
    assert transform.transform_connections(all_agents, p2p_connections, "P2P") == {
        "de-hetzner-db01": {
            "type": "endpoint",
            "id": 1,
            "state": "present",
            "services": [],
            "connect_to": {
                "de-aws-be01": {
                    "type": "endpoint",
                    "services": [],
                    "id": 2,
                },
            },
        },
        "de-aws-lb01": {
            "type": "endpoint",
            "state": "present",
            "services": [],
            "id": 3,
            "connect_to": {
                "kr-aws-dns01": {
                    "type": "endpoint",
                    "services": [],
                    "id": 4,
                },
            },
        },
    }


def testTransformConnectionsP2M(all_agents, p2m_connections):
    assert transform.transform_connections(all_agents, p2m_connections, "P2M") == {
        "auto gen 1": {
            "type": "endpoint",
            "id": 1,
            "state": "present",
            "services": [],
            "connect_to": {
                "auto gen 4": {
                    "state": "present",
                    "id": 4,
                    "type": "endpoint",
                    "services": [],
                },
                "auto gen 5": {
                    "state": "present",
                    "id": 5,
                    "type": "endpoint",
                    "services": [],
                },
                "auto gen 6": {
                    "state": "present",
                    "id": 6,
                    "type": "endpoint",
                    "services": [],
                },
            },
        },
    }


def testTransformConnectionsP2MReversed(all_agents, p2m_connections):
    connections = [
        {
            **i,
            "agent_1": i["agent_2"],
            "agent_2": i["agent_1"],
        }
        for i in p2m_connections
    ]
    assert transform.transform_connections(all_agents, connections, "P2M") == {
        "auto gen 1": {
            "type": "endpoint",
            "id": 1,
            "state": "present",
            "services": [],
            "connect_to": {
                "auto gen 4": {
                    "state": "present",
                    "id": 4,
                    "type": "endpoint",
                    "services": [],
                },
                "auto gen 5": {
                    "state": "present",
                    "id": 5,
                    "type": "endpoint",
                    "services": [],
                },
                "auto gen 6": {
                    "state": "present",
                    "id": 6,
                    "type": "endpoint",
                    "services": [],
                },
            },
        },
    }


def testTransformConnectionsP2MTagged(all_agents, p2m_connections):
    connections = [
        {
            **i,
            "agent_2": {
                **i["agent_2"],
                "agent_tags": [
                    {"agent_tag_name": "test"},
                ],
            },
        }
        for i in p2m_connections
    ]
    update_all_tags(all_agents, connections)
    assert transform.transform_connections(all_agents, connections, "P2M") == {
        "auto gen 1": {
            "type": "endpoint",
            "id": 1,
            "state": "present",
            "services": [],
            "connect_to": {
                "test": {
                    "state": "present",
                    "type": "tag",
                    "services": [],
                },
            },
        },
    }


def testTransformConnectionsP2MTaggedMultiple(all_agents, p2m_connections):
    connections = [
        {
            **i,
            "agent_2": {
                **i["agent_2"],
                "agent_tags": [
                    {"agent_tag_name": "test"},
                    {"agent_tag_name": "TEST"},
                ],
            },
        }
        for i in p2m_connections
    ]
    update_all_tags(all_agents, connections)
    assert transform.transform_connections(all_agents, connections, "P2M") == {
        "auto gen 1": {
            "type": "endpoint",
            "id": 1,
            "state": "present",
            "services": [],
            "connect_to": {
                "test": {
                    "state": "present",
                    "type": "tag",
                    "services": [],
                },
                "TEST": {
                    "state": "present",
                    "type": "tag",
                    "services": [],
                },
            },
        },
    }


def testTransformConnectionsMesh(all_agents, mesh_connections):
    assert transform.transform_connections(all_agents, mesh_connections, "MESH") == {
        "auto gen 10": {
            "type": "endpoint",
            "state": "present",
            "services": [],
            "id": 10,
        },
        "auto gen 11": {
            "type": "endpoint",
            "state": "present",
            "services": [],
            "id": 11,
        },
        "auto gen 12": {
            "type": "endpoint",
            "state": "present",
            "services": [],
            "id": 12,
        },
        "auto gen 13": {
            "type": "endpoint",
            "state": "present",
            "services": [],
            "id": 13,
        },
    }


def testTransformConnectionsMeshTaggedMultiple(all_agents, mesh_connections):
    connections = [
        {
            **i,
            "agent_1": {
                **i["agent_1"],
                "agent_tags": [
                    {"agent_tag_name": "test"},
                    {"agent_tag_name": "TEST"},
                ],
            },
            "agent_2": {
                **i["agent_2"],
                "agent_tags": [
                    {"agent_tag_name": "test"},
                    {"agent_tag_name": "TEST"},
                ],
            },
        }
        for i in mesh_connections
    ]
    update_all_tags(all_agents, connections)
    assert transform.transform_connections(all_agents, connections, "MESH") == {
        "test": {
            "type": "tag",
            "state": "present",
            "services": [],
        },
        "TEST": {
            "type": "tag",
            "state": "present",
            "services": [],
        },
    }


def testGroupAgentsByTags():
    agents = {
        1: {
            "agent_id": 1,
            "agent_name": "a",
            "agent_tags": [{"agent_tag_id": 1, "agent_tag_name": "test"}],
        },
        2: {
            "agent_id": 2,
            "agent_name": "b",
            "agent_tags": [{"agent_tag_id": 1, "agent_tag_name": "test"}],
        },
        3: {
            "agent_id": 3,
            "agent_name": "c",
            "agent_tags": [
                {"agent_tag_id": 1, "agent_tag_name": "test"},
                {"agent_tag_id": 2, "agent_tag_name": "TEST"},
            ],
        },
        4: {
            "agent_id": 4,
            "agent_name": "d",
            "agent_tags": [{"agent_tag_id": 1, "agent_tag_name": "TEST"}],
        },
        5: {"agent_id": 5, "agent_name": "e", "agent_tags": []},
        6: {
            "agent_id": 6,
            "agent_name": "f",
            "agent_tags": [{"agent_tag_id": 1, "agent_tag_name": "TEST"}],
        },
    }
    endpoints = {
        "a": {"id": 1, "type": "endpoint", "services": ["a"]},
        "b": {"id": 2, "type": "endpoint", "services": ["b"]},
        "c": {"id": 3, "type": "endpoint", "services": ["c"]},
        "d": {"id": 4, "type": "endpoint"},
        "e": {"id": 5, "type": "endpoint", "services": ["d"]},
    }
    assert transform.group_agents_by_tags(agents, endpoints) == {
        "test": {
            "type": "tag",
            "state": "present",
            "services": EqualSets({"a", "b", "c"}),
        },
        "d": {
            "type": "endpoint",
            "id": 4,
            "state": "present",
            "services": [],
        },
        "e": {
            "type": "endpoint",
            "id": 5,
            "state": "present",
            "services": ["d"],
        },
    }
