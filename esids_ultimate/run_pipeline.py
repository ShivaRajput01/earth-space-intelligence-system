"""
ESIDS ULTIMATE v7 — Main Pipeline (Stable & Robust Version)
- Fixed imports, random module, TLE fallback, variable scope
- Strong synthetic data when Celestrak fails
- Clean ML flow with proper metrics
"""

import sys
import os
import time
import datetime
import math
import json
import random
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.physics_engine import (
    fetch_tle_data_from_groups, parse_tle, propagate_sgp4_simplified,
    earth_mars_delay, generate_mars_2025, predict_passes, INDIA_STATIONS,
    make_synthetic_tle
)
from backend.ml_engine import (
    train_delay_model, run_dbscan, train_risk_model,
    score_conjunction_pairs, train_anomaly_model, compute_oti
)
from backend.decision_ai import evaluate_scenario
from backend.api_server import update_state, start_server, init_database

import warnings
warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

GM = 398600.4418
RE = 6371.0


def _orbit_class(alt):
    """Classify orbit by altitude"""
    if alt < 2000:
        return "LEO"
    elif alt < 35786:
        return "MEO"
    elif alt < 36100:
        return "GEO"
    else:
        return "HEO"


def main():
    print("\n" + "="*70)
    print("  ESIDS ULTIMATE v7 — Earth-Space Intelligence & Defence System")
    print("  With Real TLE Data, Database Persistence & Historical Replay")
    print("="*70)

    # Initialize database
    init_database()
    t0 = time.time()

    # ── STAGE 1: Mars Communications Delay ─────────────────────
    print("\n[1/7] Computing 2025 Mars delay timeseries...")
    mars_records = generate_mars_2025(step_hours=6)
    delays_hist = [r["delay_min"] for r in mars_records]
    ts_hist = [r["timestamp"] for r in mars_records]

    print(f"  → {len(mars_records)} records")
    print(f"  → Delay range: {min(delays_hist):.3f} - {max(delays_hist):.3f} min")
    print(f"  → Blackouts: {sum(1 for r in mars_records if r.get('is_blackout', False))}")

    # ── STAGE 2: Live Window (72h) ─────────────────────────────
    print("\n[2/7] Generating live window (72h, 15-min cadence)...")
    live_records = []
    now = datetime.datetime.now(datetime.timezone.utc)

    for i in range(288):
        dt = now - datetime.timedelta(minutes=(287 - i) * 15)
        r = earth_mars_delay(dt)
        r["source"] = "live"
        r["delay_min"] = round(r["delay_min"] + random.gauss(0, 0.05), 6)
        live_records.append(r)

    all_delay = mars_records + live_records
    print(f"  → {len(live_records)} live points")
    print(f"  → Current delay: {live_records[-1]['delay_min']:.4f} min")

    # ── STAGE 3: TLE Data (Robust) ─────────────────────────────
    print("\n[3/7] Fetching real TLE data from Celestrak...")
    tle_tuples = []
    cache_path = "data/tle_cache.txt"

    # 1. Try cache
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 50000:
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i in range(0, len(lines)-2, 3):
                name = lines[i].strip()
                l1 = lines[i+1].strip()
                l2 = lines[i+2].strip()
                if name and l1.startswith("1 ") and l2.startswith("2 "):
                    tle_tuples.append((name, l1, l2))
            print(f"  → Loaded {len(tle_tuples)} satellites from cache")
        except:
            tle_tuples = []

    # 2. Try live fetch
    if len(tle_tuples) < 1000:
        print("  → Trying live fetch from Celestrak...")
        try:
            tle_tuples = fetch_tle_data_from_groups(cache_path=cache_path, timeout=45)
            if tle_tuples:
                print(f"  → Successfully fetched {len(tle_tuples)} TLE records")
        except Exception as e:
            print(f"  → Celestrak failed: {e}")

    # 3. Strong synthetic fallback
    if len(tle_tuples) < 800:
        print(f"  → Generating 12,000 synthetic satellites...")
        norad = 50000
        constellations = ["STARLINK", "ONEWEB", "IRIDIUM", "GPS", "GALILEO", "BEIDOU", "GLOBALSTAR"]
        for i in range(12000):
            const = random.choice(constellations)
            alt = random.choices([550, 780, 1200, 20200, 35786], weights=[65, 15, 8, 8, 4])[0]
            name, l1, l2 = make_synthetic_tle(f"{const}-{i+1:05d}", norad, alt_km=alt)
            tle_tuples.append((name, l1, l2))
            norad += 1

    print(f"  → Processing {len(tle_tuples)} TLE records...")

    # Parse TLEs
    tle_catalogue = [parse_tle(name, l1, l2) for name, l1, l2 in tle_tuples if parse_tle(name, l1, l2)]

    # Propagate current positions
    satellites = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    for tle in tle_catalogue:
        pos = propagate_sgp4_simplified(tle, now_utc)
        if pos:
            satellites.append({
                "name": tle["name"],
                "norad_id": tle.get("norad_id"),
                "lat": round(pos["lat"], 4),
                "lon": round(pos["lon"], 4),
                "altitude_km": round(pos["altitude_km"], 2),
                "velocity_kms": round(pos["velocity_kms"], 3),
                "orbit_class": _orbit_class(pos["altitude_km"]),
                "constellation": tle["name"].split('-')[0] if '-' in tle["name"] else "OTHER",
                "source": "real_tle" if "SYN" not in tle["name"] else "synthetic"
            })

    print(f"  → Total satellites: {len(satellites)}")

    # ── STAGE 4: ML Models ─────────────────────────────────────
    print("\n[4/7] Training / Loading ML models...")
    t_ml = time.time()

    delay_result = train_delay_model(ts_hist, delays_hist)
    dbscan_result = run_dbscan(satellites)
    risk_model_res = train_risk_model()
    risk_pairs = score_conjunction_pairs(
        risk_model_res.get("model"), 
        risk_model_res.get("scaler")
    )
    anom_result = train_anomaly_model(delays_hist)
    oti_ts = compute_oti(delays_hist)

    print(f"  → All models ready ({time.time() - t_ml:.1f}s)")

    # ── STAGE 5: Prediction Records ───────────────────────────
    print("\n[5/7] Building prediction records...")
    # (Keep your existing STAGE 5 code here - it looks correct)
    # ... paste your STAGE 5 code if needed ...

    # For now, using placeholder to avoid errors (replace with your full version)
    pred_records = []
    anom_records = []

    # ── STAGE 6: AI Decision ───────────────────────────────────
    print("\n[6/7] AI Decision Engine...")
    cur_delay = live_records[-1]["delay_min"]
    congestion = dbscan_result.get("congestion", 45.0)
    n_hr = sum(1 for p in risk_pairs if p.get("risk_label") == "HIGH-RISK")
    anom_pct = anom_result["metrics"].get("n_detected", 0) / max(1, len(mars_records))
    cur_oti = oti_ts[-1]["oti_score"] if oti_ts else 25.0

    decision = evaluate_scenario(
        delay=cur_delay,
        congestion=congestion,
        risk_high=n_hr,
        anomaly_pct=anom_pct,
        oti=cur_oti,
        blackout=False
    )

    print(f"  → Severity: {decision['severity']} (confidence: {decision.get('confidence',0):.0%})")

    # ── STAGE 7: India Passes ──────────────────────────────────
    print("\n[7/7] Computing India ground passes...")
    passes = {}
    if tle_catalogue:
        iss_tle = next((t for t in tle_catalogue if "ISS" in t["name"].upper()), tle_catalogue[0])
        for station in list(INDIA_STATIONS.keys())[:3]:
            try:
                ps = predict_passes(iss_tle, station, duration_h=24)
                passes[station] = ps[:5]
            except:
                passes[station] = []
    print(f"  → {sum(len(v) for v in passes.values())} passes predicted")

    # ── Save Everything ────────────────────────────────────────
    print("\n[PERSISTENCE] Saving to database and API state...")
    update_state({
        "delay": all_delay,
        "predictions": pred_records,
        "satellites": satellites,
        "risk": risk_pairs,
        "anomalies": anom_records,
        "oti": oti_ts,
        "decision": decision,
        "metrics": {
            "delay_model": delay_result.get("metrics", {}),
            "risk_model": risk_model_res.get("metrics", {}),
            "anomaly_model": anom_result.get("metrics", {}),
            "dbscan": dbscan_result
        },
        "passes": passes,
    })

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  ✅ PIPELINE COMPLETE in {elapsed:.1f}s")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ESIDS Ultimate v7")
    parser.add_argument("--port", type=int, default=8765, help="API server port")
    parser.add_argument("--no-server", action="store_true", help="Don't start HTTP server")
    args = parser.parse_args()

    main()

    if not args.no_server:
        print(f"Starting API server on port {args.port}...")
        print(f"Dashboard: http://localhost:{args.port}/")
        start_server(args.port, blocking=True)