import os
SITE=os.environ.get('SITE','/tmp/site')
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'etkflow.py')).read().split("res=[]")[0])
res=[]
def ok(c,m): res.append(bool(c)); print(('  PASS ' if c else '  FAIL ')+m)
N=lambda m: iso(now-datetime.timedelta(minutes=m))
STORE['device_claims'].append({'id':'c3','production_id':'ETK','device_type':'beltpack','device_id':'BP03','crew_name':'Zach','crew_position':'','status':'confirmed','claimed_at':N(30)})
STORE['key_requests'].append({'id':'k1','production_id':'ETK','device_id':'BP03','status':'open','requester_role':'crew','created_at':N(10),'note':json.dumps([{'keyIndex':0,'label':'Key 1','note':'CAMS (PL)'}])})
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(viewport={'width':1280,'height':700}); ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
    tm=ctx.new_page(); tm.goto('file://'+SITE+'/showcomm/etk/index.html?role=tm'); tm.wait_for_timeout(700)
    tm.fill('#login-username','tm'); tm.fill('#login-pw','showcomm'); tm.click('#btn-login'); tm.wait_for_timeout(1500)
    # watch for any change to the page body during background refreshes
    tm.evaluate("""window.__mut=0; window.__loading=0; new MutationObserver(m=>{ window.__mut+=m.length; if(document.querySelector('#tm-body .empty-text') && /Loading/.test(document.querySelector('#tm-body .empty-text').textContent)) window.__loading++; }).observe(document.getElementById('tm-body'),{childList:true,subtree:true}); 0""")
    print('Beltpacks')
    for _ in range(3): tm.evaluate("renderETKBeltpackStatus({bg:true})"); tm.wait_for_timeout(500)
    ok(tm.evaluate("window.__mut")==0,'3 background refreshes with no changes: page untouched (no flash)')
    tm.evaluate("const b=document.getElementById('tm-body'); b.scrollTop=Math.min(400, b.scrollHeight-b.clientHeight); 0")   # however far this layout can scroll
    scrolled=tm.evaluate("document.getElementById('tm-body').scrollTop"); tm.evaluate("window.__mut=0; 0")
    STORE['key_requests'].append({'id':'k2','production_id':'ETK','device_id':'BP03','status':'open','requester_role':'crew','created_at':N(1),'note':json.dumps([{'keyIndex':1,'label':'Key 2','note':'AUD (PL)'}])})
    tm.evaluate("renderETKBeltpackStatus({bg:true})"); tm.wait_for_timeout(700)
    ok(tm.evaluate("window.__mut")>0 and 'AUD' in tm.inner_text('#etk-queue-item-BP03'),'a real change still appears on its own')
    ok(tm.evaluate("window.__loading")==0,'no "Loading…" in between')
    ok(abs(tm.evaluate("document.getElementById('tm-body').scrollTop")-scrolled)<5,'scroll position kept (%dpx)'%scrolled)
    print('Channels and Deploy')
    for v in ('channels','deploy'):
        tm.evaluate(f"setTMView('{v}')"); tm.wait_for_timeout(900); tm.evaluate("window.__mut=0; 0")
        fn={'channels':'renderETKChannels','deploy':'renderETKDeploy'}[v]
        for _ in range(3): tm.evaluate(f"{fn}({{bg:true}})"); tm.wait_for_timeout(400)
        ok(tm.evaluate("window.__mut")==0,f'{v}: background refreshes with no changes leave the page alone')
    tm.evaluate("setTMView('beltpacks')"); tm.wait_for_timeout(900)
    ok(tm.query_selector('#etk-queue-item-BP03') is not None,'switching tabs still draws immediately')
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
