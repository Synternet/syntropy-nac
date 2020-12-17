import syntropy_sdk as sdk

from syntropynac import fields, transform


def export_network(api, all_agents, network, topology):
    net = transform.transform_network(network)
    connections_filter = f"networks[]:{net['id']}"
    connections = sdk.utils.WithRetry(api.index_connections)(
        filter=connections_filter, take=sdk.utils.TAKE_MAX_ITEMS_PER_CALL
    )["data"]
    ids = [connection["agent_connection_id"] for connection in connections]
    if ids:
        connections_services = sdk.utils.BatchedRequest(
            api.get_connection_services,
            max_payload_size=sdk.utils.MAX_QUERY_FIELD_SIZE,
        )(ids)["data"]
        connection_services = {
            connection["agent_connection_id"]: connection
            for connection in connections_services
        }
    net_connections = [
        {
            **connection,
            "agent_connection_services": connection_services.get(
                connection["agent_connection_id"], {}
            ),
        }
        for connection in connections
        if connection["network"]["network_id"] == net["id"]
    ]
    transformed_connections = transform.transform_connections(
        all_agents,
        net_connections,
        topology if topology else net[fields.ConfigFields.TOPOLOGY],
    )
    if transformed_connections:
        net[fields.ConfigFields.CONNECTIONS] = transformed_connections
    if topology:
        net["topology"] = topology
    del net["use_sdn"]

    return net
