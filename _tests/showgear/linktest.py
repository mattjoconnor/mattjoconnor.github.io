import os
SITE=os.environ.get('SITE','/tmp/site')
import json, copy
from playwright.sync_api import sync_playwright
P=lambda i,n,c,col,s,e,sc=None:{'id':i,'name':n,'code':c,'color':col,'start_date':s,'end_date':e,'location':'FNK, Studio A','notes':'','archived':False,'created_at':'x','showcomm_production_id':sc}
prods=[P('p-etk','ETK','ETK','#66E5E1','2026-10-01','2026-10-16','ETK'),P('p-bra','B/R Alert','BRA','#FEFF2F','2026-10-01','2026-11-03')]
devs=[]
def dev(t,n,st='unassigned',pids=(),who=''):
    devs.append({'id':f'{t}{n}','type':t,'label':f'{t}{n:02d}','model':'','serial':'','status':st,'production_ids':list(pids),'production_id':(list(pids) or [None])[0],'assignee':who,'note':'','updated_at':'x'})
for i in range(1,37): dev('BP',i,'assigned' if i<=24 else ('assigned' if i<=30 else 'unassigned'),['p-etk'] if i<=24 else (['p-bra'] if i<=30 else []))
for i in range(1,25): dev('MIC',i)
for i in range(1,17): dev('IFB',i)
claims=[{'production_id':'ETK','device_type':'beltpack','device_id':'BP03','crew_name':'Zach','status':'confirmed','claimed_at':'2026-10-02T10:00:00Z'},
        {'production_id':'ETK','device_type':'beltpack','device_id':'BP07','crew_name':'Priya','status':'confirmed','claimed_at':'2026-10-02T11:00:00Z'},
        {'production_id':'ETK','device_type':'beltpack','device_id':'BP09','crew_name':'Old holder','status':'released','claimed_at':'2026-10-01T09:00:00Z'},
        {'production_id':'OTHER','device_type':'beltpack','device_id':'BP26','crew_name':'Not ours','status':'confirmed','claimed_at':'2026-10-02T09:00:00Z'}]
J=lambda *e: json.dumps([{'keyIndex':k,'label':f'Key {k+1}','note':n} for k,n in e])
reqs=[{'production_id':'ETK','device_id':'BP03','status':'fulfilled','created_at':'2026-10-01T08:00:00Z','note':J((0,'HOST (IFB)'))},   # previous holder: ignored
      {'production_id':'ETK','device_id':'BP03','status':'fulfilled','created_at':'2026-10-02T10:05:00Z','note':J((0,'CAMS (PL)'),(1,'AUD (PL)'),(2,'PROD (PL)'))},
      {'production_id':'ETK','device_id':'BP03','status':'open','created_at':'2026-10-02T12:00:00Z','note':J((1,'TECH (PL)'),(2,'CLEAR'))},
      {'production_id':'ETK','device_id':'BP07','status':'open','created_at':'2026-10-02T11:05:00Z','note':J((0,'HOST (IFB)'))},
      {'production_id':'ETK','device_id':'BP03','status':'open','created_at':'2026-10-02T12:30:00Z','note':json.dumps([{'keyIndex':0,'label':'Key 1','note':'CAMS (PL)','latch':True}])},
      {'production_id':'ETK','device_id':'BP09','status':'fulfilled','created_at':'2026-10-01T09:10:00Z','note':json.dumps([{'keyIndex':0,'label':'Key 1','note':'AUD (PL)','latch':True},{'keyIndex':1,'label':'Key 2','note':'HOST (IFB)'}])}]
opts={'PLs':[{'label':'CAMS','bg':[240,14,206],'fg':[0,0,0]},{'label':'AUD','bg':[240,14,206],'fg':[0,0,0]},{'label':'TECH','bg':[240,14,206],'fg':[0,0,0]},{'label':'PROD','bg':[240,14,206],'fg':[0,0,0]}],
      'IFBs':[{'label':'HOST','bg':[0,0,0],'fg':[169,212,152]}]}
BASE={'gear_productions':prods,'gear_devices':devs,'gear_log':[],'profiles':[{'id':'u-matt','role':'admin'}],'device_claims':claims,'key_requests':reqs,'etk_options':[{'key':'main','data':opts}]}
def mock(db, fail_sc=False):
    return r"""window.__DB=%s; window.__FAIL=%s;
window.supabase={createClient:()=>{ const db=window.__DB; let session=null;
  function from(table){ const st={op:'select',f:[],single:false,ord:null};
    const b={select(){return b;},order(c,o){st.ord=[c,o&&o.ascending!==false];return b;},limit(){return b;},eq(c,v){st.f.push(r=>r[c]===v);return b;},in(c,v){st.f.push(r=>v.includes(r[c]));return b;},not(){return b;},
      maybeSingle(){st.single=true;return b;},upsert(r){st.op='up';st.rows=[].concat(r);return b;},insert(r){st.op='up';st.rows=[].concat(r);return b;},delete(){st.op='del';return b;},
      then(res){ if(window.__FAIL && ['device_claims','key_requests','etk_options'].includes(table)) return Promise.resolve({data:null,error:{message:'down'}}).then(res);
        const T=db[table]=db[table]||[], m=r=>st.f.every(f=>f(r)); let out;
        if(st.op==='select'){ let o=T.filter(m); if(st.ord) o=o.slice().sort((a,b)=>(a[st.ord[0]]<b[st.ord[0]]?-1:1)*(st.ord[1]?1:-1)); out=st.single?{data:o[0]||null,error:null}:{data:JSON.parse(JSON.stringify(o)),error:null}; }
        else if(st.op==='del'){ const x=T.filter(m); db[table]=T.filter(r=>!m(r)); out={data:x.map(r=>({id:r.id})),error:null}; }
        else { for(const r of st.rows){ const row={...r}; const e=T.find(x=>x.id===row.id); e?Object.assign(e,row):T.push(row); } out={data:st.rows.map(r=>({id:r.id})),error:null}; }
        return Promise.resolve(out).then(res); } };
    return b; }
  return {from, channel(){const c={on(){return c;},subscribe(){return c;}};return c;},
    auth:{async signInWithPassword(){session={user:{id:'u-matt'}};return {data:{user:session.user},error:null};},async getSession(){return {data:{session}};},async signOut(){session=null;}}};
}};""" % (json.dumps(db), 'true' if fail_sc else 'false')
res=[]
def ok(c,m): res.append(bool(c)); print(('  PASS ' if c else '  FAIL ')+m)
with sync_playwright() as pw:
    b=pw.chromium.launch()
    def page(qs='', db=None, fail=False, phone=True, scheme='light'):
        pg=b.new_page(viewport={'width':390,'height':844} if phone else {'width':1280,'height':900}, device_scale_factor=2, color_scheme=scheme)
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e))); pg._errs=errs
        pg.route('**/*supabase*', lambda r: r.abort()); pg.add_init_script(mock(db or copy.deepcopy(BASE), fail))
        pg.goto('file://'+SITE+'/showgear/index.html'+qs); pg.wait_for_timeout(800); return pg
    print('1. QR show page (phone)')
    pg=page('?prod=ETK')
    rows=pg.eval_on_selector_all('.fx-sec:first-of-type .fx-row','els=>els.map(e=>e.innerText.replace(/\\s+/g," ").trim())')
    ok('BP03 Zach' in rows and 'BP07 Priya' in rows,'crew names from ShowComm appear on the show page (BP03 Zach, BP07 Priya)')
    ok(not any('Old holder' in r for r in rows),'a released claim shows no name')
    pg.click('.fx-row:has-text("BP03")'); pg.wait_for_timeout(200)
    keys=pg.eval_on_selector_all('#modal .sc-key','els=>els.map(e=>e.innerText.replace(/\\s+/g," ").trim())')
    print('    BP03 keys:', keys)
    ok(len(keys)==4,'tapping BP03 shows its 4 keys')
    ok(keys[0].startswith('1 CAMS PL'),'key 1: CAMS, confirmed (the previous holder’s HOST is ignored)')
    pend=pg.inner_text('#modal .sc-pending') if pg.query_selector('#modal .sc-pending') else ''
    ok('Key 1 → latch on' in pend,'key 1: latch-only change requested ("Key 1 → latch on")')
    ok('AUD' in keys[1] and 'Key 2 → TECH' in pend,'key 2: AUD is on the pack, TECH requested but not confirmed')
    ok('PROD' in keys[2] and 'Key 3 → clear' in pend,'key 3: PROD on the pack, a clear requested')
    ok(len(pg.query_selector_all('#modal .sc-key.has-pend'))==3,'keys 1–3 carry the amber corner marker')
    ok('Empty' in keys[3],'key 4: empty')
    ok('from ShowComm' in pg.inner_text('#modal'),'name labeled "from ShowComm"')
    ok(pg.query_selector('#dSave') is None,'read-only for QR viewers')
    pg.screenshot(path='/tmp/link-modal.png')
    pg.click('[data-action="close-modal"]'); pg.wait_for_timeout(100)
    pg.click('.fx-row:has-text("BP07")'); pg.wait_for_timeout(200)
    k7=pg.eval_on_selector_all('#modal .sc-key','els=>els.map(e=>e.innerText.replace(/\\s+/g," ").trim())')
    ok('Empty' in k7[0] and 'Key 1 → HOST' in pg.inner_text('#modal .sc-pending'),'BP07: nothing confirmed yet, HOST requested')
    pg.click('[data-action="close-modal"]'); pg.wait_for_timeout(100)
    pg.click('.fx-row:has-text("BP05")'); pg.wait_for_timeout(200)
    ok('Not claimed on the ShowComm cart' in pg.inner_text('#modal'),'unclaimed BP05: "Not claimed on the ShowComm cart right now"')
    ok(len(pg.query_selector_all('#modal .sc-key.empty'))==4,'unclaimed BP05 still shows 4 empty key boxes')
    pg.screenshot(path='/tmp/keys-unclaimed.png')
    align=pg.eval_on_selector('#modal .sc-key','e=>getComputedStyle(e).textAlign+"/"+getComputedStyle(e).alignItems')
    ok(align=='center/center','key text centered ('+align+')')
    ok(not pg._errs,'no errors '+str(pg._errs[:2]))
    pg.click('[data-action="close-modal"]'); pg.wait_for_timeout(100)
    pg.click('.fx-row:has-text("BP09"), .fx-chip:has-text("BP09")'); pg.wait_for_timeout(200)
    k9=pg.eval_on_selector_all('#modal .sc-key','els=>els.map(e=>e.innerText.replace(/\s+/g," ").trim())')
    ok('AUD' in k9[0] and 'LATCH' in k9[0].upper() and 'HOST' in k9[1] and 'Not claimed' in pg.inner_text('#modal'),'unclaimed BP09 shows what’s still on it (AUD latched, HOST) plus "Not claimed" '+str(k9[:2]))
    print('2. Only linked shows and beltpacks')
    pg=page('?prod=BRA')
    pg.click('.fx-chip:has-text("BP26")'); pg.wait_for_timeout(200)
    ok('Programmed keys' not in pg.inner_text('#modal') and 'Not claimed' not in pg.inner_text('#modal'),'B/R Alert (not linked): no ShowComm section, even with a stray claim elsewhere')
    print('3. Board and editor (desktop, signed in)')
    db=copy.deepcopy(BASE); pg=page('', db, phone=False)
    pg.click('[data-action="expand-all"]'); pg.wait_for_timeout(150)
    ok('Zach' in pg.inner_text('#ps-p-etk'),'Board ETK section shows Zach on BP03')
    pg.click('#modeBtn'); pg.wait_for_timeout(100); pg.fill('#suUser','matt'); pg.fill('#suPw','x'); pg.click('#suGo'); pg.wait_for_timeout(300)
    pg.click('[data-tab="matrix"]'); pg.wait_for_timeout(150)
    ok('Zach' in pg.inner_text('.mx-row:has-text("BP03")'),'Matrix row shows Zach')
    pg.click('.mx-dev:has-text("BP03")'); pg.wait_for_timeout(200)
    ok(pg.is_disabled('#aWho') and pg.input_value('#aWho')=='Zach','editor: Assigned to shows Zach, locked')
    pg.click('#dSave'); pg.wait_for_timeout(300)
    saved=pg.evaluate("window.__DB.gear_devices.find(d=>d.label==='BP03').assignee")
    ok(saved=='','saving never writes the ShowComm name into ShowGear (stored: '+repr(saved)+')')
    print('4. ShowComm unreachable')
    pg=page('?prod=ETK', fail=True)
    ok(pg.query_selector('.fx-title') is not None and len(pg.query_selector_all('.fx-chip'))==24,'ShowGear still loads normally (24 beltpacks), just without names')
    ok(not pg._errs,'no errors '+str(pg._errs[:2]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
