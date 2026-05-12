"""
ESIDS API Server v7.2 - All bugs fixed, numpy-safe, UTF-8 safe
"""
import json, sqlite3, datetime, threading, time, os, math
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Numpy-safe JSON encoder ────────────────────────────────────────────────────
class _Enc(json.JSONEncoder):
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, np.integer): return int(obj)
            if isinstance(obj, np.floating): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            if isinstance(obj, np.bool_): return bool(obj)
        except ImportError: pass
        if isinstance(obj, (datetime.datetime, datetime.date)): return obj.isoformat()
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)): return None
        return super().default(obj)

def _j(o): return json.dumps(o, cls=_Enc)

def _clean(o):
    try:
        import numpy as np
        if isinstance(o, np.integer): return int(o)
        if isinstance(o, np.floating): return float(o)
        if isinstance(o, np.bool_): return bool(o)
        if isinstance(o, np.ndarray): return o.tolist()
    except ImportError: pass
    if isinstance(o, dict): return {k: _clean(v) for k,v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(i) for i in o]
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)): return None
    return o

_state = {}
_db_path = "data/esids.db"
_iss_running = False

def init_database():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(_db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS delay_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
        distance_km REAL, delay_min REAL, is_blackout INTEGER, source TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS satellite_snapshots(
        id INTEGER PRIMARY KEY AUTOINCREMENT, norad_id INTEGER, name TEXT,
        lat REAL, lon REAL, altitude_km REAL, velocity_kms REAL,
        orbit_class TEXT, constellation TEXT, snapshot_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS risk_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, sat1 TEXT, sat2 TEXT,
        miss_distance_km REAL, risk_label TEXT, prob_high_risk REAL, recorded_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS decision_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, severity TEXT,
        confidence REAL, rationale TEXT, oti_score REAL, recorded_at TEXT)''')
    conn.commit(); conn.close()
    print("[DB] Ready:", _db_path)

def _save(dtype, recs):
    try:
        conn = sqlite3.connect(_db_path); c = conn.cursor()
        if dtype == "delay":
            c.executemany('INSERT INTO delay_history(timestamp,distance_km,delay_min,is_blackout,source) VALUES(?,?,?,?,?)',
                [(r.get("timestamp"), float(r.get("distance_km") or 0), float(r.get("delay_min") or 0),
                  int(r.get("is_blackout") or 0), r.get("source","")) for r in recs])
        elif dtype == "satellites":
            snap = datetime.datetime.now(datetime.timezone.utc).isoformat()
            c.executemany('INSERT INTO satellite_snapshots(norad_id,name,lat,lon,altitude_km,velocity_kms,orbit_class,constellation,snapshot_time) VALUES(?,?,?,?,?,?,?,?,?)',
                [(int(r.get("norad_id") or 0), r.get("name",""), float(r.get("lat") or 0), float(r.get("lon") or 0),
                  float(r.get("altitude_km") or 0), float(r.get("velocity_kms") or 0),
                  r.get("orbit_class",""), r.get("constellation",""), snap) for r in recs])
        elif dtype == "risk":
            c.executemany('INSERT INTO risk_events(sat1,sat2,miss_distance_km,risk_label,prob_high_risk,recorded_at) VALUES(?,?,?,?,?,?)',
                [(r.get("sat1",""), r.get("sat2",""), float(r.get("miss_distance_km") or 0),
                  r.get("risk_label",""), float(r.get("prob_high_risk") or 0),
                  datetime.datetime.now(datetime.timezone.utc).isoformat()) for r in recs])
        elif dtype == "decision":
            c.execute('INSERT INTO decision_history(severity,confidence,rationale,oti_score,recorded_at) VALUES(?,?,?,?,?)',
                (recs.get("severity",""), float(recs.get("confidence") or 0),
                 recs.get("rationale",""), float(recs.get("oti_score") or 0),
                 datetime.datetime.now(datetime.timezone.utc).isoformat()))
        conn.commit(); conn.close()
    except Exception as e: print(f"[DB] {dtype} error: {e}")

def update_state(data):
    global _state
    _state.update(_clean(data))
    if "delay" in data: _save("delay", data["delay"])
    if "satellites" in data: _save("satellites", data["satellites"])
    if "risk" in data: _save("risk", data["risk"])
    if "decision" in data: _save("decision", data["decision"])
    print(f"[API] State: {len(_state)} keys, {len(_state.get('satellites',[]))} sats")

def get_state(key=None):
    return _state.get(key) if key else _state

def _ocounts(sats=None):
    if sats is None: sats = _state.get("satellites", [])
    r = {"LEO":0,"MEO":0,"GEO":0,"HEO":0}
    for s in sats:
        k = s.get("orbit_class","LEO")
        r[k] = r.get(k, 0) + 1
    return r

def _iss_loop():
    global _iss_running
    print("[ISS] Tracker started")
    while _iss_running:
        t = time.time(); period = 90*60
        phase = (t % period)/period * 2*math.pi
        _state["iss_live"] = {
            "name":"ISS", "lat":round(51.6*math.sin(phase),4),
            "lon":round(((t/period*360)%360)-180,4),
            "altitude_km":round(408+math.sin(phase*3)*5,2),
            "velocity_kms":7.66,
            "timestamp":datetime.datetime.now(datetime.timezone.utc).isoformat()}
        time.sleep(5)

def start_iss_tracker():
    global _iss_running
    if not _iss_running:
        _iss_running = True
        threading.Thread(target=_iss_loop, daemon=True).start()

def stop_iss_tracker():
    global _iss_running; _iss_running = False


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def cors(self):
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")

    def js(self, data, code=200):
        b = _j(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(b)))
        self.cors()
        self.end_headers()
        self.wfile.write(b)

    def html(self, content):
        b = content if isinstance(content,bytes) else content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(b)))
        self.cors()
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(200); self.cors(); self.end_headers()

    def _find_dashboard(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base, "static", "dashboard.html"),
            os.path.join("static", "dashboard.html"),
            os.path.join("..", "static", "dashboard.html"),
        ]
        for p in candidates:
            if os.path.exists(p): return p
        return None

    def do_GET(self):
        purl = urlparse(self.path); path = purl.path; q = parse_qs(purl.query)
        try:
            if path in ("/", "/index.html"):
                f = self._find_dashboard()
                if f:
                    # Read as binary to avoid any encoding issues, send as UTF-8
                    with open(f, "rb") as fh: raw = fh.read()
                    self.html(raw); return
                self.js({"error":"dashboard.html not found"},404); return

            elif path == "/api/status":
                self.js({"status":"online","satellites":len(_state.get("satellites",[])),
                    "timestamp":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "database":os.path.exists(_db_path),"keys":list(_state.keys())})

            elif path == "/api/delay":
                d = _state.get("delay",[]); lim = int(q.get("limit",[len(d)])[0])
                self.js({"data":d[-lim:],"count":len(d)})

            elif path == "/api/predictions":
                d = _state.get("predictions",[])
                self.js({"data":d,"count":len(d)})

            elif path == "/api/satellites":
                sats = list(_state.get("satellites",[]))
                orbit = q.get("orbit",["ALL"])[0].upper()
                const = q.get("constellation",["ALL"])[0].upper()
                search = q.get("search",[""])[0].upper()
                lim = int(q.get("limit",[20000])[0])
                off = int(q.get("offset",[0])[0])
                if orbit != "ALL": sats = [s for s in sats if s.get("orbit_class","").upper()==orbit]
                if const != "ALL": sats = [s for s in sats if const in s.get("constellation","").upper()]
                if search: sats = [s for s in sats if search in s.get("name","").upper()]
                consts = {}
                for s in _state.get("satellites",[]):
                    c = s.get("constellation","?"); consts[c] = consts.get(c,0)+1
                top50 = dict(sorted(consts.items(),key=lambda x:-x[1])[:50])
                self.js({"data":sats[off:off+lim],"count":len(sats),
                    "total":len(_state.get("satellites",[])),
                    "orbit_counts":_ocounts(),"constellation_counts":top50})

            elif path == "/api/satellites/constellations":
                consts = {}
                for s in _state.get("satellites",[]):
                    c = s.get("constellation","?"); consts[c] = consts.get(c,0)+1
                self.js({"constellations":dict(sorted(consts.items(),key=lambda x:-x[1])[:50]),
                    "total":len(consts)})

            elif path == "/api/iss":
                self.js(_state.get("iss_live",{"name":"ISS","lat":0.0,"lon":0.0,
                    "altitude_km":408.0,"velocity_kms":7.66,"timestamp":
                    datetime.datetime.now(datetime.timezone.utc).isoformat()}))

            elif path == "/api/risk":
                risk = list(_state.get("risk",[]))
                lbl = q.get("label",["ALL"])[0].upper()
                if lbl != "ALL": risk = [r for r in risk if r.get("risk_label","").upper()==lbl]
                lim = int(q.get("limit",[500])[0])
                counts = {"SAFE":0,"CAUTION":0,"HIGH-RISK":0}
                for r in _state.get("risk",[]):
                    lk = r.get("risk_label","SAFE"); counts[lk] = counts.get(lk,0)+1
                self.js({"data":risk[:lim],"count":len(risk),"counts":counts})

            elif path == "/api/anomalies":
                d = _state.get("anomalies",[]); self.js({"data":d,"count":len(d)})

            elif path == "/api/oti":
                d = _state.get("oti",[]); self.js({"data":d,"count":len(d)})

            elif path == "/api/decision":
                self.js(_state.get("decision",{}))

            elif path == "/api/metrics":
                self.js(_state.get("metrics",{}))

            elif path == "/api/feature-importance":
                self.js(_state.get("importance",{}))

            elif path == "/api/passes":
                passes = _state.get("passes",{})
                st = q.get("station",[None])[0]
                self.js({"station":st,"passes":passes.get(st,[])} if st else passes)

            elif path == "/api/india":
                sats = _state.get("satellites",[]); iss = _state.get("iss_live",{})
                india = [s for s in sats if 8<=s.get("lat",0)<=35 and 68<=s.get("lon",0)<=97]
                self.js({"satellites":india,"count":len(india),
                    "iss_visible":8<=iss.get("lat",0)<=35 and 68<=iss.get("lon",0)<=97,
                    "iss":iss,"passes":_state.get("passes",{})})

            elif path == "/api/live-feed":
                d = _state.get("delay",[]); iss = _state.get("iss_live",{})
                dec = _state.get("decision",{}); risk = _state.get("risk",[])
                hr = [r for r in risk if r.get("risk_label")=="HIGH-RISK"]
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                events = [
                    {"t":now,"type":"INFO","msg":f"System {dec.get('severity','NOMINAL')} - {len(_state.get('satellites',[]))} satellites tracked"},
                    {"t":now,"type":"WARN" if hr else "OK","msg":f"{len(hr)} HIGH-RISK conjunctions active"},
                    {"t":now,"type":"INFO","msg":f"Mars delay: {d[-1].get('delay_min','--') if d else '--'} min"},
                    {"t":now,"type":"OK","msg":f"ISS at {iss.get('lat',0):.1f}N, {iss.get('lon',0):.1f}E, alt {iss.get('altitude_km',0):.0f}km"},
                    {"t":now,"type":"INFO","msg":f"Database: {os.path.getsize(_db_path)//1024}KB" if os.path.exists(_db_path) else "DB offline"},
                ]
                self.js({"events":events,"iss":iss})

            elif path == "/api/alerts":
                dec = _state.get("decision",{}); alerts = []
                if dec.get("severity") in ["WARNING","CRITICAL"]:
                    alerts.append({"severity":dec["severity"],"message":dec.get("rationale",""),
                        "timestamp":datetime.datetime.now(datetime.timezone.utc).isoformat()})
                self.js({"alerts":alerts,"count":len(alerts)})

            elif path == "/api/whatif":
                from backend.decision_ai import evaluate_scenario
                res = evaluate_scenario(
                    delay=float(q.get("delay",[10])[0]),
                    congestion=float(q.get("congestion",[50])[0]),
                    risk_high=int(q.get("risk_count",[20])[0]),
                    anomaly_pct=float(q.get("anom_pct",[0.03])[0]),
                    oti=float(q.get("oti",[50])[0]),
                    blackout=q.get("blackout",["false"])[0].lower()=="true")
                self.js(res)

            else:
                self.js({"error":f"Not found: {path}"},404)

        except Exception as e:
            import traceback; traceback.print_exc()
            try: self.js({"error":str(e)},500)
            except: pass

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            n = int(self.headers.get("Content-Length",0))
            body = json.loads(self.rfile.read(n)) if n else {}
            if p == "/api/avoidance/plan":
                from backend.decision_ai import plan_hohmann_transfer
                self.js(plan_hohmann_transfer(body.get("current_alt_km",550),
                    body.get("target_alt_km",600), body.get("mass_kg",1000)))
            else:
                self.js({"error":"Not found"},404)
        except Exception as e:
            self.js({"error":str(e)},500)


def start_server(port=8765, blocking=True):
    init_database(); start_iss_tracker()
    srv = HTTPServer(("",port), H)
    print(f"[API] http://localhost:{port}")
    if blocking:
        try: srv.serve_forever()
        except KeyboardInterrupt: stop_iss_tracker()
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv
