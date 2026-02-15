import requests

OSRM_BASE_URL = "https://router.project-osrm.org"


def osrm_road_distance(lat1, lon1, lat2, lon2, profile="driving"):
    """
    Returns road distance in KM using OSRM.
    profile: driving | walking | cycling
    Returns None on failure.
    """
    try:
        url = (
            f"{OSRM_BASE_URL}/route/v1/{profile}/"
            f"{lon1},{lat1};{lon2},{lat2}"
            f"?overview=false"
        )
        r = requests.get(url, timeout=10).json()

        if r.get("code") != "Ok":
            return None

        return r["routes"][0]["distance"] / 1000.0
    except Exception:
        return None


def osrm_duration_min(lat1, lon1, lat2, lon2, profile="driving"):
    """
    Returns OSRM duration in minutes (float). Returns None on failure.
    """
    try:
        url = (
            f"{OSRM_BASE_URL}/route/v1/{profile}/"
            f"{lon1},{lat1};{lon2},{lat2}"
            f"?overview=false"
        )
        r = requests.get(url, timeout=10).json()

        if r.get("code") != "Ok":
            return None

        return r["routes"][0]["duration"] / 60.0
    except Exception:
        return None


def osrm_steps(lat1, lon1, lat2, lon2, profile="walking"):
    """
    Returns a list of step instructions (strings) from OSRM.
    If OSRM doesn't return instructions, returns [].
    """
    try:
        url = (
            f"{OSRM_BASE_URL}/route/v1/{profile}/"
            f"{lon1},{lat1};{lon2},{lat2}"
            f"?steps=true&overview=false"
        )
        r = requests.get(url, timeout=10).json()

        if r.get("code") != "Ok":
            return []

        steps = r["routes"][0]["legs"][0]["steps"]
        # OSRM has "maneuver" objects; instruction might not always exist
        out = []
        for s in steps:
            instr = s.get("maneuver", {}).get("instruction")
            if instr:
                out.append(instr)
        return out
    except Exception:
        return []
