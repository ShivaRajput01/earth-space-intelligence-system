# 📡 ESIDS v7.1 — Celestrak Group Reference Card

## All 32 Groups Being Fetched

Your system automatically fetches from these URLs:

### 🌐 General Categories
```
1.  https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle
2.  https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle
3.  https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle
```

### 🛰️ Navigation (GNSS)
```
4.  https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle
5.  https://celestrak.org/NORAD/elements/gp.php?GROUP=glo-ops&FORMAT=tle
6.  https://celestrak.org/NORAD/elements/gp.php?GROUP=galileo&FORMAT=tle
7.  https://celestrak.org/NORAD/elements/gp.php?GROUP=beidou&FORMAT=tle
```

### 📡 Communications
```
8.  https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle
9.  https://celestrak.org/NORAD/elements/gp.php?GROUP=oneweb&FORMAT=tle
10. https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium&FORMAT=tle
11. https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium-NEXT&FORMAT=tle
12. https://celestrak.org/NORAD/elements/gp.php?GROUP=orbcomm&FORMAT=tle
13. https://celestrak.org/NORAD/elements/gp.php?GROUP=globalstar&FORMAT=tle
14. https://celestrak.org/NORAD/elements/gp.php?GROUP=x-comm&FORMAT=tle
15. https://celestrak.org/NORAD/elements/gp.php?GROUP=other-comm&FORMAT=tle
16. https://celestrak.org/NORAD/elements/gp.php?GROUP=gorizont&FORMAT=tle
```

### 🌦️ Weather & Earth Observation
```
17. https://celestrak.org/NORAD/elements/gp.php?GROUP=geo&FORMAT=tle
18. https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle
19. https://celestrak.org/NORAD/elements/gp.php?GROUP=noaa&FORMAT=tle
20. https://celestrak.org/NORAD/elements/gp.php?GROUP=goes&FORMAT=tle
21. https://celestrak.org/NORAD/elements/gp.php?GROUP=resource&FORMAT=tle
22. https://celestrak.org/NORAD/elements/gp.php?GROUP=dmc&FORMAT=tle
23. https://celestrak.org/NORAD/elements/gp.php?GROUP=planet&FORMAT=tle
24. https://celestrak.org/NORAD/elements/gp.php?GROUP=spire&FORMAT=tle
```

### 🔧 Special Services
```
25. https://celestrak.org/NORAD/elements/gp.php?GROUP=sarsat&FORMAT=tle
26. https://celestrak.org/NORAD/elements/gp.php?GROUP=tdrss&FORMAT=tle
27. https://celestrak.org/NORAD/elements/gp.php?GROUP=argos&FORMAT=tle
```

### 📻 Amateur & Experimental
```
28. https://celestrak.org/NORAD/elements/gp.php?GROUP=amateur&FORMAT=tle
29. https://celestrak.org/NORAD/elements/gp.php?GROUP=satnogs&FORMAT=tle
```

### 🇷🇺 Russian Systems
```
30. https://celestrak.org/NORAD/elements/gp.php?GROUP=raduga&FORMAT=tle
31. https://celestrak.org/NORAD/elements/gp.php?GROUP=molniya&FORMAT=tle
```

---

## 📊 Expected Satellite Counts

| # | Group | Satellites | Description |
|---|-------|-----------|-------------|
| 1 | active | 5,000+ | All currently active satellites |
| 2 | stations | 3-5 | ISS, Tiangong, etc. |
| 3 | visual | 200+ | Bright satellites visible to naked eye |
| 4 | gps-ops | 31 | GPS operational constellation |
| 5 | glo-ops | 24 | GLONASS operational |
| 6 | galileo | 28 | Galileo navigation |
| 7 | beidou | 35 | BeiDou navigation |
| 8 | starlink | 5,100+ | SpaceX Starlink broadband |
| 9 | oneweb | 600+ | OneWeb internet |
| 10 | iridium | 66 | Iridium legacy |
| 11 | iridium-NEXT | 75 | Iridium NEXT generation |
| 12 | orbcomm | 31 | ORBCOMM IoT |
| 13 | globalstar | 24 | Globalstar phones |
| 14 | x-comm | 10-20 | Experimental communications |
| 15 | other-comm | 100+ | Other commercial |
| 16 | gorizont | 5-10 | Russian geostationary |
| 17 | geo | 500+ | All geostationary |
| 18 | weather | 20+ | Weather satellites |
| 19 | noaa | 15-20 | NOAA operational |
| 20 | goes | 4 | GOES weather |
| 21 | resource | 40+ | Earth resources |
| 22 | dmc | 8 | Disaster monitoring |
| 23 | planet | 200+ | Planet Labs imaging |
| 24 | spire | 100+ | Spire weather/AIS |
| 25 | sarsat | 10-15 | Search & rescue |
| 26 | tdrss | 8-12 | Tracking & data relay |
| 27 | argos | 10-15 | Data collection |
| 28 | amateur | 50+ | Amateur radio |
| 29 | satnogs | 60+ | SatNOGS network |
| 30 | raduga | 5-8 | Raduga satellites |
| 31 | molniya | 3-5 | Molniya orbits |

**Total Unique: ~6,200 satellites** (after deduplication)

---

## 🔄 Manual Testing

### Test Single Group
```bash
curl "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle" | head -30
```

### Test Multiple Groups (Python)
```python
from backend.physics_engine import fetch_tle_data_from_groups

# All groups (default)
all_tles = fetch_tle_data_from_groups()
print(f"Total: {len(all_tles)}")

# Specific groups
nav_tles = fetch_tle_data_from_groups(
    groups=["gps-ops", "galileo", "glo-ops", "beidou"]
)
print(f"Navigation: {len(nav_tles)}")

# Communication megaconstellations only
mega_tles = fetch_tle_data_from_groups(
    groups=["starlink", "oneweb"]
)
print(f"Megaconstellations: {len(mega_tles)}")
```

---

## 📝 TLE Format Reference

Each satellite has 3 lines:

```
Line 0: Satellite Name
ISS (ZARYA)

Line 1: Orbital Elements (Part 1)
1 25544U 98067A   26106.50000000  .00016717  00000-0  10270-3 0  9992

Line 2: Orbital Elements (Part 2)  
2 25544  51.6409 247.4627 0001538  65.4785  94.8934 15.54225995 12345
```

### Key Elements
- **NORAD ID**: 25544 (unique identifier)
- **Inclination**: 51.6409° (orbit angle)
- **RAAN**: 247.4627° (right ascension)
- **Eccentricity**: 0.0001538 (orbit shape)
- **Argument of Perigee**: 65.4785°
- **Mean Anomaly**: 94.8934° (position in orbit)
- **Mean Motion**: 15.54225995 (orbits per day)

---

## 🎯 Performance Tips

### Optimize for Speed
```python
# Only fetch groups you need
essential_groups = [
    "stations",    # ISS, Tiangong
    "gps-ops",     # GPS
    "starlink",    # Starlink (if analyzing)
]

tles = fetch_tle_data_from_groups(groups=essential_groups)
```

### Cache Management
```bash
# Check cache
cat data/tle_cache.txt | head -30

# Refresh cache (delete and re-run)
rm data/tle_cache.txt
python run_pipeline.py

# Cache location
ls -lh data/tle_cache.txt
```

---

## 🔍 Constellation-Specific Groups

### Want Only GPS?
```python
gps_tles = fetch_tle_data_from_groups(groups=["gps-ops"])
```

### Want All GNSS?
```python
gnss_tles = fetch_tle_data_from_groups(
    groups=["gps-ops", "glo-ops", "galileo", "beidou"]
)
```

### Want Starlink Only?
```python
starlink_tles = fetch_tle_data_from_groups(groups=["starlink"])
```

### Want Weather Satellites?
```python
weather_tles = fetch_tle_data_from_groups(
    groups=["weather", "noaa", "goes"]
)
```

---

## 📚 Additional Celestrak Resources

### Browse All Groups
https://celestrak.org/NORAD/elements/

### Search Satellites
https://celestrak.org/satcat/search.php

### TLE Format Documentation
https://celestrak.org/NORAD/documentation/tle-fmt.php

### Satellite Database
https://celestrak.org/satcat/satcat-format.php

### Space-Track (Login Required)
https://www.space-track.org/

---

## ✅ Verification Checklist

After running the system:

- [ ] Check terminal output shows "Fetching from [group]..." for each
- [ ] Verify "Total unique satellites: XXXX" appears
- [ ] Confirm cache file created: `data/tle_cache.txt`
- [ ] Check database size: `ls -lh data/esids.db`
- [ ] Verify dashboard shows correct satellite count
- [ ] Test 3D globe renders smoothly
- [ ] Confirm API endpoint `/api/satellites` returns data

---

*Quick Reference Card — ESIDS v7.1*
*All 32 Celestrak Groups at a Glance*
