"""Runs every ShowPoint test suite against the assembled site and fails if any check fails.
Layout: $SITE = the root site, $SITE/showcomm, $SITE/showgear; a web server on :8765 serves $SITE."""
import os, re, subprocess, sys, time
SITE=os.environ.get('SITE','/tmp/site'); T=os.path.dirname(os.path.abspath(__file__))
env=dict(os.environ, SITE=SITE, NODE_PATH=os.path.join(T,'node_modules'))
SUITES=[  # (label, command, working folder, extra env)
 ('ShowGear · QR and exports',  ['node',f'{T}/sg_qrtest_full.js'], f'{SITE}/showgear', {}),
 ('ShowGear · colors/board',    ['node',f'{T}/sg_cbtest.js'],       f'{SITE}/showgear', {}),
 ('ShowGear · matrix',          ['node',f'{T}/sg_mxtest_full.js'],  f'{SITE}/showgear', {}),
 ('ShowGear · sharing',         ['node',f'{T}/sg_sharetest.js'],    f'{SITE}/showgear', {}),
 ('ShowGear · core',            ['node',f'{T}/sg_sgtest.js'],       f'{SITE}/showgear', {}),
 ('ShowGear · board (browser)', ['python3',f'{T}/sg_boardtest.py'], T, {}),
 ('ShowGear · ShowComm link',   ['python3',f'{T}/sg_linktest.py'],  T, {}),
 ('ShowGear · update prompt',   ['python3',f'{T}/sp_sgupd.py'],     T, {}),
 ('ShowComm · cart keys/move',  ['node',f'{T}/sc_movetest.js'],     f'{SITE}/showcomm/etk', {}),
 ('ShowComm · cart loads',      ['node',f'{T}/sc_repro.js','index.html','crew'], f'{SITE}/showcomm/etk', {}),
 ('ShowComm · TM loads',        ['node',f'{T}/sc_repro.js','index.html','tm'],   f'{SITE}/showcomm/etk', {}),
 ('ShowComm · full flow',       ['python3',f'{T}/sc_etkflow.py'],   T, {}),
 ('ShowComm · clock skew',      ['python3',f'{T}/sc_etkflow_skew.py'], T, {'BREAK_GTE':'1'}),
 ('ShowComm · chat',            ['python3',f'{T}/sc_chattest.py'],  T, {}),
 ('ShowComm · offline',         ['python3',f'{T}/sc_offlinetest.py'], T, {}),
 ('ShowComm · colors + update', ['python3',f'{T}/sc_updtest.py'],   T, {}),
 ('ShowComm · push delivery',   ['python3',f'{T}/sc_pushtest.py'],  T, {}),
 ('ShowPoint · home + install', ['python3',f'{T}/sc_sptest.py'],    T, {}),
 ('ShowPoint · installed app',  ['python3',f'{T}/sc_pwatest.py'],   T, {}),
 ('ShowPoint · redirects',      ['python3',f'{T}/sp_redir.py'],     T, {}),
 ('ShowPoint · fresh pages',    ['python3',f'{T}/sp_fresh.py'],     T, {}),
 ('Push function',              ['node',f'{T}/fn_test.js'],         T, {}),
]
only=sys.argv[1:]
results=[]; t0=time.time()
for label,cmd,cwd,extra in SUITES:
    if only and not any(o.lower() in label.lower() for o in only): continue
    t=time.time()
    try: p=subprocess.run(cmd,cwd=cwd,env={**env,**extra},capture_output=True,text=True,timeout=420); out=p.stdout+p.stderr; code=p.returncode
    except subprocess.TimeoutExpired as e: out=(e.stdout or '')+'\nTIMED OUT'; code=124
    fails=[l.strip() for l in out.split('\n') if re.search(r'\bFAIL\b',l)]
    m=re.search(r'(\d+) passed, (\d+) failed',out)
    ok = code==0 and not fails and (m is None or m.group(2)=='0') and 'Traceback' not in out and 'TIMED OUT' not in out
    if 'repro' in cmd[1]: ok = ok and 'errors: none' in out
    if 'fresh' in cmd[1]: ok = ok and '5/5' in out and 'True' in out
    if 'redir' in cmd[1]: ok = ok and out.count(' OK ')>=5
    summary = f"{m.group(1)} passed" if m and ok else ('ok' if ok else (fails[0] if fails else out.strip().split('\n')[-1][:140]))
    results.append((ok,label,summary,time.time()-t))
    print(f"{'✅' if ok else '❌'} {label:30} {summary}  ({time.time()-t:.0f}s)", flush=True)
    if not ok: print('   ' + '\n   '.join(out.strip().split('\n')[-25:]), flush=True)
bad=[r for r in results if not r[0]]
print(f"\n{len(results)-len(bad)}/{len(results)} suites passed in {time.time()-t0:.0f}s")
sys.exit(1 if bad else 0)
