class PeerState:
    ABSENT = "absent"
    PRESENT = "present"


class PeerType:
    ENDPOINT = "endpoint"
    ID = "id"
    TAG = "tag"


class ConfigFields:
    CONNECTIONS = "connections"
    CONNECT_TO = "connect_to"
    ENDPOINTS = "endpoints"
    ID = "id"
    IGNORE_NETWORK_TOPOLOGY = "ignore_configured_topology"
    NAME = "name"
    PEER_TYPE = "type"
    SERVICES = "services"
    STATE = "state"
    TAGS = "tags"
    TOPOLOGY = "topology"
    USE_SDN = "use_sdn"


class Topology:
    P2P = "P2P"
    P2M = "P2M"
    MESH = "MESH"


ALLOWED_PEER_TYPES = (
    PeerType.ENDPOINT,
    PeerType.ID,
    PeerType.TAG,
)

ALLOWED_TOPOLOGIES = (
    Topology.P2P,
    Topology.P2M,
    Topology.MESH,
)
