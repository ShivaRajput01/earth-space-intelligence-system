"""
ESIDS Physics Engine — Orbital mechanics, Mars communications, TLE propagation
"""
import datetime, math, requests
import numpy as np
from scipy.optimize import brentq

# ── Constants ─────────────────────────────────────────────────────────────────
GM_EARTH = 398600.4418  # km³/s²
RE = 6371.0  # km
C = 299792.458  # km/s (speed of light)
EARTH_ROT = 7.2921159e-5  # rad/s

# India ground stations
INDIA_STATIONS = {
    "ISRO Bengaluru": (12.9716, 77.5946),
    "ISRO Lucknow": (26.8467, 80.9462),
    "ISRO Mauritius": (-20.2908, 57.5534),
    "ISRO Biak": (-0.9119, 136.0894),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Kolkata": (22.5726, 88.3639),
}


# ── TLE Data Fetching ─────────────────────────────────────────────────────────
def fetch_tle_data_from_groups(groups=None, cache_path=None):
    """
    Fetch real TLE data from multiple Celestrak groups.
    
    Args:
        groups: List of TLE groups to fetch. If None, uses comprehensive default list.
        cache_path: Optional file path to cache TLE data
    
    Returns:
        List of (name, line1, line2) tuples (deduplicated)
    """
    if groups is None:
        # Comprehensive list of Celestrak groups for 1000+ satellites
        groups = [
            "active",           # Active satellites
            "stations",         # Space stations (ISS, Tiangong)
            "visual",           # Bright satellites
            "gps-ops",          # GPS operational
            "glo-ops",          # GLONASS operational
            "galileo",          # Galileo
            "beidou",           # BeiDou
            "geo",              # Geostationary
            "weather",          # Weather satellites
            "noaa",             # NOAA satellites
            "goes",             # GOES satellites
            "resource",         # Earth resources satellites
            "sarsat",           # Search & rescue
            "dmc",              # Disaster monitoring
            "tdrss",            # Tracking & data relay
            "argos",            # ARGOS data collection
            "planet",           # Planet Labs
            "spire",            # Spire Global
            "oneweb",           # OneWeb
            "starlink",         # Starlink
            "iridium",          # Iridium
            "iridium-NEXT",     # Iridium NEXT
            "orbcomm",          # ORBCOMM
            "globalstar",       # Globalstar
            "amateur",          # Amateur radio
            "x-comm",           # Experimental communications
            "other-comm",       # Other communications
            "satnogs",          # SatNOGS
            "gorizont",         # Gorizont
            "raduga",           # Raduga
            "molniya",          # Molniya
        ]
    
    all_tles = []
    seen_norad_ids = set()
    
    for group in groups:
        url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
        
        try:
            print(f"  Fetching from {group}...", end=" ")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            group_tles = []
            
            # TLE format: 3 lines per satellite (name, line1, line2)
            for i in range(0, len(lines)-2, 3):
                name = lines[i].strip()
                line1 = lines[i+1].strip()
                line2 = lines[i+2].strip()
                
                if line1.startswith('1 ') and line2.startswith('2 '):
                    # Extract NORAD ID for deduplication
                    try:
                        norad_id = int(line1[2:7])
                        if norad_id not in seen_norad_ids:
                            seen_norad_ids.add(norad_id)
                            group_tles.append((name, line1, line2))
                    except:
                        pass
            
            all_tles.extend(group_tles)
            print(f"{len(group_tles)} satellites")
            
        except Exception as e:
            print(f"Failed ({e})")
            continue
    
    print(f"\n  Total unique satellites: {len(all_tles)}")
    
    # Cache if requested
    if cache_path and all_tles:
        try:
            with open(cache_path, 'w') as f:
                for name, l1, l2 in all_tles:
                    f.write(f"{name}\n{l1}\n{l2}\n")
            print(f"  Cached to {cache_path}")
        except Exception as e:
            print(f"  Cache failed: {e}")
    
    return all_tles


def fetch_tle_data(group="active", cache_path=None):
    """
    Legacy function for single-group fetching.
    Use fetch_tle_data_from_groups() for comprehensive data.
    """
    url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
    
    try:
        print(f"Fetching TLE data from {url}...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        lines = response.text.strip().split('\n')
        tles = []
        
        # TLE format: 3 lines per satellite (name, line1, line2)
        for i in range(0, len(lines)-2, 3):
            name = lines[i].strip()
            line1 = lines[i+1].strip()
            line2 = lines[i+2].strip()
            
            if line1.startswith('1 ') and line2.startswith('2 '):
                tles.append((name, line1, line2))
        
        print(f"Fetched {len(tles)} TLE records")
        
        # Cache if requested
        if cache_path:
            with open(cache_path, 'w') as f:
                for name, l1, l2 in tles:
                    f.write(f"{name}\n{l1}\n{l2}\n")
        
        return tles
        
    except Exception as e:
        print(f"Error fetching TLE data: {e}")
        # Return empty list if fetch fails
        return []


def parse_tle(name, line1, line2):
    """Parse TLE into orbital elements"""
    try:
        norad_id = int(line1[2:7])
        epoch_year = int(line1[18:20])
        epoch_day = float(line1[20:32])
        
        # Convert epoch to datetime
        year = 2000 + epoch_year if epoch_year < 57 else 1900 + epoch_year
        epoch = datetime.datetime(year, 1, 1) + datetime.timedelta(days=epoch_day-1)
        
        # Line 2 elements
        incl = float(line2[8:16])  # degrees
        raan = float(line2[17:25])  # degrees
        ecc_str = "0." + line2[26:33].replace(' ', '0')
        ecc = float(ecc_str)
        argp = float(line2[34:42])  # degrees
        mean_anom = float(line2[43:51])  # degrees
        mean_motion = float(line2[52:63])  # revs/day
        
        # Compute semi-major axis from mean motion
        n = mean_motion * 2 * math.pi / 86400  # rad/s
        a = (GM_EARTH / (n**2))**(1/3)  # km
        
        return {
            "name": name,
            "norad_id": norad_id,
            "epoch": epoch.isoformat(),
            "a": a,
            "ecc": ecc,
            "incl": incl,
            "raan": raan,
            "argp": argp,
            "mean_anom": mean_anom,
            "mean_motion": mean_motion,
        }
    except Exception as e:
        print(f"Error parsing TLE {name}: {e}")
        return None


def propagate_sgp4_simplified(tle_dict, dt):
    """
    Simplified SGP4-style propagation (Keplerian approximation)
    Returns lat, lon, alt in degrees and km
    """
    try:
        epoch = datetime.datetime.fromisoformat(tle_dict["epoch"])
        # Ensure epoch has timezone info
        if epoch.tzinfo is None:
            epoch = epoch.replace(tzinfo=datetime.timezone.utc)
        
        delta_t = (dt - epoch).total_seconds()
        
        # Mean motion
        n = tle_dict["mean_motion"] * 2 * math.pi / 86400  # rad/s
        
        # Propagate mean anomaly
        M = (tle_dict["mean_anom"] * math.pi / 180 + n * delta_t) % (2 * math.pi)
        
        # Solve Kepler's equation (M = E - e*sin(E))
        ecc = tle_dict["ecc"]
        E = M
        for _ in range(10):
            E = M + ecc * math.sin(E)
        
        # True anomaly
        nu = 2 * math.atan2(
            math.sqrt(1 + ecc) * math.sin(E / 2),
            math.sqrt(1 - ecc) * math.cos(E / 2)
        )
        
        # Radius
        a = tle_dict["a"]
        r = a * (1 - ecc * math.cos(E))
        
        # Position in orbital plane
        x_orb = r * math.cos(nu)
        y_orb = r * math.sin(nu)
        
        # Convert to ECI
        incl = tle_dict["incl"] * math.pi / 180
        raan = tle_dict["raan"] * math.pi / 180
        argp = tle_dict["argp"] * math.pi / 180
        
        # Perifocal to ECI
        cos_raan, sin_raan = math.cos(raan), math.sin(raan)
        cos_incl, sin_incl = math.cos(incl), math.sin(incl)
        cos_argp, sin_argp = math.cos(argp), math.sin(argp)
        
        # Transform
        x_eci = (cos_raan * cos_argp - sin_raan * sin_argp * cos_incl) * x_orb + \
                (-cos_raan * sin_argp - sin_raan * cos_argp * cos_incl) * y_orb
        y_eci = (sin_raan * cos_argp + cos_raan * sin_argp * cos_incl) * x_orb + \
                (-sin_raan * sin_argp + cos_raan * cos_argp * cos_incl) * y_orb
        z_eci = (sin_incl * sin_argp) * x_orb + (sin_incl * cos_argp) * y_orb
        
        # Convert to lat/lon (simplified - ignoring precession)
        lon = math.atan2(y_eci, x_eci) * 180 / math.pi
        lat = math.asin(z_eci / r) * 180 / math.pi
        alt = r - RE
        
        # Compute velocity
        vel = math.sqrt(GM_EARTH / r)
        
        return {
            "lat": lat,
            "lon": lon,
            "altitude_km": alt,
            "velocity_kms": vel,
        }
        
    except Exception as e:
        print(f"Propagation error for {tle_dict.get('name', 'unknown')}: {e}")
        return None


# ── Mars Communications Delay ─────────────────────────────────────────────────
def earth_mars_distance_km(dt):
    """
    Compute Earth-Mars distance using simplified ephemeris.
    Based on Keplerian orbits (good approximation for delay calculations)
    """
    # Julian date
    jd = dt.toordinal() + 1721424.5 + dt.hour / 24 + dt.minute / 1440 + dt.second / 86400
    
    # Days since J2000
    d = jd - 2451545.0
    
    # Earth orbital elements (simplified)
    e_earth = 0.0167
    a_earth = 149.6e6  # km
    L_earth = (280.460 + 0.9856474 * d) % 360
    
    # Mars orbital elements
    e_mars = 0.0934
    a_mars = 227.9e6  # km
    L_mars = (355.433 + 0.5240212 * d) % 360
    
    # Convert to radians
    L_earth_rad = L_earth * math.pi / 180
    L_mars_rad = L_mars * math.pi / 180
    
    # Simplified position (circular approximation for quick computation)
    x_earth = a_earth * math.cos(L_earth_rad)
    y_earth = a_earth * math.sin(L_earth_rad)
    
    x_mars = a_mars * math.cos(L_mars_rad)
    y_mars = a_mars * math.sin(L_mars_rad)
    
    # Distance
    dist_km = math.sqrt((x_mars - x_earth)**2 + (y_mars - y_earth)**2)
    
    return dist_km


def earth_mars_delay(dt):
    """
    Compute communication delay to Mars
    Returns dict with delay_min, distance_km, is_blackout
    """
    dist_km = earth_mars_distance_km(dt)
    delay_sec = dist_km / C
    delay_min = delay_sec / 60
    
    # Blackout occurs during superior conjunction (Earth-Sun-Mars alignment)
    # Simplified: if distance > 380M km (near max distance)
    is_blackout = dist_km > 380e6
    
    return {
        "timestamp": dt.isoformat(),
        "distance_km": round(dist_km, 2),
        "delay_min": round(delay_min, 6),
        "is_blackout": is_blackout,
    }


def generate_mars_2025(step_hours=6):
    """Generate Mars delay for entire year 2025"""
    records = []
    start = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    
    current = start
    while current < end:
        rec = earth_mars_delay(current)
        records.append(rec)
        current += datetime.timedelta(hours=step_hours)
    
    return records


# ── Ground Pass Predictions ───────────────────────────────────────────────────
def predict_passes(tle_dict, station_name, duration_h=24):
    """
    Predict satellite passes over a ground station
    Returns list of pass events
    """
    if station_name not in INDIA_STATIONS:
        return []
    
    lat_gs, lon_gs = INDIA_STATIONS[station_name]
    passes = []
    
    now = datetime.datetime.now(datetime.timezone.utc)
    end_time = now + datetime.timedelta(hours=duration_h)
    
    current = now
    step = datetime.timedelta(minutes=1)
    
    in_pass = False
    pass_start = None
    max_elev = 0
    
    while current < end_time:
        pos = propagate_sgp4_simplified(tle_dict, current)
        
        if pos:
            # Compute elevation angle (simplified)
            dlat = pos["lat"] - lat_gs
            dlon = pos["lon"] - lon_gs
            dist_deg = math.sqrt(dlat**2 + dlon**2)
            
            # Simple elevation estimate
            elev = 90 - dist_deg * 10  # Very rough approximation
            
            if elev > 10:  # Above horizon
                if not in_pass:
                    in_pass = True
                    pass_start = current
                    max_elev = elev
                else:
                    max_elev = max(max_elev, elev)
            else:
                if in_pass:
                    # Pass ended
                    duration = (current - pass_start).total_seconds()
                    passes.append({
                        "start": pass_start.isoformat(),
                        "duration_sec": int(duration),
                        "max_elevation_deg": round(max_elev, 1),
                        "station": station_name,
                    })
                    in_pass = False
        
        current += step
    
    return passes


# ── Conjunction Detection ─────────────────────────────────────────────────────
def find_conjunction(tle1, tle2, dt):
    """
    Check if two satellites are in close proximity
    Returns miss distance in km
    """
    pos1 = propagate_sgp4_simplified(tle1, dt)
    pos2 = propagate_sgp4_simplified(tle2, dt)
    
    if not pos1 or not pos2:
        return None
    
    # Convert to Cartesian (very simplified)
    r1 = RE + pos1["altitude_km"]
    r2 = RE + pos2["altitude_km"]
    
    lat1_rad = pos1["lat"] * math.pi / 180
    lon1_rad = pos1["lon"] * math.pi / 180
    lat2_rad = pos2["lat"] * math.pi / 180
    lon2_rad = pos2["lon"] * math.pi / 180
    
    x1 = r1 * math.cos(lat1_rad) * math.cos(lon1_rad)
    y1 = r1 * math.cos(lat1_rad) * math.sin(lon1_rad)
    z1 = r1 * math.sin(lat1_rad)
    
    x2 = r2 * math.cos(lat2_rad) * math.cos(lon2_rad)
    y2 = r2 * math.cos(lat2_rad) * math.sin(lon2_rad)
    z2 = r2 * math.sin(lat2_rad)
    
    dist = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    
    return dist


# ── Synthetic TLE Generation (for testing) ────────────────────────────────────
def make_synthetic_tle(name, norad_id, alt_km=550, incl_deg=53, raan_deg=0):
    """Generate a synthetic TLE for testing"""
    # Compute mean motion from altitude
    a = RE + alt_km
    n_rad_s = math.sqrt(GM_EARTH / (a**3))
    mean_motion = n_rad_s * 86400 / (2 * math.pi)  # revs/day
    
    # Create TLE lines
    epoch = datetime.datetime.now(datetime.timezone.utc)
    year = epoch.year % 100
    day_of_year = epoch.timetuple().tm_yday
    day_fraction = (epoch.hour + epoch.minute/60 + epoch.second/3600) / 24
    epoch_str = f"{year:02d}{day_of_year:03d}.{int(day_fraction * 100000000):08d}"
    
    line1 = f"1 {norad_id:05d}U 25001A   {epoch_str} .00000000  00000-0  00000-0 0    00"
    line2 = f"2 {norad_id:05d} {incl_deg:7.4f} {raan_deg:7.4f} 0000000   0.0000   0.0000 {mean_motion:11.8f}    00"
    
    # Add checksum
    def checksum(line):
        s = 0
        for c in line[0:68]:
            if c.isdigit():
                s += int(c)
            elif c == '-':
                s += 1
        return str(s % 10)
    
    line1 = line1[:68] + checksum(line1)
    line2 = line2[:68] + checksum(line2)
    
    return name, line1, line2


# ── Ground Track ──────────────────────────────────────────────────────────────
def ground_track(tle_dict, num_points=100):
    """Generate ground track points for visualization"""
    epoch = datetime.datetime.fromisoformat(tle_dict["epoch"])
    period_sec = 86400 / tle_dict["mean_motion"]
    
    points = []
    for i in range(num_points):
        dt = epoch + datetime.timedelta(seconds=i * period_sec / num_points)
        pos = propagate_sgp4_simplified(tle_dict, dt)
        if pos:
            points.append((pos["lat"], pos["lon"]))
    
    return points
