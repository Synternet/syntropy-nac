from unittest import mock

import pytest
import syntropy_sdk as sdk

from syntropynac import transform, utils
from tests.utils import EqualSets


def test_export_p2p_network(api_agents, api_connections, api_services, all_agents):
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
                        "services": ["sdn-pgadmin"],
                        "type": "endpoint",
                    }
                },
                "id": 3,
                "services": ["sdn-bi"],
                "state": "present",
                "type": "endpoint",
            },
            "de-hetzner-db01": {
                "connect_to": {
                    "de-aws-be01": {
                        "id": 2,
                        "services": EqualSets(["sdn-pgadmin", "streaming"]),
                        "type": "endpoint",
                    }
                },
                "id": 1,
                "services": EqualSets(["sdn-bi", "nats-streaming"]),
                "state": "present",
                "type": "endpoint",
            },
        },
        "endpoints": {
            "auto gen 0": {"id": 0, "services": ["nginx", "redis"], "tags": []},
            "auto gen 10": {
                "id": 10,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 11": {
                "id": 11,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 12": {
                "id": 12,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 13": {
                "id": 13,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 14": {
                "id": 14,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 15": {
                "id": 15,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 16": {
                "id": 16,
                "services": ["nginx", "redis"],
                "tags": [],
            },
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
    sdk.ServicesApi.platform_agent_service_index.assert_called_once()


def test_export_mesh_network(
    api_agents, api_connections, api_services, all_agents, p2m_connections
):
    ids = list(all_agents.keys())
    for id in ids:
        if id > 16:
            del all_agents[id]
    sdk.ConnectionsApi.platform_connection_groups_index = mock.Mock(
        spec=sdk.ConnectionsApi.platform_connection_groups_index,
        return_value={"data": p2m_connections},
    )
    result = {
        "connections": {
            "auto gen 1": {
                "id": 1,
                "services": [],
                "state": "present",
                "type": "endpoint",
            },
            "auto gen 4": {
                "id": 4,
                "services": [],
                "state": "present",
                "type": "endpoint",
            },
            "auto gen 5": {
                "id": 5,
                "services": [],
                "state": "present",
                "type": "endpoint",
            },
            "auto gen 6": {
                "id": 6,
                "services": [],
                "state": "present",
                "type": "endpoint",
            },
        },
        "endpoints": {
            "auto gen 0": {"id": 0, "services": ["nginx", "redis"], "tags": []},
            "auto gen 10": {
                "id": 10,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 11": {
                "id": 11,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 12": {
                "id": 12,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 13": {
                "id": 13,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 14": {
                "id": 14,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 15": {
                "id": 15,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 16": {
                "id": 16,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 2": {"id": 2, "services": ["nginx", "redis"], "tags": []},
            "auto gen 3": {"id": 3, "services": ["nginx", "redis"], "tags": []},
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
    sdk.ServicesApi.platform_agent_service_index.assert_called_once()


def test_export_p2p1_network(
    api_agents, api_connections, api_services, all_agents, mesh_connections
):
    ids = list(all_agents.keys())
    for id in ids:
        if id > 16:
            del all_agents[id]
    sdk.ConnectionsApi.platform_connection_groups_index = mock.Mock(
        spec=sdk.ConnectionsApi.platform_connection_groups_index,
        return_value={"data": mesh_connections},
    )
    result = {
        "connections": {
            10: {
                "connect_to": {
                    "iot_mqtt": {"id": 13, "services": [], "type": "endpoint"}
                },
                "id": 10,
                "services": [],
                "state": "present",
                "type": "id",
            },
            "iot_device1": {
                "connect_to": {
                    "iot_device3": {
                        "id": 12,
                        "services": [],
                        "type": "endpoint",
                    }
                },
                "id": 10,
                "services": [],
                "state": "present",
                "type": "endpoint",
            },
            "iot_device2": {
                "connect_to": {
                    "iot_mqtt": {"id": 13, "services": [], "type": "endpoint"}
                },
                "id": 11,
                "services": [],
                "state": "present",
                "type": "endpoint",
            },
            "iot_device3": {
                "connect_to": {
                    "iot_mqtt": {"id": 13, "services": [], "type": "endpoint"}
                },
                "id": 12,
                "services": [],
                "state": "present",
                "type": "endpoint",
            },
            "iot_mqtt": {
                "connect_to": {
                    "iot_device1": {
                        "id": 10,
                        "services": [],
                        "type": "endpoint",
                    }
                },
                "id": 13,
                "services": [],
                "state": "present",
                "type": "endpoint",
            },
        },
        "endpoints": {
            "auto gen 0": {"id": 0, "services": ["nginx", "redis"], "tags": []},
            "auto gen 1": {"id": 1, "services": ["nginx", "redis"], "tags": []},
            "auto gen 14": {
                "id": 14,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 15": {
                "id": 15,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 16": {
                "id": 16,
                "services": ["nginx", "redis"],
                "tags": [],
            },
            "auto gen 2": {"id": 2, "services": ["nginx", "redis"], "tags": []},
            "auto gen 3": {"id": 3, "services": ["nginx", "redis"], "tags": []},
            "auto gen 4": {"id": 4, "services": ["nginx", "redis"], "tags": []},
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
    sdk.ServicesApi.platform_agent_service_index.assert_called_once()
