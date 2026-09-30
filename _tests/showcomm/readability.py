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
    auth:{ async signInWithPassword({email}){ const id=/^tm@/.test(email)?'u-tm':/^matt@/.test(email)?'u-matt':null; if(!id) return {data:null,error:{message:'bad'}}; session={user:{id,email}}; return {data:{user:session.user,session},error:null}; },
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

import sys, os
AUDIT=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'audit.js')).read()
TAG=sys.argv[1] if len(sys.argv)>1 else 'before'
os.makedirs(f'/tmp/ui/{TAG}', exist_ok=True)
N=lambda m: iso(now-datetime.timedelta(minutes=m))
J=lambda *e: json.dumps([dict(keyIndex=k,label=f'Key {k+1}',note=n,**({'latch':True} if l else {})) for k,n,l in e])
STORE['profiles'].append({'id':'u-matt','role':'admin','display_name':'Matt'})
STORE['device_claims']+= [{'id':'c3','production_id':'ETK','device_type':'beltpack','device_id':'BP03','crew_name':'Zach','crew_position':'','status':'confirmed','claimed_at':N(90)},
                          {'id':'c7','production_id':'ETK','device_type':'beltpack','device_id':'BP07','crew_name':'Priya','crew_position':'','status':'confirmed','claimed_at':N(60)},
                          {'id':'c11','production_id':'ETK','device_type':'beltpack','device_id':'BP11','crew_name':'Sam','crew_position':'','status':'confirmed','claimed_at':N(50)}]
STORE['key_requests']+=[{'id':'k1','production_id':'ETK','device_id':'BP03','status':'fulfilled','created_at':N(80),'note':J((0,'CAMS (PL)',1),(1,'AUD (PL)',0))},
                        {'id':'k2','production_id':'ETK','device_id':'BP03','status':'open','created_at':N(20),'note':J((1,'TECH (PL)',0),(2,'HOST (IFB)',0))},
                        {'id':'k3','production_id':'ETK','device_id':'BP07','status':'open','created_at':N(10),'note':J((0,'AD (PL)',0))},
                        {'id':'k4','production_id':'ETK','device_id':'BP11','status':'fulfilled','created_at':N(40),'note':J((0,'PROD (PL)',0),(1,'CUL (PL)',1))}]
STORE['messages']=[{'id':'m1','production_id':'ETK','sender_id':'u-tm','sender_role':'tm','sender_name':'TM','body':'BP07 keeps dropping off CAMS','created_at':N(30)},
                   {'id':'m2','production_id':'ETK','sender_id':'u-matt','sender_role':'admin','sender_name':'Matt','body':'On my way, swap it for BP31','created_at':N(28)}]
issues={}
def audit(pg, state):
    rows=pg.evaluate(AUDIT)
    bad=[r for r in rows if (r['fs']<12 or (not r['imgBg'] and r['contrast']<r['need']))]
    for r in bad:
        k=(r['cls'] or '(no class)', r['text'][:28]); issues.setdefault(k, []).append((state, r['fs'], r['contrast']))
    pg.screenshot(path=f'/tmp/ui/{TAG}/{state}.png', full_page=False)
    return len(rows), len(bad)
with sync_playwright() as pw:
    b=pw.chromium.launch()
    for scheme in ('light','dark'):
        for vw,vh,dev in ((390,844,'phone'),(1280,900,'laptop')):
            ctx=b.new_context(viewport={'width':vw,'height':vh}, color_scheme=scheme, device_scale_factor=1)
            ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
            tm=ctx.new_page(); tm.goto('file://'+SITE+'/showcomm/etk/index.html?role=tm'); tm.wait_for_timeout(700)
            print(f'[{scheme}/{dev}] login', audit(tm, f'{scheme}-{dev}-login'))
            tm.fill('#login-username','tm'); tm.fill('#login-pw','showcomm'); tm.click('#btn-login'); tm.wait_for_timeout(1500)
            for view in ('beltpacks','messages','channels','deploy','settings'):
                tm.evaluate(f"setTMView('{view}')"); tm.wait_for_timeout(900)
                if view=='beltpacks':
                    t=tm.query_selector('.etk-allbp-toggle, [onclick*="etkToggleAll"], .etk-all-toggle')
                    if t: t.click(); tm.wait_for_timeout(400)
                print(f'[{scheme}/{dev}] {view}', audit(tm, f'{scheme}-{dev}-{view}'))
            ctx.close()
    # cart: iPad, light only (it stays light)
    ctx=b.new_context(viewport={'width':820,'height':1180}, device_scale_factor=1)
    ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
    c=ctx.new_page(); c.goto('file://'+SITE+'/showcomm/etk/index.html?role=crew'); c.wait_for_timeout(1200)
    print('[cart] grid', audit(c,'cart-grid'))
    c.click('.crew-device-card:has-text("BP05")'); c.wait_for_timeout(300); print('[cart] claim', audit(c,'cart-claim'))
    c.fill('#crew-claim-name','Ann'); c.click('#btn-crew-claim-submit'); c.wait_for_timeout(900)
    c.click('#crew-cell-0'); c.wait_for_timeout(300); print('[cart] picker', audit(c,'cart-picker'))
    c.click('.crew-picker-opt:text-is("CAMS")'); c.wait_for_timeout(300); print('[cart] picked', audit(c,'cart-picked'))
    b.close()
print(f"\n=== {len(issues)} distinct text elements failing (under 12px, or contrast below 4.5:1 / 3:1 for large) ===")
print(f"{0 if issues else 1} passed, {len(issues)} failed")   # summary line for the runner
for (cls,text),hits in sorted(issues.items(), key=lambda kv:-len(kv[1])):
    fs=min(h[1] for h in hits); con=min(h[2] for h in hits)
    print(f"  {cls[:34]:34} | {text[:26]:26} | min {fs}px, min {con}:1 | {len(hits)} screens")
