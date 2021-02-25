from unittest import mock

import pytest
import syntropy_sdk as sdk

from syntropynac import transform, utils
from tests.utils import EqualSets


@pytest.fixture
def api(
    p2p_connections,
    p2m_connections,
    mesh_connections,
    platform_agent_index_stub,
    p2p_connection_services,
):
    def get_connections(*args, filter=None, **kwargs):
        if "321" in filter:
            return {"data": p2p_connections}
        elif "123" in filter:
            return {"data": p2m_connections}
        elif "456" in filter:
            return {"data": mesh_connections}
        else:
            return None

    def get_services(ids):
        return {
            "data": [
                {
                    "agent_id": id,
                    "agent_service_name": service,
                }
                for id in ids
                for service in ("nginx", "redis")
            ]
        }

    api = mock.Mock(spec=sdk.PlatformApi)
    api.platform_connection_index = mock.Mock(
        spec=sdk.PlatformApi.platform_connection_index,
        side_effect=get_connections,
    )
    api.platform_agent_index = mock.Mock(
        spec=sdk.PlatformApi.platform_agent_index, side_effect=platform_agent_index_stub
    )
    api.platform_connection_service_show = mock.Mock(
        spec=sdk.PlatformApi.platform_connection_service_show,
        return_value={"data": p2p_connection_services},
    )
    api.platform_agent_service_index = mock.Mock(
        spec=sdk.PlatformApi.platform_agent_service_index,
        side_effect=get_services,
    )
    return api


@pytest.mark.parametrize(
    "network,topology,result",
    [
        (
            {
                "network_name": "test",
                "network_id": 321,
                "network_disable_sdn_connections": False,
                "network_metadata": {
                    "network_type": "P2P",
                },
            },
            None,
            {
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
                "id": 321,
                "name": "test",
                "state": "present",
                "topology": "P2P",
            },
        ),
        (
            {
                "network_name": "test",
                "network_id": 123,
                "network_disable_sdn_connections": False,
                "network_metadata": {
                    "network_type": "MESH",
                },
            },
            None,
            {
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
                "id": 123,
                "name": "test",
                "state": "present",
                "topology": "MESH",
            },
        ),
        (
            {
                "network_name": "test",
                "network_id": 456,
                "network_disable_sdn_connections": False,
                "network_metadata": {
                    "network_type": "MESH",
                },
            },
            "P2P",
            {
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
                "ignore_configured_topology": True,
                "id": 456,
                "name": "test",
                "state": "present",
                "topology": "P2P",
            },
        ),
    ],
)
def test_export_network(api, all_agents, network, topology, result):
    ids = list(all_agents.keys())
    for id in ids:
        if id > 16:
            del all_agents[id]
    for id in all_agents:
        all_agents[id]["networks"] = [network]
    assert utils.export_network(api, all_agents, network, topology) == result
    api.platform_agent_service_index.assert_called_once()
