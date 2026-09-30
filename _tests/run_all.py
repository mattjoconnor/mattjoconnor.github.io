#!/usr/bin/env python3
"""Runs every ShowPoint test suite against an assembled site and fails if any check fails.

The site must be laid out like GitHub Pages:
  $SITE/            (mattjoconnor.github.io: ShowPoint home, worker, icons)
  $SITE/showcomm/   (showcomm repo; ETK is in etk/)
  $SITE/showgear/   (showgear repo)
"""
import functools, http.server, os, re, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.environ.get("SITE") or os.path.dirname(HERE)
ETK, SG = os.path.join(SITE, "showcomm", "etk"), os.path.join(SITE, "showgear")
os.environ["SITE"] = SITE

# Serve the site the way GitHub Pages does (folders redirect to add a trailing slash)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
try:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), functools.partial(Quiet, directory=SITE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
except OSError:   # something is already serving on 8765 (e.g. a workflow step): use it rather than crash
    srv = None
    print("Port 8765 already in use; using the server that's already running.", flush=True)

def summary(out):
    m = re.findall(r"(\d+) passed, (\d+) failed", out)
    return (int(m[-1][1]) == 0, f"{m[-1][0]} passed, {m[-1][1]} failed") if m else (False, "no summary line")
def no_fail(out, need=1):
    p, f = out.count("PASS"), out.count("FAIL")
    return (f == 0 and p >= need, f"{p} passed, {f} failed")
def contains(*needles):
    return lambda out: (all(n in out for n in needles), "ok" if all(n in out for n in needles) else "missing: " + ", ".join(n for n in needles if n not in out))

def prep_function():
    """Transpile the push function (minus its imports) so its routing can run in Node."""
    src = open(os.path.join(SITE, "_supabase", "functions", "etk-push", "index.ts")).read()
    d = os.path.join(HERE, "showpoint"); open(os.path.join(d, "fn.ts"), "w").write("\n".join(l for l in src.split("\n") if not l.startswith("import ")))
    subprocess.run([os.path.join(HERE, "node_modules", ".bin", "tsc"), "fn.ts", "--target", "es2022", "--module", "none",
                    "--skipLibCheck", "--noCheck", "--outDir", "out"], cwd=d, capture_output=True)

PY = [sys.executable]
SUITES = [
    # name, command, working dir, extra env, checker
    ("ShowComm · full crew→TM flow",        PY + [f"{HERE}/showcomm/etkflow.py"],        HERE, {},                  summary),
    ("ShowComm · confirm with clock skew",  PY + [f"{HERE}/showcomm/etkflow_skew.py"],   HERE, {"BREAK_GTE": "1"},  summary),
    ("ShowComm · chat",                     PY + [f"{HERE}/showcomm/chattest.py"],       HERE, {},                  summary),
    ("ShowComm · offline handling",         PY + [f"{HERE}/showcomm/offlinetest.py"],    HERE, {},                  summary),
    ("ShowComm · update prompt + cart colors", PY + [f"{HERE}/showcomm/updtest.py"],     HERE, {},                  summary),
    ("ShowComm · push delivery",            PY + [f"{HERE}/showcomm/pushtest.py"],       HERE, {},                  summary),
    ("ShowComm · install (home screen)",    PY + [f"{HERE}/showcomm/pwatest.py"],        HERE, {},                  summary),
    ("ShowComm · phone navigation",         PY + [f"{HERE}/showcomm/navtest.py"],        HERE, {},                  summary),
    ("ShowComm · readability (12px, 4.5:1)", PY + [f"{HERE}/showcomm/readability.py"],   HERE, {},                  summary),
    ("ShowComm · cart key moves",           ["node", f"{HERE}/showcomm/movetest.js"],    ETK,  {},                  lambda o: no_fail(o, 5)),
    ("ShowComm · cart page loads",          ["node", f"{HERE}/showcomm/repro.js", "index.html", "crew"], ETK, {}, contains("errors: none")),
    ("ShowComm · TM page loads",            ["node", f"{HERE}/showcomm/repro.js", "index.html", "tm"],   ETK, {}, contains("errors: none")),
    ("ShowGear · board",                    ["node", f"{HERE}/showgear/sgtest.js"],      SG,   {},                  summary),
    ("ShowGear · colors",                   ["node", f"{HERE}/showgear/cbtest.js"],      SG,   {},                  summary),
    ("ShowGear · matrix",                   ["node", f"{HERE}/showgear/mxtest_full.js"], SG,   {},                  summary),
    ("ShowGear · sharing",                  ["node", f"{HERE}/showgear/sharetest.js"],   SG,   {},                  summary),
    ("ShowGear · QR + PDFs",                ["node", f"{HERE}/showgear/qrtest_full.js"], SG,   {},                  summary),
    ("ShowGear · board order + archive",    PY + [f"{HERE}/showgear/boardtest.py"],      HERE, {},                  summary),
    ("ShowGear · ShowComm link",            PY + [f"{HERE}/showgear/linktest.py"],       HERE, {},                  summary),
    ("ShowGear · phone navigation",         PY + [f"{HERE}/showgear/navtest.py"],        HERE, {},                  summary),
    ("ShowGear · update prompt",            PY + [f"{HERE}/showgear/sgupd.py"],          HERE, {},                  summary),
    ("ShowPoint · home + switcher",         PY + [f"{HERE}/showcomm/sptest.py"],         HERE, {},                  summary),
    ("ShowPoint · folder redirects",        PY + [f"{HERE}/showpoint/redirects.py"],     HERE, {},                  lambda o: (o.count(" OK ") >= 5 and "FAIL" not in o, f"{o.count(' OK ')} of 5 addresses load")),
    ("ShowPoint · always-fresh pages",      PY + [f"{HERE}/showpoint/fresh.py"],         HERE, {},                  contains("redirects: 5/5", "fresh copy on reopen: True")),
    ("Push function · message text + keys", ["node", f"{HERE}/showpoint/fn_text.js"],   HERE, {},                  summary),
    ("Push function · routing",             ["node", f"{HERE}/showpoint/fn_routing.js"], os.path.join(HERE, "showpoint"), {}, summary),
]

prep_function()
failed, t0 = [], time.time()
for name, cmd, cwd, env, check in SUITES:
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, env={**os.environ, **env}, capture_output=True, text=True, timeout=420)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        out = "TIMED OUT"
    ok, detail = check(out)
    print(f"{'PASS' if ok else 'FAIL'}  {name:42} {detail}  ({time.time()-t:.0f}s)", flush=True)
    if not ok:
        failed.append(name)
        print("\n".join("      " + l for l in out.strip().splitlines()[-25:]), flush=True)
        if os.environ.get("GITHUB_ACTIONS"):   # show the failure as an annotation on the run's page
            fails = [l.strip() for l in out.splitlines() if "FAIL" in l][:6] or out.strip().splitlines()[-6:]
            print(f"::error title={name}::{detail} | " + " || ".join(fails).replace("%", "%25").replace("\r", "").replace("\n", " "), flush=True)
if srv: srv.shutdown()
print(f"\n{len(SUITES)-len(failed)} of {len(SUITES)} suites passed in {time.time()-t0:.0f}s")
sys.exit(1 if failed else 0)
