import functools
import os
from unittest import mock

import pytest
import syntropy_sdk as sdk
from click.testing import CliRunner
from syntropy_sdk import models


@pytest.fixture
def login_mock():
    with mock.patch(
        "syntropy_sdk.utils.login_with_access_token",
        autospec=True,
        returns="JWT access token",
    ) as the_mock:
        yield the_mock


@pytest.fixture
def env_mock():
    with mock.patch.dict(
        os.environ, {"SYNTROPY_API_SERVER": "server", "SYNTROPY_API_TOKEN": "token"}
    ) as the_mock:
        yield the_mock


@pytest.fixture
def api_lock_fix(env_mock):
    # NOTE: We don't restore __del__ for api client since there is a known issue with locking pool.
    sdk.ApiClient.__del__ = lambda x: x


@pytest.fixture
def runner(api_lock_fix):
    return CliRunner()


@pytest.fixture
def api_agents_search(
    platform_agent_search_stub,
):
    with mock.patch.object(
        sdk.AgentsApi,
        "v1_network_agents_search",
        autospec=True,
        side_effect=platform_agent_search_stub,
    ) as api:
        yield api


@pytest.fixture
def api_agents_get(
    platform_agent_get_stub,
):
    with mock.patch.object(
        sdk.AgentsApi,
        "v1_network_agents_get",
        autospec=True,
        side_effect=platform_agent_get_stub,
    ) as api:
        yield api


@pytest.fixture
def with_pagination():
    def wrapper(a):
        def f(*args, **kwargs):
            res = a(*args, **kwargs)
            return res.to_dict()

        return f

    with mock.patch.object(
        sdk.utils,
        "WithPagination",
        autospec=True,
        side_effect=wrapper,
    ) as api:
        yield api


@pytest.fixture
def with_batched():
    def wrapper(a):
        def f(*args, **kwargs):
            res = a(*args, **kwargs)
            return res.to_dict()

        return f

    with mock.patch.object(
        sdk.utils,
        "BatchedRequest",
        autospec=True,
        side_effect=wrapper,
    ) as api:
        yield api


@pytest.fixture
def with_batched_filter():
    def wrapper(a, b):
        def f(filter=None, **kwargs):
            filter = ",".join(str(i) for i in filter)
            res = a(filter=filter, **kwargs)
            return res

        return f

    with mock.patch.object(
        sdk.utils,
        "BatchedRequestFilter",
        autospec=True,
        side_effect=wrapper,
    ) as api:
        yield api


@pytest.fixture
def api_connections(
    p2p_connections,
):
    with mock.patch.object(
        sdk.ConnectionsApi,
        "v1_network_connections_get",
        autospec=True,
        return_value=models.V1NetworkConnectionsGetResponse(data=p2p_connections),
    ) as api:
        with mock.patch.object(
            sdk.ConnectionsApi,
            "v1_network_connections_search",
            autospec=True,
            return_value=models.V1NetworkConnectionsSearchResponse(
                data=p2p_connections
            ),
        ) as api:
            with mock.patch.object(
                sdk.ConnectionsApi,
                "v1_network_connections_create_p2_p",
                autospec=True,
            ) as api:
                with mock.patch.object(
                    sdk.ConnectionsApi,
                    "v1_network_connections_remove",
                    autospec=True,
                ) as api:
                    yield api


@pytest.fixture
def api_connections_services(
    p2p_connection_services,
):
    with mock.patch.object(
        sdk.ConnectionsApi,
        "v1_network_connections_get",
        autospec=True,
        return_value=models.V1NetworkConnectionsGetResponse(
            data=p2p_connection_services
        ),
    ):
        with mock.patch.object(
            sdk.ConnectionsApi,
            "v1_network_connections_search",
            autospec=True,
            return_value=models.V1NetworkConnectionsSearchResponse(
                data=p2p_connection_services
            ),
        ):
            with mock.patch.object(
                sdk.ConnectionsApi,
                "v1_network_connections_create_p2_p",
                autospec=True,
            ) as api:
                with mock.patch.object(
                    sdk.ConnectionsApi,
                    "v1_network_connections_remove",
                    autospec=True,
                ) as api:
                    yield api


@pytest.fixture
def api_services(connection_services_stub):
    def get_services(_, filter=None, **kwargs):
        return {
            "data": [
                {
                    "agent_id": int(id),
                    "agent_service_name": service,
                }
                for id in filter.split(",")
                for service in ("nginx", "redis")
            ]
        }

    with mock.patch.object(
        sdk.ConnectionsApi,
        "v1_network_connections_services_get",
        autospec=True,
        side_effect=connection_services_stub,
        # return_value=connection_services,
    ):
        with mock.patch.object(
            sdk.AgentsApi,
            "v1_network_agents_services_get",
            autospec=True,
            side_effect=get_services,
        ):
            with mock.patch.object(
                sdk.ConnectionsApi,
                "v1_network_connections_services_update",
                autospec=True,
            ):
                yield


@pytest.fixture
def test_yaml():
    return """---
# Create connection between IoT devices and IoT load balancer
name: edge_to_lb
state: present
use_sdn: true
# Connect devices only through SDN, skip public internet
use_public: false
# SDN connection count - how many failover paths to create
sdn_path_count: 3
# Latency threshold, %
latency_threshold: 10
# Packet loss threshold, %
pl_threshold: 1
topology: p2m
connections:
  de-aws-lb01:
    type: endpoint
# Allow IoT devices to access 2 services: haproxy load balancer and MQTT broker
    services: 
      - haproxy
      - mqtt
    connect_to:
      iot_device:
# Connect all endpoints tagged as iot_device
        type: tag
# Allow ssh connection from lb to devices
        services: ssh
"""


@pytest.fixture
def all_agents(platform_agent_get_stub):
    return {agent["agent_id"]: agent for agent in platform_agent_get_stub().data}


@pytest.fixture
def p2p_connections():
    return [
        {
            "agent_connection_group_id": 1,
            "agent_1": {
                "agent_id": 1,
                "agent_name": "de-hetzner-db01",
            },
            "agent_2": {
                "agent_id": 2,
                "agent_name": "de-aws-be01",
            },
        },
        {
            "agent_connection_group_id": 2,
            "agent_1": {
                "agent_id": 3,
                "agent_name": "de-aws-lb01",
            },
            "agent_2": {
                "agent_id": 4,
                "agent_name": "kr-aws-dns01",
            },
        },
    ]


@pytest.fixture
def p2m_connections():
    return [
        {
            "agent_connection_group_id": 3,
            "agent_1": {
                "agent_id": 1,
                "agent_name": "auto gen 1",
            },
            "agent_2": {
                "agent_id": 4,
                "agent_name": "auto gen 4",
            },
        },
        {
            "agent_connection_group_id": 4,
            "agent_1": {
                "agent_id": 1,
                "agent_name": "auto gen 1",
            },
            "agent_2": {
                "agent_id": 5,
                "agent_name": "auto gen 5",
            },
        },
        {
            "agent_connection_group_id": 5,
            "agent_1": {
                "agent_id": 1,
                "agent_name": "auto gen 1",
            },
            "agent_2": {
                "agent_id": 6,
                "agent_name": "auto gen 6",
            },
        },
    ]


@pytest.fixture
def mesh_connections():
    return [
        {
            "agent_connection_group_id": 6,
            "agent_1": {
                "agent_id": 13,
                "agent_name": "iot_mqtt",
            },
            "agent_2": {
                "agent_id": 10,
                "agent_name": "iot_device1",
            },
        },
        {
            "agent_connection_group_id": 7,
            "agent_1": {
                "agent_id": 13,
                "agent_name": "iot_mqtt",
            },
            "agent_2": {
                "agent_id": 11,
                "agent_name": "iot_device2",
            },
        },
        {
            "agent_connection_group_id": 8,
            "agent_1": {
                "agent_id": 13,
                "agent_name": "iot_mqtt",
            },
            "agent_2": {
                "agent_id": 10,
                "agent_name": "iot_device2",
            },
        },
        {
            "agent_connection_group_id": 9,
            "agent_1": {
                "agent_id": 13,
                "agent_name": "iot_mqtt",
            },
            "agent_2": {
                "agent_id": 12,
                "agent_name": "iot_device3",
            },
        },
        {
            "agent_connection_group_id": 10,
            "agent_1": {
                "agent_id": 10,
                "agent_name": "iot_device1",
            },
            "agent_2": {
                "agent_id": 12,
                "agent_name": "iot_device3",
            },
        },
    ]


@pytest.fixture
def created_connections():
    return [
        {
            "agent_connection_group_id": 10,
            "agent_1": {
                "agent_id": 13,
                "agent_name": "iot_mqtt",
            },
            "agent_2": {
                "agent_id": 10,
                "agent_name": "iot_device1",
            },
        },
        {
            "agent_connection_group_id": 7,
            "agent_1": {
                "agent_id": 13,
                "agent_name": "iot_mqtt",
            },
            "agent_2": {
                "agent_id": 11,
                "agent_name": "iot_device2",
            },
        },
        {
            "agent_connection_group_id": 8,
            "agent_1": {
                "agent_id": 13,
                "agent_name": "iot_mqtt",
            },
            "agent_2": {
                "agent_id": 14,
                "agent_name": "iot_device2",
            },
        },
    ]


@pytest.fixture
def create_agent_subnets():
    def func(id, name, subnets=24):
        if not isinstance(subnets, (list, tuple)):
            subnets = (subnets,)
        return {
            "agent_service_id": id,
            "agent_service_name": name,
            "agent_service_type": "DOCKER",
            "agent_service_is_active": True,
            "agent_service_subnets": [
                {
                    "agent_service_subnet_id": subnet,
                    "agent_service_subnet_ip": f"172.18.0.{subnet}",
                    "agent_service_subnet_is_active": True,
                }
                for subnet in subnets
            ],
        }

    return func


@pytest.fixture
def create_agent_connection_subnets():
    def func(subnets, enabled_flags):
        return [
            {
                "agent_connection_subnet_id": id,
                "agent_service_subnet_id": subnet,
                "agent_connection_subnet_status": "ERROR",
                "agent_connection_subnet_is_enabled": enabled,
                "agent_connection_subnet_error": "Some message",
            }
            for id, (subnet, enabled) in enumerate(zip(subnets, enabled_flags))
        ]

    return func


@pytest.fixture
def agent_connection_subnets_1():
    return [
        {
            "agent_connection_subnet_id": 14,
            "agent_service_subnet_id": 21,
            "agent_connection_subnet_status": "ERROR",
            "agent_connection_subnet_is_enabled": True,
            "agent_connection_subnet_error": "Agent '9' service ip: 172.18.0.5 intersects network CIDRS: 172.18.0.0/16",
        },
        {
            "agent_connection_subnet_id": 31,
            "agent_service_subnet_id": 22,
            "agent_connection_subnet_status": "PENDING",
            "agent_connection_subnet_is_enabled": False,
            "agent_connection_subnet_error": "Agent '22' service ip: 172.17.0.2 intersects network CIDRS: 172.17.0.0/16",
        },
        {
            "agent_connection_subnet_id": 40,
            "agent_service_subnet_id": 23,
            "agent_connection_subnet_status": "ERROR",
            "agent_connection_subnet_is_enabled": True,
            "agent_connection_subnet_error": "Agent '22' service ip: 172.19.0.3 intersects network CIDRS: 172.19.0.0/16",
        },
        {
            "agent_connection_subnet_id": 39,
            "agent_service_subnet_id": 24,
            "agent_connection_subnet_status": "ERROR",
            "agent_connection_subnet_is_enabled": True,
            "agent_connection_subnet_error": "Agent '22' service ip: 172.18.0.5 intersects network CIDRS: 172.18.0.0/16",
        },
        {
            "agent_connection_subnet_id": 38,
            "agent_service_subnet_id": 25,
            "agent_connection_subnet_status": "ERROR",
            "agent_connection_subnet_is_enabled": True,
            "agent_connection_subnet_error": "Agent '22' service ip: 172.18.0.5 intersects network CIDRS: 172.18.0.0/16",
        },
    ]


@pytest.fixture
def agent_connection_subnets_2():
    return [
        {
            "agent_connection_subnet_id": 14,
            "agent_service_subnet_id": 21,
            "agent_connection_subnet_status": "ERROR",
            "agent_connection_subnet_is_enabled": False,
            "agent_connection_subnet_error": "Agent '9' service ip: 172.18.0.5 intersects network CIDRS: 172.18.0.0/16",
        },
        {
            "agent_connection_subnet_id": 31,
            "agent_service_subnet_id": 22,
            "agent_connection_subnet_status": "PENDING",
            "agent_connection_subnet_is_enabled": False,
            "agent_connection_subnet_error": "Agent '22' service ip: 172.17.0.2 intersects network CIDRS: 172.17.0.0/16",
        },
        {
            "agent_connection_subnet_id": 40,
            "agent_service_subnet_id": 23,
            "agent_connection_subnet_status": "ERROR",
            "agent_connection_subnet_is_enabled": True,
            "agent_connection_subnet_error": "Agent '22' service ip: 172.19.0.3 intersects network CIDRS: 172.19.0.0/16",
        },
        {
            "agent_connection_subnet_id": 39,
            "agent_service_subnet_id": 24,
            "agent_connection_subnet_status": "ERROR",
            "agent_connection_subnet_is_enabled": True,
            "agent_connection_subnet_error": "Agent '22' service ip: 172.18.0.5 intersects network CIDRS: 172.18.0.0/16",
        },
        {
            "agent_connection_subnet_id": 38,
            "agent_service_subnet_id": 25,
            "agent_connection_subnet_status": "ERROR",
            "agent_connection_subnet_is_enabled": False,
            "agent_connection_subnet_error": "Agent '22' service ip: 172.18.0.5 intersects network CIDRS: 172.18.0.0/16",
        },
    ]


@pytest.fixture
def connection_services():
    return {
        "agent_connection_group_id": 169,
        "agent_connection_subnets": [],
        "agent_1": {
            "agent_id": 9,
            "agent_services": [
                {
                    "agent_service_id": 16,
                    "agent_service_name": "nats-streaming",
                    "agent_service_type": "DOCKER",
                    "agent_service_is_active": True,
                    "agent_service_subnets": [
                        {
                            "agent_service_subnet_id": 21,
                            "agent_service_subnet_ip": "172.18.0.11",
                            "agent_service_subnet_is_active": True,
                        },
                        {
                            "agent_service_subnet_id": 22,
                            "agent_service_subnet_ip": "172.17.0.3",
                            "agent_service_subnet_is_active": True,
                        },
                    ],
                },
                {
                    "agent_service_id": 21,
                    "agent_service_name": "sdn-bi",
                    "agent_service_type": "DOCKER",
                    "agent_service_is_active": True,
                    "agent_service_subnets": [
                        {
                            "agent_service_subnet_id": 23,
                            "agent_service_subnet_ip": "172.18.0.5",
                            "agent_service_subnet_is_active": True,
                        }
                    ],
                },
                {
                    "agent_service_id": 123,
                    "agent_service_name": "missing-subnet",
                    "agent_service_type": "DOCKER",
                    "agent_service_is_active": True,
                    "agent_service_subnets": [
                        {
                            "agent_service_subnet_id": 123,
                            "agent_service_subnet_ip": "172.18.0.5",
                            "agent_service_subnet_is_active": True,
                        }
                    ],
                },
            ],
        },
        "agent_2": {
            "agent_id": 22,
            "agent_services": [
                {
                    "agent_service_id": 13,
                    "agent_service_name": "sdn-pgadmin",
                    "agent_service_type": "DOCKER",
                    "agent_service_is_active": True,
                    "agent_service_subnets": [
                        {
                            "agent_service_subnet_id": 24,
                            "agent_service_subnet_ip": "172.18.0.10",
                            "agent_service_subnet_is_active": True,
                        }
                    ],
                },
                {
                    "agent_service_id": 18,
                    "agent_service_name": "streaming",
                    "agent_service_type": "DOCKER",
                    "agent_service_is_active": True,
                    "agent_service_subnets": [
                        {
                            "agent_service_subnet_id": 25,
                            "agent_service_subnet_ip": "172.17.0.3",
                            "agent_service_subnet_is_active": True,
                        },
                    ],
                },
            ],
        },
    }


@pytest.fixture
def p2p_connection_services(
    connection_services, agent_connection_subnets_1, agent_connection_subnets_2
):
    return [
        {
            **connection_services,
            "agent_connection_group_id": 1,
            "agent_connection_subnets": agent_connection_subnets_1,
        },
        {
            **connection_services,
            "agent_connection_group_id": 2,
            "agent_connection_subnets": agent_connection_subnets_2,
        },
    ]


@pytest.fixture
def config_connections():
    return {
        "agent 0": {
            "services": ["a", "b"],
        },
        "agent 1": {
            "services": ["b", "c"],
        },
        "agent 2": {
            "services": ["d", "e"],
        },
        "agent 3": {
            "services": ["f", "g"],
        },
        "agent 4": {
            "services": ["h", "i"],
        },
    }


@pytest.fixture
def index_connections_ex():
    return {"data": []}


@pytest.fixture
def platform_agent_index_ex():
    return {"data": []}


@pytest.fixture
def platform_agent_get_stub():
    def func(*args, **kwargs):
        return models.V1NetworkAgentsGetResponse(
            data=[
                {
                    "agent_name": f"auto gen {i}",
                    "agent_id": i,
                    "agent_tags": [],
                }
                for i in range(256)
            ]
        )

    return func


@pytest.fixture
def platform_agent_search_stub():
    def func(_, body, **kwargs):
        if body.filter.agent_name:
            for i in range(30):
                if f"agent{i}" in body.filter.agent_name:
                    return {"data": [{"agent_name": f"agent{i}", "agent_id": i}]}
        elif body.filter.agent_tag_name:
            return {
                "data": [
                    {
                        "agent_name": f"filter - {body.filter.agent_tag_name[0]} {i}",
                        "agent_id": 10 * len(body.filter.agent_tag_name[0]) + i,
                    }
                    for i in range(3)
                ]
            }
        return {"data": []}

    return func


@pytest.fixture
def connection_services_stub(
    connection_services, agent_connection_subnets_1, agent_connection_subnets_2
):
    def func(_, filter=None, _preload_content=None):
        return {
            "data": [
                {
                    **connection_services,
                    "agent_connection_group_id": int(id),
                    "agent_connection_subnets": agent_connection_subnets_2
                    if int(id) % 2
                    else agent_connection_subnets_1,
                }
                for id in filter.split(",")
            ]
        }

    return func
