from unittest import mock

import pytest
import syntropy_sdk as sdk

from syntropynac import transform, utils
from tests.utils import EqualSets


def test_export_p2p_network(
    api_agents_get, api_agents_search, api_connections, api_services, all_agents
):
    ids = list(all_agents.keys())
    for id in ids:
        if id > 16:
            del all_agents[id]
    result = {
        "connections": {
            "de-aws-lb01": {
                "connect_to": {
                    "kr-aws-dns01": {
                        "id": 4,
                        "services": EqualSets(["sdn-pgadmin", "streaming"]),
                        "type": "endpoint",
                    }
                },
                "id": 3,
                "services": EqualSets(["sdn-bi", "nats-streaming"]),
                "state": "present",
                "type": "endpoint",
            },
            "de-hetzner-db01": {
                "connect_to": {
                    "de-aws-be01": {
                        "id": 2,
                        "services": ["sdn-pgadmin"],
                        "type": "endpoint",
                    }
                },
                "id": 1,
                "services": ["sdn-bi"],
                "state": "present",
                "type": "endpoint",
            },
        },
        "endpoints": {
            "auto gen 0": {"id": 0, "services": ["nginx", "redis"], "tags": []},
            "auto gen 10": {"id": 10, "services": ["nginx", "redis"], "tags": []},
            "auto gen 11": {"id": 11, "services": ["nginx", "redis"], "tags": []},
            "auto gen 12": {"id": 12, "services": ["nginx", "redis"], "tags": []},
            "auto gen 13": {"id": 13, "services": ["nginx", "redis"], "tags": []},
            "auto gen 14": {"id": 14, "services": ["nginx", "redis"], "tags": []},
            "auto gen 15": {"id": 15, "services": ["nginx", "redis"], "tags": []},
            "auto gen 16": {"id": 16, "services": ["nginx", "redis"], "tags": []},
            "auto gen 5": {"id": 5, "services": ["nginx", "redis"], "tags": []},
            "auto gen 6": {"id": 6, "services": ["nginx", "redis"], "tags": []},
            "auto gen 7": {"id": 7, "services": ["nginx", "redis"], "tags": []},
            "auto gen 8": {"id": 8, "services": ["nginx", "redis"], "tags": []},
            "auto gen 9": {"id": 9, "services": ["nginx", "redis"], "tags": []},
        },
        "state": "present",
        "topology": "P2P",
    }
    assert (
        utils.export_network(mock.Mock(spec=sdk.ApiClient), all_agents, "p2p") == result
    )
    sdk.AgentsApi.v1_network_agents_services_get.assert_called_once()


def test_export_mesh_network(
    api_agents_get,
    api_agents_search,
    api_connections,
    api_services,
    all_agents,
    p2m_connections,
):
    ids = list(all_agents.keys())
    for id in ids:
        if id > 16:
            del all_agents[id]
    sdk.ConnectionsApi.v1_network_connections_get = mock.Mock(
        spec=sdk.ConnectionsApi.v1_network_connections_get,
        return_value={"data": p2m_connections},
    )
    result = {
        "connections": {
            "auto gen 1": {
                "id": 1,
                "services": ["sdn-bi"],
                "state": "present",
                "type": "endpoint",
            },
            "auto gen 2": {
                "id": 2,
                "services": ["sdn-pgadmin"],
                "state": "present",
                "type": "endpoint",
            },
            "auto gen 3": {
                "id": 3,
                "services": EqualSets(["sdn-bi", "nats-streaming"]),
                "state": "present",
                "type": "endpoint",
            },
            "auto gen 4": {
                "id": 4,
                "services": EqualSets(["sdn-pgadmin", "streaming"]),
                "state": "present",
                "type": "endpoint",
            },
        },
        "endpoints": {
            "auto gen 0": {"id": 0, "services": ["nginx", "redis"], "tags": []},
            "auto gen 10": {"id": 10, "services": ["nginx", "redis"], "tags": []},
            "auto gen 11": {"id": 11, "services": ["nginx", "redis"], "tags": []},
            "auto gen 12": {"id": 12, "services": ["nginx", "redis"], "tags": []},
            "auto gen 13": {"id": 13, "services": ["nginx", "redis"], "tags": []},
            "auto gen 14": {"id": 14, "services": ["nginx", "redis"], "tags": []},
            "auto gen 15": {"id": 15, "services": ["nginx", "redis"], "tags": []},
            "auto gen 16": {"id": 16, "services": ["nginx", "redis"], "tags": []},
            "auto gen 5": {"id": 5, "services": ["nginx", "redis"], "tags": []},
            "auto gen 6": {"id": 6, "services": ["nginx", "redis"], "tags": []},
            "auto gen 7": {"id": 7, "services": ["nginx", "redis"], "tags": []},
            "auto gen 8": {"id": 8, "services": ["nginx", "redis"], "tags": []},
            "auto gen 9": {"id": 9, "services": ["nginx", "redis"], "tags": []},
        },
        "state": "present",
        "topology": "MESH",
    }

    assert (
        utils.export_network(mock.Mock(spec=sdk.ApiClient), all_agents, "mesh")
        == result
    )
    sdk.AgentsApi.v1_network_agents_services_get.assert_called_once()


def test_export_p2p1_network(
    api_agents_get,
    api_agents_search,
    api_connections,
    api_services,
    all_agents,
    mesh_connections,
):
    ids = list(all_agents.keys())
    for id in ids:
        if id > 16:
            del all_agents[id]
    sdk.ConnectionsApi.v1_network_connections_get.return_value = {
        "data": mesh_connections
    }

    result = {
        "connections": {
            "de-aws-lb01": {
                "connect_to": {
                    "kr-aws-dns01": {
                        "id": 4,
                        "services": EqualSets(["sdn-pgadmin", "streaming"]),
                        "type": "endpoint",
                    }
                },
                "id": 3,
                "services": EqualSets(["sdn-bi", "nats-streaming"]),
                "state": "present",
                "type": "endpoint",
            },
            "de-hetzner-db01": {
                "connect_to": {
                    "de-aws-be01": {
                        "id": 2,
                        "services": ["sdn-pgadmin"],
                        "type": "endpoint",
                    }
                },
                "id": 1,
                "services": ["sdn-bi"],
                "state": "present",
                "type": "endpoint",
            },
        },
        "endpoints": {
            "auto gen 0": {"id": 0, "services": ["nginx", "redis"], "tags": []},
            "auto gen 10": {"id": 10, "services": ["nginx", "redis"], "tags": []},
            "auto gen 11": {"id": 11, "services": ["nginx", "redis"], "tags": []},
            "auto gen 12": {"id": 12, "services": ["nginx", "redis"], "tags": []},
            "auto gen 13": {"id": 13, "services": ["nginx", "redis"], "tags": []},
            "auto gen 14": {"id": 14, "services": ["nginx", "redis"], "tags": []},
            "auto gen 15": {"id": 15, "services": ["nginx", "redis"], "tags": []},
            "auto gen 16": {"id": 16, "services": ["nginx", "redis"], "tags": []},
            "auto gen 5": {"id": 5, "services": ["nginx", "redis"], "tags": []},
            "auto gen 6": {"id": 6, "services": ["nginx", "redis"], "tags": []},
            "auto gen 7": {"id": 7, "services": ["nginx", "redis"], "tags": []},
            "auto gen 8": {"id": 8, "services": ["nginx", "redis"], "tags": []},
            "auto gen 9": {"id": 9, "services": ["nginx", "redis"], "tags": []},
        },
        "state": "present",
        "topology": "P2P",
    }

    assert (
        utils.export_network(mock.Mock(spec=sdk.ApiClient), all_agents, "p2p") == result
    )
    sdk.AgentsApi.v1_network_agents_services_get.assert_called_once()
    sdk.ConnectionsApi.v1_network_connections_services_get.assert_called_once()
