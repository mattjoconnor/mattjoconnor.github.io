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
    b=pw.chromium.launch(channel='chromium'); ctx=b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2, is_mobile=True, has_touch=True, permissions=['notifications'])
    ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop)
    ctx.add_init_script(MOCK.replace("window.__notes=[]; window.Notification=function(t,o){ window.__notes.push({t,body:o&&o.body}); this.close=()=>{}; }; window.Notification.permission='granted'; window.Notification.requestPermission=async()=>'granted';",""))
    errs=[]
    def man(pg):
        cdp=ctx.new_cdp_session(pg); m=cdp.send('Page.getAppManifest'); i=cdp.send('Page.getInstallabilityErrors')
        return json.loads(m.get('data') or '{}'), [e for e in i.get('installabilityErrors',[]) if e.get('errorId')!='in-incognito']
    regs=lambda pg: pg.evaluate("navigator.serviceWorker.getRegistrations().then(rs=>rs.map(r=>r.scope))")
    print('1. Upgrading a phone that has the old ShowComm worker')
    pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(H+'/showcomm/etk/manifest-tm.json'); pg.evaluate("navigator.serviceWorker.register('/showcomm/etk/sw.js',{scope:'/showcomm/etk/'})"); pg.wait_for_timeout(800)
    pg.goto(H+'/showcomm/etk/index.html?role=tm'); pg.wait_for_timeout(2000)
    r=regs(pg); ok(r==[H+'/'],'old per-app worker removed; only ShowPoint’s site-wide worker remains '+str(r))
    d,e=man(pg); ok(d.get('name')=='ShowPoint' and not e,'TM page now installs as ShowPoint '+str(d.get('name'))+str(e))
    print('2. ShowPoint home')
    pg.goto(H+'/'); pg.wait_for_timeout(1200)
    d,e=man(pg); ok(d.get('name')=='ShowPoint' and d.get('scope')=='/' and not e,'home: installable as ShowPoint, covering the whole site')
    tiles=pg.eval_on_selector_all('.app','els=>els.map(a=>a.getAttribute("href"))')
    ok(tiles==['/showcomm/etk/index.html?role=tm','/showgear/'],'two tiles: ShowComm and ShowGear '+str(tiles))
    ok(not pg.evaluate("document.documentElement.scrollWidth>innerWidth+1"),'home fits a phone screen')
    pg.screenshot(path='/tmp/sp-home.png')
    pg.click('.app:has-text("ShowComm")'); pg.wait_for_timeout(1500)
    ok('/showcomm/etk/' in pg.url and pg.is_visible('#login-username'),'ShowComm tile opens the TM login')
    ok(pg.evaluate("navigator.serviceWorker.controller&&navigator.serviceWorker.controller.scriptURL")==H+'/sw.js','ShowComm runs under the ShowPoint worker')
    print('3. Wordmark switcher')
    pg.fill('#login-username','tm'); pg.fill('#login-pw','showcomm'); pg.click('#btn-login'); pg.wait_for_timeout(1500)
    ok(pg.get_attribute('#tm-ribbon .wm-home','href')=='/','ShowComm wordmark links to ShowPoint home')
    pg.click('#tm-ribbon .wm-home'); pg.wait_for_timeout(1000)
    ok(pg.url==H+'/' and pg.is_visible('.app'),'tapping it goes home')
    pg.click('.app:has-text("ShowGear")'); pg.wait_for_timeout(1500)
    ok(pg.get_attribute('.r-brand .wm-home','href')=='/' and pg.evaluate("getComputedStyle(document.querySelector('.r-brand .wm-home')).pointerEvents")!='none','ShowGear wordmark links home')
    d,e=man(pg); ok(d.get('name')=='ShowPoint','ShowGear is part of ShowPoint too')
    sg=ctx.new_page(); sg.goto(H+'/showgear/?prod=ETK'); sg.wait_for_timeout(1200)
    ok(sg.evaluate("getComputedStyle(document.querySelector('.r-brand .wm-home')).pointerEvents")=='none','QR show page: wordmark does nothing (no way into the suite)')
    print('4. Cart stays its own app; popups through ShowPoint’s worker')
    cart=ctx.new_page(); cart.goto(H+'/showcomm/etk/index.html?role=crew'); cart.wait_for_timeout(1500)
    d,e=man(cart); ok(d.get('name')=='ETK Cart','cart still installs as ETK Cart (for the iPad)')
    tm=ctx.new_page(); tm.goto(H+'/showcomm/etk/index.html?role=tm'); tm.wait_for_timeout(1200)
    tm.fill('#login-username','tm'); tm.fill('#login-pw','showcomm'); tm.click('#btn-login'); tm.wait_for_timeout(1500)
    tm.evaluate("etkAlertTick()"); tm.wait_for_timeout(400)
    cart.click('.crew-device-card:has-text("BP10")'); cart.wait_for_timeout(300); cart.fill('#crew-claim-name','Rae'); cart.click('#btn-crew-claim-submit'); cart.wait_for_timeout(900)
    cart.click('#crew-cell-0'); cart.wait_for_timeout(200); cart.click('.crew-picker-opt:text-is("LITE")'); cart.wait_for_timeout(200); cart.click('#crew-submit-btn'); cart.wait_for_timeout(1600)
    tm.evaluate("etkAlertTick()"); tm.wait_for_timeout(800)
    notes=tm.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.scope+' :: '+'|'.join?'' : r).catch(()=>'')")
    notes=tm.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.getNotifications().then(n=>[r.scope, n.map(x=>x.title+' / '+x.body)]))")
    ok(notes[0]==H+'/' and any('BP10 · Rae' in n and 'LITE' in n for n in notes[1]),'popup delivered by ShowPoint’s worker: '+str(notes))
    ok(not errs,'no page errors '+str(errs[:3]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
