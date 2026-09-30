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



res=[]
def ok(c,m): res.append(bool(c)); print(('  PASS ' if c else '  FAIL ')+m)
H='http://localhost:8765'
with sync_playwright() as pw:
    b=pw.chromium.launch(channel='chromium'); ctx=b.new_context(viewport={'width':390,'height':844}, is_mobile=True, permissions=['notifications'])
    ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop)
    ctx.add_init_script(MOCK.replace("window.__notes=[]; window.Notification=function(t,o){ window.__notes.push({t,body:o&&o.body}); this.close=()=>{}; }; window.Notification.permission='granted'; window.Notification.requestPermission=async()=>'granted';",""))
    errs=[]
    print('3. A push arriving at ShowPoint’s worker')
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(H+'/'); pg.wait_for_timeout(1500)
    pg.evaluate("navigator.serviceWorker.ready.then(()=>true)")          # wait until the worker is really active (slow machines vary)
    cdp=ctx.new_cdp_session(pg); regs=[]
    cdp.on('ServiceWorker.workerRegistrationUpdated', lambda e: regs.extend(e['registrations']))
    cdp.send('ServiceWorker.enable')
    for _ in range(50):                                                   # up to 5 s for the registration report
        if any(r['scopeURL']==H+'/' for r in regs): break
        pg.wait_for_timeout(100)
    rid=[r['registrationId'] for r in regs if r['scopeURL']==H+'/'][0]
    cdp.send('ServiceWorker.deliverPushMessage', {'origin':H,'registrationId':rid,'data':json.dumps({'title':'BP05 · Priya','body':'Key 2 → TECH (latch)','tag':'etk-r1','url':'/showcomm/etk/index.html?role=tm'})})
    pg.wait_for_timeout(1200)
    n=pg.evaluate("navigator.serviceWorker.getRegistration('/').then(r=>r.getNotifications()).then(ns=>ns.map(x=>({t:x.title,b:x.body,u:x.data&&x.data.url})))")
    ok(any(x['t']=='BP05 · Priya' and x['b']=='Key 2 → TECH (latch)' and x['u'].endswith('role=tm') for x in n),'worker shows it: '+str(n))
    cdp.send('ServiceWorker.deliverPushMessage', {'origin':H,'registrationId':rid,'data':'not json'}); pg.wait_for_timeout(800)
    n2=pg.evaluate("navigator.serviceWorker.getRegistration('/').then(r=>r.getNotifications()).then(ns=>ns.map(x=>x.title+' / '+x.body))")
    ok(any('ShowComm / not json' in x for x in n2),'a malformed push still shows a basic alert (no silent failure)')
    print('4. ShowComm when push can’t register')
    tm=ctx.new_page(); tm.on('pageerror', lambda e: errs.append(str(e)))
    tm.goto(H+'/showcomm/etk/index.html?role=tm'); tm.wait_for_timeout(1200)
    tm.fill('#login-username','tm'); tm.fill('#login-pw','showcomm'); tm.click('#btn-login'); tm.wait_for_timeout(2500)
    ok(tm.get_attribute('#tm-alerts-btn','aria-label')=='Alerts on' and tm.evaluate("_etkPushOn")==False,'no push service reachable: stays "Alerts on", falls back to popups')
    ok(tm.evaluate("_tmActiveView")=='beltpacks' and tm.query_selector('#etk-queue-list') is not None,'dashboard works normally')
    ok(not errs,'no page errors '+str(errs[:3]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
