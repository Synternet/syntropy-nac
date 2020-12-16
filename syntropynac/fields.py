class PeerState:
    PRESENT = "present"
    ABSENT = "absent"


class PeerType:
    ENDPOINT = "endpoint"
    TAG = "tag"
    ID = "id"


class ConfigFields:
    ID = "id"
    NAME = "name"
    STATE = "state"
    SERVICES = "services"
    TOPOLOGY = "topology"
    CONNECT_TO = "connect_to"
    CONNECTIONS = "connections"
    PEER_TYPE = "type"
    USE_SDN = "use_sdn"
    IGNORE_NETWORK_TOPOLOGY = "ignore_configured_topology"
