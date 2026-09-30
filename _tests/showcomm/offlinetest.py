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
NET={'down':False}
def dbop(spec):
    if NET['down']: return json.dumps({'data':None,'error':{'message':'TypeError: Failed to fetch'}})
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
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(viewport={'width':820,'height':1180})
    ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
    errs=[]
    cart=ctx.new_page(); cart.on('pageerror', lambda e: errs.append(str(e)))
    cart.goto('file://'+SITE+'/showcomm/etk/index.html?role=crew'); cart.wait_for_timeout(800)
    banner=lambda pg: (pg.get_attribute('#etk-conn-banner','class') or '', pg.inner_text('#etk-conn-banner')) if pg.query_selector('#etk-conn-banner') else ('','')
    ok(('build '+cart.evaluate('ETK_BUILD')) in cart.inner_text('#crew-build'),'build number on the cart grid')
    print('1. Dead spot mid-request')
    cart.click('.crew-device-card:has-text("BP05")'); cart.wait_for_timeout(200); cart.fill('#crew-claim-name','Zach'); cart.click('#btn-crew-claim-submit'); cart.wait_for_timeout(700)
    cart.click('#crew-cell-0'); cart.wait_for_timeout(150); cart.click('.crew-picker-opt:text-is("CAMS")'); cart.wait_for_timeout(150)
    NET['down']=True; cart.evaluate("etkConnCheck()"); cart.wait_for_timeout(500)
    c,tx=banner(cart)
    ok('off' in c and 'show' in c and 'iPad is back online' in tx,'red banner: '+tx)
    ok(cart.is_disabled('#crew-submit-btn') and 'WAITING' in cart.inner_text('#crew-submit-btn').upper(),'Submit locked: "Waiting for connection…"')
    ok('CAMS' in cart.inner_text('#crew-cell-0'),'their pick is still there')
    before=len(STORE['key_requests'])
    cart.evaluate("crewSubmitBundle()"); cart.wait_for_timeout(300)
    ok(len(STORE['key_requests'])==before,'nothing sent into the void')
    NET['down']=False; cart.evaluate("etkConnCheck()"); cart.wait_for_timeout(500)
    c,tx=banner(cart)
    ok('on' in c and 'Back online' in tx,'green "Back online"')
    ok(not cart.is_disabled('#crew-submit-btn') and 'SUBMIT' in cart.inner_text('#crew-submit-btn').upper(),'Submit unlocked')
    cart.wait_for_timeout(2700); ok('show' not in (cart.get_attribute('#etk-conn-banner','class') or ''),'banner slides away')
    cart.click('#crew-submit-btn'); cart.wait_for_timeout(1600)
    ok(len(STORE['key_requests'])==before+1,'request goes through once back')
    print('2. Wi-Fi drops right as someone claims')
    cart.click('.crew-device-card:has-text("BP06")'); cart.wait_for_timeout(200); cart.fill('#crew-claim-name','Ann')
    NET['down']=True; cart.click('#btn-crew-claim-submit'); cart.wait_for_timeout(700)
    ok(cart.is_visible('#crew-claim-name') and cart.input_value('#crew-claim-name')=='Ann','stays on the form, name kept (no bounce to the grid)')
    ok('No connection' in cart.inner_text('#crew-claim-error') and 'off' in banner(cart)[0],'explains it; banner up')
    ok(cart.is_disabled('#btn-crew-claim-submit'),'Claim locked while offline')
    NET['down']=False; cart.evaluate("etkConnCheck()"); cart.wait_for_timeout(500)
    cart.click('#btn-crew-claim-submit'); cart.wait_for_timeout(800)
    ok(any(c_['device_id']=='BP06' and c_['crew_name']=='Ann' for c_ in STORE['device_claims']),'claims fine once back')
    print('2b. Release during an outage')
    NET['down']=True; cart.evaluate("etkConnCheck()"); cart.wait_for_timeout(400)
    cart.evaluate("crewShowReleaseConfirm()"); cart.wait_for_timeout(150); cart.evaluate("crewConfirmRelease()"); cart.wait_for_timeout(400)
    ok([c_['status'] for c_ in STORE['device_claims'] if c_['device_id']=='BP06'][-1]=='confirmed' and cart.evaluate("_crewClaim&&_crewClaim.device_id")=='BP06','offline release: BP06 stays Ann’s, still on her screen')
    NET['down']=False; cart.evaluate("etkConnCheck()"); cart.wait_for_timeout(500)
    print('3. The device’s own offline signal')
    ctx.set_offline(True); cart.wait_for_timeout(400)
    ok('off' in banner(cart)[0],'airplane mode / Wi-Fi off: banner immediately')
    ctx.set_offline(False); cart.wait_for_timeout(800)
    ok('on' in banner(cart)[0],'back on: "Back online"')
    cart.screenshot(path='/tmp/offline-cart.png')
    print('4. TM dashboard')
    tm=ctx.new_page(); tm.on('pageerror', lambda e: errs.append(str(e)))
    tm.goto('file://'+SITE+'/showcomm/etk/index.html?role=tm'); tm.wait_for_timeout(700)
    tm.fill('#login-username','tm'); tm.fill('#login-pw','showcomm'); tm.click('#btn-login'); tm.wait_for_timeout(1300)
    NET['down']=True; tm.evaluate("etkConnCheck()"); tm.wait_for_timeout(400)
    ok('board may be out of date' in banner(tm)[1],'TM sees: '+banner(tm)[1])
    NET['down']=False; tm.evaluate("etkConnCheck()"); tm.wait_for_timeout(800)
    ok('on' in banner(tm)[0] and tm.query_selector('#etk-queue-list') is not None,'TM back online, board refreshed')
    ok(not errs,'no page errors '+str(errs[:3]))
    NET['down']=True; cart.evaluate("etkConnCheck()"); cart.wait_for_timeout(500); cart.screenshot(path='/tmp/offline-cart.png'); NET['down']=False
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
