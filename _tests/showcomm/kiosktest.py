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
    b=pw.chromium.launch(); ctx=b.new_context(viewport={'width':820,'height':1180})
    ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
    errs=[]
    def pg(path):
        p=ctx.new_page(); p.on('pageerror', lambda e: errs.append(str(e))); p.goto(H+path); p.wait_for_timeout(1300); return p
    mode=lambda p: p.evaluate("localStorage.getItem('etk_mode')")
    crew_on=lambda p: p.evaluate("document.getElementById('screen-crew').style.display")=='flex'
    print('1. Installed cart launching')
    a=pg('/showcomm/etk/crew/')
    ok(crew_on(a) and mode(a)=='crew','start address /showcomm/etk/crew/ → cart, and the device remembers "crew"')
    c=pg('/showcomm/etk/index.html')
    ok(crew_on(c) and not c.is_visible('.login-role-grid'),'launch with NO role in the address → still the cart (no login gate)')
    cdp=ctx.new_cdp_session(c); man=json.loads(cdp.send('Page.getAppManifest').get('data') or '{}')
    ok(man.get('name')=='ETK Cart' and man.get('start_url','').endswith('/showcomm/etk/crew/'),'installs as ETK Cart, starting at /showcomm/etk/crew/')
    print('2. Explicit addresses win')
    t=pg('/showcomm/etk/tm')
    ok(not crew_on(t) and t.is_visible('#login-username') and mode(t)=='tm','the TM link on the same device opens the TM login')
    t.fill('#login-username','tm'); t.fill('#login-pw','showcomm'); t.click('#btn-login'); t.wait_for_timeout(1500)
    t.evaluate("setTMView('cart')"); t.wait_for_timeout(1500)
    ok(mode(t)=='tm','opening the TM dashboard’s Cart tab doesn’t turn the laptop into a cart')
    print('3. Errors are shown, not silent')
    e=pg('/showcomm/etk/crew/')
    e.evaluate("setTimeout(()=>{ throw new Error('test failure') }, 0); 0"); e.wait_for_timeout(300)
    box=e.inner_text('#etk-err') if e.query_selector('#etk-err') else ''
    ok('test failure' in box and 'build' in box,'error box shows the problem and build: '+box[:70])
    b.close()
real=[x for x in errs if 'test failure' not in x]
ok(not real,'no other page errors '+str(real[:2]))
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
