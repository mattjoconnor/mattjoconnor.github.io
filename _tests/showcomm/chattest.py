import os
SITE=os.environ.get('SITE','/tmp/site')
import json, datetime
from playwright.sync_api import sync_playwright
now=datetime.datetime.now(datetime.timezone.utc)
iso=lambda d: d.strftime('%Y-%m-%dT%H:%M:%S.000Z')
SEED={'productions':[{'id':'ETK','name':'ETK','control_room':'','dates':'','start_date':'2026-10-01','end_date':'2026-10-16','status':'active','beltpacks':[f'BP{i:02d}' for i in range(1,25)],'keypanels':[],'sort_order':0}],
 'profiles':[{'id':'u-tm','role':'tm','display_name':'TM'},{'id':'u-matt','role':'admin','display_name':'Matt'}],'messages':[],'device_claims':[],'key_requests':[],
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
    auth:{ async signInWithPassword({email}){ const id=/^tm@/.test(email)?'u-tm':/^matt@/.test(email)?'u-matt':null; if(!id) return {data:null,error:{message:'bad'}}; session={user:{id,email}}; return {data:{user:session.user,session},error:null}; },
           async getSession(){ return {data:{session}}; }, async signOut(){ session=null; }, onAuthStateChange(cb){ (window.__authCbs=window.__authCbs||[]).push(cb); return {data:{subscription:{unsubscribe(){}}}}; } } })};
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
            if st['table'] in ('key_requests','bp_custody','messages') and not row.get('created_at'): row['created_at']=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]+'Z'
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
    def login(user, pw_, size=None):
        pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(user+': '+str(e)))
        if size: pg.set_viewport_size(size)
        pg.goto('file://'+SITE+'/showcomm/etk/index.html?role=tm'); pg.wait_for_timeout(700)
        pg.fill('#login-username',user); pg.fill('#login-pw',pw_); pg.click('#btn-login'); pg.wait_for_timeout(1300); return pg
    print('1. Matt signs in on the TM page')
    matt=login('matt','matt',{'width':390,'height':844})
    ok(matt.evaluate("_tmMode")==True and matt.evaluate("_currentRole")=='tm' and matt.evaluate("_currentProfile.role")=='admin','admin gets the TM dashboard, chat knows it’s Matt')
    tabs=matt.eval_on_selector_all('#tm-prod-tabs .ribbon-tab','els=>els.map(e=>e.dataset.view)')
    ok(tabs==['beltpacks','messages','channels','deploy','cart','settings'],'tabs: '+str(tabs))
    ok(matt.inner_text('#tm-role-badge').upper()=='MATT' and 'rgb(30, 158, 94)' in matt.eval_on_selector('#tm-role-badge','e=>getComputedStyle(e).backgroundColor'),'header badge says MATT, in green')
    print('2. A TM messages; Matt sees it')
    tm=login('tm','showcomm')
    ok(tm.inner_text('#tm-role-badge').upper()=='TM','TM login still shows the purple TM badge')
    tm.evaluate("setTMView('messages')"); tm.wait_for_timeout(500)
    ok('No messages yet' in tm.inner_text('#etk-msg-list'),'empty thread explains who it reaches')
    tm.fill('#etk-msg-input','BP07 keeps dropping off CAMS'); tm.click('#etk-msg-send'); tm.wait_for_timeout(500)
    m=STORE['messages'][-1]
    ok(m['sender_role']=='tm' and m['sender_name']=='TM' and m['production_id']=='ETK','saved as from TM')
    ok('You' in tm.inner_text('.etk-msg.mine .etk-msg-meta'),'TM sees their own message as "You", on the right')
    matt.evaluate("etkLoadMessages()"); matt.wait_for_timeout(500)
    print('    tab text:', repr(matt.inner_text('#tm-prod-tabs .ribbon-tab[data-view="messages"]')), '| badge el:', matt.inner_text('#tm-prod-tabs .ribbon-tab[data-view="messages"] .etk-msg-badge') if matt.query_selector('#tm-prod-tabs .ribbon-tab[data-view="messages"] .etk-msg-badge') else None)
    ok(matt.inner_text('#tm-prod-tabs .ribbon-tab[data-view="messages"] .etk-msg-badge')=='1','unread badge on your Messages tab')
    ok(any('Message from TM' in t for t in matt.eval_on_selector_all('.toast, [class*="toast"]','els=>els.map(e=>e.textContent)')),'toast: "Message from TM: …"')
    matt.click('#tm-prod-tabs .ribbon-tab[data-view="messages"]'); matt.wait_for_timeout(600)
    ok('active' in matt.get_attribute('#tm-prod-tabs .ribbon-tab[data-view="messages"]','class'),'tab highlights correctly even with the badge')
    ok('TM' in matt.inner_text('.etk-msg:not(.mine) .etk-msg-meta') and 'CAMS' in matt.inner_text('.etk-msg:not(.mine) .etk-msg-body'),'you see it labeled TM')
    ok(matt.query_selector('#tm-prod-tabs .ribbon-tab[data-view="messages"] .etk-msg-badge') is None,'badge clears once read')
    print('3. Matt replies')
    matt.fill('#etk-msg-input','On my way, swap it for BP31'); matt.click('#etk-msg-send'); matt.wait_for_timeout(500)
    m=STORE['messages'][-1]
    ok(m['sender_role']=='admin' and m['sender_name']=='Matt','saved as from Matt')
    comp=matt.eval_on_selector('.etk-msg-compose','e=>{const r=e.getBoundingClientRect();return r.bottom<=innerHeight+1 && r.top>0}')
    ok(comp,'phone: the compose box sits on screen')
    matt.screenshot(path='/tmp/chat-phone.png')
    tm.evaluate("etkLoadMessages()"); tm.wait_for_timeout(500)
    ok('Matt' in tm.inner_text('.etk-msg:not(.mine) .etk-msg-meta') and 'BP31' in tm.inner_text('.etk-msg:not(.mine)'),'TM sees your reply labeled Matt')
    print('4. Live delivery (the realtime path)')
    tm.evaluate("setTMView('beltpacks')"); tm.wait_for_timeout(400)
    tm.evaluate("etkReceiveMessage({id:'live1',production_id:'ETK',sender_id:'u-matt',sender_role:'admin',sender_name:'Matt',body:'Also check BP12',created_at:new Date().toISOString()})"); tm.wait_for_timeout(300)
    ok(tm.query_selector('#tm-prod-tabs .ribbon-tab[data-view="messages"] .etk-msg-badge') is not None and tm.inner_text('#tm-prod-tabs .ribbon-tab[data-view="messages"] .etk-msg-badge')=='1','live message on another tab → badge')
    tm.evaluate("etkReceiveMessage({id:'live1',production_id:'ETK',sender_id:'u-matt',sender_role:'admin',body:'dup',created_at:new Date().toISOString()})")
    ok(tm.evaluate("_etkMsgs.filter(m=>m.id==='live1').length")==1,'the same message arriving twice shows once')
    print('5. Another tab changes the login (Android shares it with Chrome)')
    matt.evaluate("window.__reloaded=false; (window.__authCbs||[]).forEach(cb=>cb('TOKEN_REFRESHED',{user:{id:'u-matt'}}))"); matt.wait_for_timeout(1800)
    ok(matt.evaluate("_tmMode")==True and matt.inner_text('#tm-role-badge').upper()=='MATT','a routine token refresh changes nothing')
    matt.evaluate("(window.__authCbs||[]).forEach(cb=>cb('SIGNED_IN',{user:{id:'u-tm'}}))"); matt.wait_for_timeout(400)
    ok(any('different account in another tab' in t for t in matt.eval_on_selector_all('.toast, [class*="toast"]','els=>els.map(e=>e.textContent)')),'says the login changed in another tab')
    matt.wait_for_timeout(2000)
    ok(matt.evaluate("typeof _tmMode==='undefined' || _tmMode===false") and matt.is_visible('#login-username'),'reloads, so it can’t keep acting under the wrong name')
    ok(not errs,'no page errors '+str(errs[:3]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
