DEFAULT_JOURNEY_TYPE = "boarding"
VALID_JOURNEY_TYPES = {"boarding", "arrival", "connection"}
DATABASE_CONNECT_TIMEOUT_SECONDS = 5


class RouteMode:
    FASTEST = "fastest"
    ACCESSIBLE = "accessible"
    WITH_STOP = "with_stop"


class EdgeType:
    CORRIDOR = "corridor"
    RAMP = "ramp"
    STAIRS = "stairs"
    ESCALATOR = "escalator"
    ELEVATOR = "elevator"
    SECURITY = "security"
    BOARDING = "boarding"
    RESTRICTED_TRANSITION = "restricted_transition"


class NodeZone:
    PUBLIC = "public"
    CHECKIN = "checkin"
    SECURITY = "security"
    DOMESTIC_AIRSIDE = "domestic_airside"
    INTERNATIONAL_AIRSIDE = "international_airside"
    CONNECTION = "connection"
    BAGGAGE_CLAIM = "baggage_claim"
    RESTRICTED = "restricted"


VALID_ROUTE_MODES = {RouteMode.FASTEST, RouteMode.ACCESSIBLE, RouteMode.WITH_STOP}
VALID_EDGE_TYPES = {
    EdgeType.CORRIDOR,
    EdgeType.RAMP,
    EdgeType.STAIRS,
    EdgeType.ESCALATOR,
    EdgeType.ELEVATOR,
    EdgeType.SECURITY,
    EdgeType.BOARDING,
    EdgeType.RESTRICTED_TRANSITION,
}
VALID_NODE_ZONES = {
    NodeZone.PUBLIC,
    NodeZone.CHECKIN,
    NodeZone.SECURITY,
    NodeZone.DOMESTIC_AIRSIDE,
    NodeZone.INTERNATIONAL_AIRSIDE,
    NodeZone.CONNECTION,
    NodeZone.BAGGAGE_CLAIM,
    NodeZone.RESTRICTED,
}
