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
N=lambda m: iso(now-datetime.timedelta(minutes=m))
J=lambda *e: json.dumps([dict(keyIndex=k,label=f'Key {k+1}',note=n,**({'latch':True} if l else {})) for k,n,l in e])
STORE['device_claims']+=[{'id':'c3','production_id':'ETK','device_type':'beltpack','device_id':'BP03','crew_name':'Zach','crew_position':'','status':'confirmed','claimed_at':N(90)},
                         {'id':'c5','production_id':'ETK','device_type':'beltpack','device_id':'BP05','crew_name':'Ann','crew_position':'','status':'confirmed','claimed_at':N(80)}]
STORE['key_requests']+=[{'id':'f3','production_id':'ETK','device_id':'BP03','status':'fulfilled','requester_role':'crew','created_at':N(85),'note':J((0,'CAMS (PL)',0))},
                        {'id':'f5','production_id':'ETK','device_id':'BP05','status':'fulfilled','requester_role':'crew','created_at':N(75),'note':J((0,'CAMS (PL)',1),(1,'AUD (PL)',0))}]
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(viewport={'width':820,'height':1180})
    ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
    errs=[]
    def pg(qs):
        p=ctx.new_page(); p.on('pageerror', lambda e: errs.append(str(e))); p.goto('file://'+SITE+'/showcomm/etk/index.html'+qs); p.wait_for_timeout(900); return p
    print('1. Blank on the cart')
    cart=pg('?role=crew')
    cart.click('.crew-device-card:has-text("BP05")'); cart.wait_for_timeout(900)
    cart.click('#crew-cell-2'); cart.wait_for_timeout(200)
    ok(cart.query_selector('.crew-picker-opt.blank') is None,'empty key 3: no Blank option (nothing to clear)')
    cart.click('#crew-cell-1'); cart.wait_for_timeout(200); cart.click('.crew-picker-selected'); cart.wait_for_timeout(150)
    ok(cart.is_visible('.crew-picker-opt.blank'),'key 2 (AUD): Blank offered at the top')
    cart.click('.crew-picker-opt.blank'); cart.wait_for_timeout(200)
    ok('BLANK' in cart.inner_text('#crew-cell-1').upper(),'key 2 now reads Blank (pending)')
    ok('undo' in cart.inner_text('.crew-picker-opt.blank').lower(),'picker stays open: "Tap again to undo"')
    cart.click('.crew-picker-opt.blank'); cart.wait_for_timeout(200)
    ok('AUD' in cart.inner_text('#crew-cell-1'),'tapping Blank again undoes it')
    if cart.query_selector('.crew-picker-selected'): cart.click('.crew-picker-selected'); cart.wait_for_timeout(150)
    cart.click('.crew-picker-opt.blank'); cart.wait_for_timeout(200)
    cart.click('#crew-submit-btn'); cart.wait_for_timeout(1600)
    r=[x for x in STORE['key_requests'] if x['device_id']=='BP05' and x['status']=='open'][-1]
    ok(json.loads(r['note'])==[{'keyIndex':1,'label':'Key 2','note':'CLEAR'}],'submitted as a CLEAR for key 2')
    tm=pg('?role=tm'); tm.fill('#login-username','tm'); tm.fill('#login-pw','showcomm'); tm.click('#btn-login'); tm.wait_for_timeout(1500)
    ok('CLEAR' in tm.inner_text('#etk-queue-item-BP05').upper(),'TM queue shows CLEAR on BP05')
    tm.click('#etk-queue-item-BP05 .etk-queue-confirm'); tm.wait_for_timeout(900)
    k=tm.evaluate("etkPackKeys(_etkBpData.BP05.reqs,_etkBpData.BP05.claim).map(k=>k.on&&k.on.label)")
    ok(k==['CAMS',None,None,None],'after confirm: key 2 empty, CAMS untouched '+str(k))
    print('2. TM edits a claimed pack (Zach, BP03)')
    notes_before=tm.evaluate("(window.__notesCount=0, 0)")
    tm.evaluate("window.__alertCount=0; window.etkChime=()=>{window.__alertCount++;}; 0")   # end with a value (a trailing function would get called)
    tm.evaluate("etkAlertTick()"); tm.wait_for_timeout(300)
    tm.click('#etk-all-toggle'); tm.wait_for_timeout(300)
    tm.click('#etk-bp-status-grid .etk-queue-item:has(.etk-queue-item-id:text-is("BP03")) .etk-edit-btn'); tm.wait_for_timeout(300)
    rows=tm.query_selector_all('#etk-edit-overlay .etk-edit-row')
    ok(len(rows)==4 and 'CAMS' in rows[0].inner_text(),'editor lists 4 keys with what’s on the pack')
    rows[0].query_selector('input').check()                       # latch-only change on key 1
    rows[2].query_selector('select').select_option('IFBs|HOST')   # key 3 → HOST
    tm.click('#etk-edit-save'); tm.wait_for_timeout(900)
    r=[x for x in STORE['key_requests'] if x['device_id']=='BP03' and x['status']=='open'][-1]
    ents=json.loads(r['note'])
    ok(r['requester_role']=='tm' and ents==[{'keyIndex':0,'label':'Key 1','note':'CAMS (PL)','latch':True},{'keyIndex':2,'label':'Key 3','note':'HOST (IFB)'}],'queued as a TM request: key 1 latch on, key 3 HOST')
    ok(tm.query_selector('#etk-queue-item-BP03') is not None,'BP03 appears in Needs Programming')
    tm.evaluate("etkAlertTick()"); tm.wait_for_timeout(400)
    ok(tm.evaluate("window.__alertCount")==0,'no chime or popup for the TM’s own edit')
    cart2=pg('?role=crew'); cart2.wait_for_timeout(400)
    cls=cart2.get_attribute('.crew-device-card:has(.crew-device-card-id:text-is("BP03"))','class')
    ok('pending' in cls,'cart shows BP03 amber (Pending)')
    print('3. TM edits an unclaimed pack (BP09), and guards')
    tm.click('#etk-bp-status-grid .etk-queue-item:has(.etk-queue-item-id:text-is("BP09")) .etk-edit-btn'); tm.wait_for_timeout(300)
    rows=tm.query_selector_all('#etk-edit-overlay .etk-edit-row')
    tm.click('#etk-edit-save'); tm.wait_for_timeout(200)
    ok('Nothing changed' in tm.inner_text('#etk-edit-err'),'nothing changed: says so, saves nothing')
    rows[0].query_selector('select').select_option('PLs|TECH'); rows[1].query_selector('select').select_option('PLs|TECH')
    tm.click('#etk-edit-save'); tm.wait_for_timeout(200)
    ok('two keys' in tm.inner_text('#etk-edit-err'),'same PL on two keys: blocked with a clear message')
    rows[1].query_selector('select').select_option('')
    tm.click('#etk-edit-save'); tm.wait_for_timeout(900)
    q=tm.query_selector('#etk-queue-item-BP09')
    ok(q is not None and 'Unclaimed' in q.inner_text() and 'TECH' in q.inner_text(),'unclaimed BP09 shows in the queue with TECH')
    tm.click('#etk-queue-item-BP09 .etk-queue-confirm'); tm.wait_for_timeout(900)
    ok(all(x['status']=='fulfilled' for x in STORE['key_requests'] if x['device_id']=='BP09'),'Confirm Programmed works on an unclaimed pack')
    tm.screenshot(path='/tmp/ui/tm-after-edit.png')
    ok(not errs,'no page errors '+str(errs[:2]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
