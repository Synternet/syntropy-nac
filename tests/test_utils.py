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
    index_agents_stub,
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

    api = mock.Mock(spec=sdk.PlatformApi)
    api.index_connections = mock.Mock(
        spec=sdk.PlatformApi.index_connections,
        side_effect=get_connections,
    )
    api.index_agents = mock.Mock(
        spec=sdk.PlatformApi.index_agents, side_effect=index_agents_stub
    )
    api.get_connection_services = mock.Mock(
        spec=sdk.PlatformApi.get_connection_services,
        return_value={"data": p2p_connection_services},
    )
    return api


@pytest.mark.parametrize(
    "network,topology,result",
    [
        (
            {
                "network_name": "test",
                "network_id": 321,
                "network_type": "POINT_TO_POINT",
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
                "network_type": "POINT_TO_POINT",
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
                "network_type": "MESH",
                "network_disable_sdn_connections": False,
            },
            None,
            {
                "connections": {
                    "auto gen 10": {
                        "id": 10,
                        "services": [],
                        "state": "present",
                        "type": "endpoint",
                    },
                    "auto gen 11": {
                        "id": 11,
                        "services": [],
                        "state": "present",
                        "type": "endpoint",
                    },
                    "auto gen 12": {
                        "id": 12,
                        "services": [],
                        "state": "present",
                        "type": "endpoint",
                    },
                    "auto gen 13": {
                        "id": 13,
                        "services": [],
                        "state": "present",
                        "type": "endpoint",
                    },
                },
                "id": 456,
                "name": "test",
                "state": "present",
                "topology": "MESH",
            },
        ),
        (
            {
                "network_name": "test",
                "network_id": 456,
                "network_type": "MESH",
                "network_disable_sdn_connections": False,
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
                "id": 456,
                "name": "test",
                "state": "present",
                "topology": "P2P",
            },
        ),
    ],
)
def test_export_network(api, all_agents, network, topology, result):
    assert utils.export_network(api, all_agents, network, topology) == result
