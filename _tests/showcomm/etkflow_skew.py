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
import copy, itertools, os
BREAK_GTE = os.environ.get('BREAK_GTE')=='1'   # simulate the database's time comparison disagreeing with the app
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
            if op=='gte' and (BREAK_GTE or not (x is not None and x>=v)): return False
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
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(viewport={'width':1280,'height':900})
    ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
    errs=[]
    def page(qs):
        pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(qs+': '+str(e))); pg.goto('file://'+SITE+'/showcomm/etk/index.html'+qs); pg.wait_for_timeout(700); return pg
    DB=lambda pg: STORE
    def claim(cart, bp, name):
        cart.click(f'.crew-device-card:has-text("{bp}")'); cart.wait_for_timeout(200)
        cart.fill('#crew-claim-name', name); cart.click('#btn-crew-claim-submit'); cart.wait_for_timeout(700)
    def pick(cart, idx, label, change=False):
        cart.click(f'#crew-cell-{idx}'); cart.wait_for_timeout(150)
        if change: cart.click('.crew-picker-selected'); cart.wait_for_timeout(100)
        cart.click(f'.crew-picker-opt:text-is("{label}")'); cart.wait_for_timeout(150)
    print('1. Zach claims BP05, requests CAMS (latch) + AUD')
    cart=page('?role=crew')
    claim(cart,'BP05','Zach')
    pick(cart,0,'CAMS')
    ok(cart.query_selector('.crew-latch-btn') is not None,'a Latch toggle appears after picking a PL')
    cart.click('.crew-latch-btn'); cart.wait_for_timeout(150)
    ok('LATCH' in cart.inner_text('#crew-cell-0').upper(),'key 1 shows Latch on the cart')
    pick(cart,1,'AUD')
    cart.click('#crew-submit-btn'); cart.wait_for_timeout(1600)
    kr=DB(cart)['key_requests']
    ents=json.loads(kr[0]['note']) if kr else []
    ok(len(kr)==1 and ents[0].get('latch') is True and ents[0]['note']=='CAMS (PL)' and 'latch' not in ents[1],'saved: key 1 CAMS with latch flag, key 2 AUD without')
    print('2. TM sees it and confirms')
    tm=page('?role=tm')
    tm.fill('#login-username','tm'); tm.fill('#login-pw','showcomm'); tm.click('#btn-login'); tm.wait_for_timeout(1200)
    ok(tm.title()=='(1) ShowComm TM','tab title shows the count: '+tm.title())
    q=tm.inner_text('#etk-queue-item-BP05') if tm.query_selector('#etk-queue-item-BP05') else ''
    ok('CAMS' in q and 'LATCH' in q and 'AUD' in q,'queue: BP05 with CAMS + LATCH tag, AUD')
    tm.click('#etk-queue-item-BP05 .etk-queue-confirm'); tm.wait_for_timeout(600)
    ok(all(r['status']=='fulfilled' for r in DB(tm)['key_requests']),'Confirm Programmed marks them done')
    ok(tm.title()=='ShowComm TM','title count clears: '+tm.title())
    print('3. Zach releases; Priya claims BP05 and sees what is really on it')
    cart.reload(); cart.wait_for_timeout(700)
    cart.click('.crew-device-card:has-text("BP05")'); cart.wait_for_timeout(600)
    cart.evaluate("crewShowReleaseConfirm()"); cart.wait_for_timeout(150); cart.evaluate("crewConfirmRelease()"); cart.wait_for_timeout(800)
    claim(cart,'BP05','Priya')
    c0=cart.inner_text('#crew-cell-0'); c1=cart.inner_text('#crew-cell-1')
    ok('CAMS' in c0 and 'LATCH' in c0.upper() and 'AUD' in c1,'Priya sees CAMS (latch) and AUD, not an empty pack')
    print('4. Priya changes key 2 to TECH; TM is alerted')
    tm.evaluate("etkAlertTick()"); tm.wait_for_timeout(300)   # baseline
    pick(cart,1,'TECH',change=True)
    cart.click('#crew-submit-btn'); cart.wait_for_timeout(1600)
    tm.evaluate("setTMView('deploy')"); tm.wait_for_timeout(400)
    tm.evaluate("etkAlertTick()"); tm.wait_for_timeout(500)
    notes=tm.evaluate("window.__notes")
    ok(any(n['t']=='BP05 · Priya' and 'Key 2 → TECH' in (n['body'] or '') for n in notes),'desktop popup: "BP05 · Priya / Key 2 → TECH" '+str(notes[-1:]))
    ok(tm.title()=='(1) ShowComm TM','title count back to 1 while on another tab')
    tm.evaluate("setTMView('beltpacks')"); tm.wait_for_timeout(600)
    k=tm.evaluate("_etkBpData.BP05.keys.map(k=>k.urg+':'+(k.rec&&k.rec.parsed?k.rec.parsed.label:'-'))")
    ok(k[0]=='green:CAMS' and k[1]=='red:TECH','queue: key 1 CAMS already on (no action), key 2 TECH is the change '+str(k))
    print('5. Channels tab')
    tm.evaluate("setTMView('channels')"); tm.wait_for_timeout(700)
    card=lambda l: tm.inner_text(f'.etk-ch-card:has(.etk-ch-head b:text-is("{l}"))')
    ok('BP05' in card('CAMS') and 'Priya' in card('CAMS') and 'LATCH' in card('CAMS'),'CAMS: BP05 Priya, LATCH')
    ok('BP05' in card('AUD') and 'CHANGING' in card('AUD').upper(),'AUD: BP05 marked changing')
    ok('BP05' in card('TECH') and 'REQUESTED' in card('TECH').upper(),'TECH: BP05 marked requested')
    ok('Nobody' in card('HOST'),'HOST: nobody on it')
    tm.screenshot(path='/tmp/etk-channels.png')
    print('6. Priya leaves before the TM confirms; Lee takes BP05')
    cart.reload(); cart.wait_for_timeout(700)
    cart.click('.crew-device-card:has-text("BP05")'); cart.wait_for_timeout(600)
    cart.evaluate("crewShowReleaseConfirm()"); cart.wait_for_timeout(150); cart.evaluate("crewConfirmRelease()"); cart.wait_for_timeout(800)
    claim(cart,'BP05','Lee')
    ok('AUD' in cart.inner_text('#crew-cell-1') and 'TECH' not in cart.inner_text('#crew-cell-1'),'Lee sees AUD (on the pack); Priya’s unconfirmed TECH does not carry over')
    tm.evaluate("setTMView('beltpacks')"); tm.wait_for_timeout(700)
    ok(tm.query_selector('#etk-queue-item-BP05') is None,'nothing queued for BP05: Lee hasn’t asked for anything')
    print('7. Pack left out since two days ago')
    ban=tm.inner_text('.etk-overdue-banner') if tm.query_selector('.etk-overdue-banner') else ''
    ok('BP09' in ban,'Beltpacks banner: BP09 not returned since yesterday')
    tm.evaluate("setTMView('deploy')"); tm.wait_for_timeout(700)
    t9=tm.query_selector('.etk-deploy-tile:has-text("BP09")')
    ok(t9 and 'overdue' in t9.get_attribute('class') and 'NOT RETURNED' in t9.inner_text().upper(),'Deploy: BP09 tile red, "Not returned"')
    ok(tm.is_visible('#etk-count-late-box') and tm.inner_text('#etk-count-late')=='1','Deploy counter: 1 not returned')
    tm.screenshot(path='/tmp/etk-deploy.png')
    t9.click(); tm.wait_for_timeout(600)
    ok('overdue' not in (tm.query_selector('.etk-deploy-tile:has-text("BP09")').get_attribute('class') or ''),'checking BP09 in clears the flag')
    ok(not errs,'no page errors '+str(errs[:3]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
