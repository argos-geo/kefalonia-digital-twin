import os, subprocess, smtplib, ssl, datetime
from email.message import EmailMessage

env = {}
for line in open(os.path.expanduser("~/.argos_ops_env")):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1); env[k] = v

def sh(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e: return "ERR: %s" % e

now_dt = datetime.datetime.now(datetime.UTC)
now = now_dt.strftime("%Y-%m-%d %H:%M UTC")
marine_tail = sh("tail -6 ~/marine_refresh.log")
db = sh("docker exec -i argos-postgis psql -U argos -d argos -t -c \"SELECT (SELECT count(*) FROM argos.marine_forecast), (SELECT max(fetched_at) FROM argos.marine_forecast), (SELECT count(*) FROM argos.marine_grid), (SELECT max(cmems_run) FROM argos.marine_forecast);\"")
api = sh("for u in http://localhost:8000/health http://localhost/health https://argos-geo.org/api/health https://api.argos-geo.org/health; do code=$(curl -s -o /tmp/h.txt -w %{http_code} -m 8 $u); echo \"$u -> $code $(head -c 120 /tmp/h.txt)\"; done")
dockers = sh("docker ps --format \"{{.Names}}: {{.Status}}\"")
disk_raw = sh("df -h / | tail -1")
load = sh("uptime")

OK, WARNMARK = "OK", "!!"

# ---- disk bar + WARN + delta vs yesterday (Batch 4 g v2, 18 Oct 2026) ----
pct = -1
parts = disk_raw.split()
if len(parts) >= 5 and parts[4].rstrip("%").isdigit():
    pct = int(parts[4].rstrip("%"))
state_f = os.path.expanduser("~/.argos_disk_state")
delta = ""
try:
    prev = int(open(state_f).read().strip())
    if pct >= 0:
        d = pct - prev
        delta = " (%+d vs yesterday)" % d if d != 0 else " (flat)"
except Exception:
    pass
if pct >= 0:
    try:
        open(state_f, "w").write(str(pct))
    except Exception:
        pass
disk_line = disk_raw
warn = ""
disk_mark = OK
if pct >= 0:
    filled = round(pct / 5)
    bar = "[" + "#" * filled + "-" * (20 - filled) + "]"
    disk_line = "/  %s %d%% used%s (%s free of %s)" % (bar, pct, delta, parts[3], parts[1])
    if pct >= 75:
        disk_mark = WARNMARK
        warn = "\n** WARN: / at %d%%, threshold 75. Cleanup ladder: du driver check, docker system prune -af, journalctl --vacuum-size=200M. **" % pct

# ---- load flag (2-core VM) ----
load_flag = ""
load1 = "?"
load_mark = OK
try:
    l1 = float(load.split("load average:")[1].split(",")[0].strip())
    load1 = "%.2f" % l1
    if l1 > 2.0:
        load_mark = WARNMARK
        load_flag = "  ** BUSY: load1 %.2f > 2.0 **" % l1
except Exception:
    pass

# ---- marine fetch age in hours ----
marine_age = "?"
marine_mark = OK
try:
    ts = db.split("|")[1].strip()
    ft = datetime.datetime.fromisoformat(ts)
    age_h = (now_dt - ft).total_seconds() / 3600.0
    marine_age = "%.1fh ago" % age_h
    if age_h > 14: marine_mark = WARNMARK
except Exception:
    pass

# ---- containers + api ----
n_up = dockers.count("Up")
cont_mark = OK if n_up >= 4 else WARNMARK
api_ok = any(("-> 200" in l and "ok" in l) for l in api.splitlines())
api_mark = OK if api_ok else WARNMARK

glance = "%s disk %s%s | %s load %s | %s containers %d up | %s api | %s marine fetched %s" % (
    disk_mark, ("%d%%" % pct) if pct >= 0 else "?", delta,
    load_mark, load1,
    cont_mark, n_up,
    api_mark,
    marine_mark, marine_age)

body = """ARGOS VM daily report - %s

== QUICK GLANCE ==
%s%s

== MARINE REFRESH, log tail (want: TRUNCATE+COPY pairs, no ERROR lines; COPY 1778 = beach rows, COPY 79883 = current-grid cells) ==
%s

== MARINE DATA, freshness (forecast rows | last fetch time | grid rows | model run cycle; fetch should be <14h old, model run is always 24-48h old by product design) ==
%s

== API HEALTH (each candidate URL -> HTTP status + body; want one 200 with ok/healthy body) ==
%s

== DOCKER CONTAINERS (want: all four Up, postgis healthy) ==
%s

== DISK (WARN at 75 percent; act at 80) ==
%s%s

== LOAD (time, uptime, load average 1/5/15 min; 2-core VM so sustained >2.0 = busy) ==
%s%s
""" % (now, glance, warn and "  <-- see DISK WARN below" or "", marine_tail, db, api, dockers, disk_line, warn, load, load_flag)

msg = EmailMessage()
msg["From"] = env["REPORT_FROM"]; msg["To"] = env["REPORT_TO"]
msg["Subject"] = ("ARGOS VM report %s" % now) + (" [DISK WARN]" if warn else "")
msg.set_content(body)
ctx = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.resend.com", 465, context=ctx) as s:
    s.login("resend", env["RESEND_API_KEY"])
    s.send_message(msg)
print("sent to", env["REPORT_TO"])
