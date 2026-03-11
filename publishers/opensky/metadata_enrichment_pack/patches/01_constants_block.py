# Drop-in constants and helper builders for `bootstrap_opensky.py`

OPENSKY_STATE_VECTORS_DOC = "https://openskynetwork.github.io/opensky-api/index.html#state-vectors"
OPENSKY_AUTH_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

def _bbox_label(config: dict) -> str:
    bbox = config["bounding_box"]
    return (
        f"lat {bbox['lamin']}-{bbox['lamax']}, "
        f"lon {bbox['lomin']}-{bbox['lomax']}"
    )

def _daily_budget_note(config: dict) -> str:
    bbox = config["bounding_box"]
    cadence = int(config.get("cadence_seconds", 300))
    req_per_day = int(86400 / cadence) if cadence > 0 else 0
    credit_cost = bbox.get("credit_cost_per_request", 1)
    total = req_per_day * credit_cost
    return (
        f"{req_per_day} requests/day at {credit_cost} credit(s)/request "
        f"for an estimated {total} credits/day."
    )

def _position_source_summary() -> str:
    return "ADS-B, ASTERIX, MLAT, FLARM"
