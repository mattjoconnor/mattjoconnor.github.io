import os
SITE=os.environ.get('SITE','/tmp/site')
import json, datetime
from playwright.sync_api import sync_playwright
now=datetime.datetime.now(datetime.timezone.utc)
iso=lambda d: d.strftime('%Y-%m-%dT%H:%M:%S.000Z')
SEED={'productions':[{'id':'ETK','name':'ETK','control_room':'','dates':'','start_date':'2026-10-01','end_date':'2026-10-16','status':'active','beltpacks':[f'BP{i:02d}' for i in range(1,25)],'keypanels':[],'sort_order':0}],
 'profiles':[{'id':'u-tm','role':'tm','display_name':'TM'}],'device_claims':[],'key_requests':[],
 'bp_custody':[{'id':'c1','device_id':'BP09','production_id':'ETK','action':'deployed','crew_name':None,'created_at':iso(now-datetime.timedelta(days=2))}],
 'etk_options':[{'key':'main','data':{'PLs':[{'label':l,'fg':[0,0,0],'bg':[240,14,206]} for l in ['CAMS','TECH','CUL','LITE','AUD','AD','PROD']],
                                      'IFBs':[{'label':l,'fg':[169,212,152],'bg':[0,0,0]} for l in ['HOST','JUDGE','CHEF 1','PGM MIX']]}}],
 'beltpack_assignments':[],'kp_assignments':[],'go_options':[],'global_options':[]}
MOCK=r"""
(function(){
  window.__notes=[]; window.Notification=function(t,o){ window.__notes.push({t,body:o&&o.body}); this.close=()=>{}; }; window.Notification.permission='granted'; window.Notification.requestPermission=async()=>'granted';
  function from(table){
    const st={table, op:'select', f:[], single:0, ord:null, lim:null};
    const b={
      select(){ return b; }, eq(c,v){st.f.push(['eq',c,v]);return b;}, neq(c,v){st.f.push(['neq',c,v]);return b;},
      in(c,v){st.f.push(['in',c,v]);return b;}, gte(c,v){st.f.push(['gte',c,v]);return b;}, lte(c,v){st.f.push(['lte',c,v]);return b;},
      ilike(c,v){st.f.push(['ilike',c,v]);return b;}, not(c,op,v){ st.f.push(['notin',c,String(v).replace(/[()]/g,'').split(',')]); return b; },
      order(c,o){st.ord=[c,!o||o.ascending!==false];return b;}, limit(k){st.lim=k;return b;},
      single(){st.single=2;return b;}, maybeSingle(){st.single=1;return b;},
      insert(r){st.op='insert';st.rows=[].concat(r);return b;}, upsert(r){st.op='upsert';st.rows=[].concat(r);return b;},
      update(v){st.op='update';st.val=v;return b;}, delete(){st.op='delete';return b;},
      then(res,rej){ return window.__dbop(JSON.stringify(st)).then(JSON.parse).then(res,rej); } };
    return b; }
  let session=null;
  window.supabase={createClient:()=>({ from, channel(){const c={on(){return c;},subscribe(cb){cb&&cb('SUBSCRIBED');return c;}};return c;}, getChannels(){return [];}, removeChannel(){},
    auth:{ async signInWithPassword({email}){ if(!/^tm@/.test(email)) return {data:null,error:{message:'bad'}}; session={user:{id:'u-tm',email}}; return {data:{user:session.user,session},error:null}; },
           async getSession(){ return {data:{session}}; }, async signOut(){ session=null; }, onAuthStateChange(){ return {data:{subscription:{unsubscribe(){}}}}; } } })};
})();
"""
import copy, itertools
STORE=copy.deepcopy(SEED); _ids=itertools.count()
def dbop(spec):
    st=json.loads(spec); T=STORE.setdefault(st['table'],[])
    def match(r):
        for op,c,v in st['f']:
            x=r.get(c)
            if op=='eq' and x!=v: return False
            if op=='neq' and x==v: return False
            if op=='in' and x not in v: return False
            if op=='notin' and x in v: return False
            if op=='gte' and not (x is not None and x>=v): return False
            if op=='lte' and not (x is not None and x<=v): return False
            if op=='ilike' and str(x or '').lower()!=str(v).lower(): return False
        return True
    op=st['op']
    if op=='select':
        out=[r for r in T if match(r)]
        if st['ord']: out.sort(key=lambda r:(r.get(st['ord'][0]) is None, r.get(st['ord'][0]) or ''), reverse=not st['ord'][1])
        if st['lim']: out=out[:st['lim']]
    elif op in ('insert','upsert'):
        out=[]
        for r in st['rows']:
            row=dict(r); row.setdefault('id','r%d'%next(_ids))
            if st['table'] in ('key_requests','bp_custody') and not row.get('created_at'): row['created_at']=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]+'Z'
            key='key' if st['table']=='etk_options' else 'id'
            e=next((x for x in T if x.get(key)==row.get(key)),None)
            (e.update(row) if e else T.append(row)); out.append(row)
    elif op=='update':
        out=[r for r in T if match(r)]
        for r in out: r.update(st['val'])
    else:
        out=[r for r in T if match(r)]; STORE[st['table']]=[r for r in T if not match(r)]
    data=json.loads(json.dumps(out))
    if st['single']: return json.dumps({'data':data[0] if data else None,'error':({'message':'no rows'} if st['single']==2 and not data else None)})
    return json.dumps({'data':data,'error':None})

import os, time, re as _re
res=[]
def ok(c,m): res.append(bool(c)); print(('  PASS ' if c else '  FAIL ')+m)
H='http://localhost:8765'; F=SITE+'/showcomm/etk/index.html'
ORIG=open(F,encoding='utf-8').read()
def bump(n):
    open(F,'w',encoding='utf-8').write(ORIG.replace("const ETK_BUILD='2026-09-30.10'", "const ETK_BUILD='2026-09-30.%d'"%n)); t=time.time()+n; os.utime(F,(t,t))
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(viewport={'width':820,'height':1180})
    ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
    errs=[]
    try:
        print('1. Cart card colors')
        cart=ctx.new_page(); cart.on('pageerror', lambda e: errs.append(str(e)))
        cart.goto(H+'/showcomm/etk/index.html?role=crew'); cart.wait_for_timeout(1200)
        cls=lambda bp: cart.get_attribute(f'.crew-device-card:has(.crew-device-card-id:text-is("{bp}"))','class')
        cart.click('.crew-device-card:has-text("BP05")'); cart.wait_for_timeout(200); cart.fill('#crew-claim-name','Zach'); cart.click('#btn-crew-claim-submit'); cart.wait_for_timeout(700)
        cart.click('#crew-cell-0'); cart.wait_for_timeout(150); cart.click('.crew-picker-opt:text-is("CAMS")'); cart.wait_for_timeout(150)
        cart.click('#crew-submit-btn'); cart.wait_for_timeout(2200)
        ok('pending' in cls('BP05') and 'PENDING' in cart.inner_text('.crew-device-card.pending').upper(),'BP05 after requesting: amber, "Pending"')
        c1=cls('BP01'); ok('ready' not in c1 and 'pending' not in c1,'unclaimed BP01: no color')
        cart.click('.crew-device-card:has-text("BP06")'); cart.wait_for_timeout(200); cart.fill('#crew-claim-name','Ann'); cart.click('#btn-crew-claim-submit'); cart.wait_for_timeout(700)
        cart.evaluate("crewReturnToGrid()"); cart.wait_for_timeout(700)
        ok('ready' in cls('BP06') and 'READY' in cart.inner_text('.crew-device-card.ready').upper(),'BP06 claimed, nothing asked: green, "Ready"')
        for r in STORE['key_requests']:
            if r['device_id']=='BP05': r['status']='fulfilled'      # the TM confirms
        cart.evaluate("crewLoadDevices(true)"); cart.wait_for_timeout(600)
        ok('ready' in cls('BP05'),'TM confirms → BP05 turns green on the next refresh')
        ok(cart.query_selector('#crew-device-list .crew-loading') is None,'refresh is seamless (no "Loading…" flash)')
        cart.screenshot(path='/tmp/cart-colors.png')
        print('2. Update prompt on the TM dashboard')
        tm=ctx.new_page(); tm.on('pageerror', lambda e: errs.append(str(e)))
        tm.goto(H+'/showcomm/etk/index.html?role=tm'); tm.wait_for_timeout(700)
        tm.fill('#login-username','tm'); tm.fill('#login-pw','showcomm'); tm.click('#btn-login'); tm.wait_for_timeout(1500)
        tm.evaluate("etkCheckUpdate(false)"); tm.wait_for_timeout(500)
        ok(tm.query_selector('#etk-update-btn') is None,'no prompt while nothing changed')
        bump(11); tm.evaluate("etkCheckUpdate(false)"); tm.wait_for_timeout(800)
        ok(tm.query_selector('#etk-update-btn') is not None and 'UPDATE READY' in tm.inner_text('#etk-update-btn').upper(),'new build published → "Update ready · tap to reload"')
        tm.click('#etk-update-btn'); tm.wait_for_timeout(1500)
        ok(tm.evaluate("ETK_BUILD")=='2026-09-30.11','tap → running the new build')
        print('3. Cart updates itself, but only when idle')
        cart.click('.crew-device-card:has-text("BP07")'); cart.wait_for_timeout(300)   # someone mid-claim
        cart.evaluate("window.__marker=1"); cart.evaluate("etkCheckUpdate(false)"); cart.wait_for_timeout(1500)
        ok(cart.evaluate("window.__marker")==1 and cart.is_visible('#crew-claim-name'),'mid-claim: does NOT reload')
        cart.evaluate("crewCancelClaimForm()"); cart.evaluate("window._etkLastTouch=0"); cart.wait_for_timeout(11500)
        ok(cart.evaluate("typeof window.__marker")=='undefined' and cart.evaluate("ETK_BUILD")=='2026-09-30.11','idle on the grid: reloads itself onto the new build')
    finally:
        open(F,'w',encoding='utf-8').write(ORIG)
    ok(not errs,'no page errors '+str(errs[:3]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
