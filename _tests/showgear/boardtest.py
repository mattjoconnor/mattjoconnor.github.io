import os
SITE=os.environ.get('SITE','/tmp/site')
import json
from playwright.sync_api import sync_playwright
P=lambda i,n,c,col,s,e=None,bo=None:{'id':i,'name':n,'code':c,'color':col,'start_date':s,'end_date':e,'location':'','notes':'','archived':False,'created_at':'x','board_order':bo}
prods=[P('p-bra','B/R Alert','BRA','#FEFF2F','2026-10-01','2026-11-03'),P('p-etk','ETK','ETK','#66E5E1','2026-09-01','2026-09-16'),
       P('p-bbb','B/R Big Board','BBB','#5936BB','2026-10-06','2026-12-28'),P('p-wkb','Who Knows Ball','WKB','#E757F3','2026-10-09','2026-10-15')]
devs=[]
def dev(t,n,st='unassigned',pids=()):
    devs.append({'id':f'{t}{n}','type':t,'label':f'{t}{n:02d}','model':'','serial':'','status':st,'production_ids':list(pids),'production_id':(list(pids) or [None])[0],'assignee':'','note':'','updated_at':'x'})
for i in range(1,37): dev('BP',i,'assigned' if i<=30 else 'unassigned', ['p-etk'] if i<=24 else (['p-bra','p-bbb'] if i<=30 else []))
for i in range(1,25): dev('MIC',i,'assigned' if i<=5 else 'unassigned',['p-etk'] if i<=5 else [])
for i in range(1,17): dev('IFB',i)
DB={'gear_productions':prods,'gear_devices':devs,'gear_log':[],'profiles':[{'id':'u-matt','role':'admin'}]}
mock = r"""
window.__DB=%s;
window.supabase={createClient:()=>{ const db=window.__DB; let session=null;
  function from(table){ const st={op:'select',f:[],single:false};
    const b={select(){return b;},order(){return b;},limit(){return b;},eq(c,v){st.f.push(r=>r[c]===v);return b;},in(c,v){st.f.push(r=>v.includes(r[c]));return b;},not(){return b;},
      maybeSingle(){st.single=true;return b;},upsert(r){st.op='up';st.rows=[].concat(r);return b;},insert(r){st.op='up';st.rows=[].concat(r);return b;},delete(){st.op='del';return b;},
      then(res){ const T=db[table]=db[table]||[], m=r=>st.f.every(f=>f(r)); let out;
        if(st.op==='select'){ const o=T.filter(m); out=st.single?{data:o[0]||null,error:null}:{data:JSON.parse(JSON.stringify(o)),error:null}; }
        else if(st.op==='del'){ const x=T.filter(m); db[table]=T.filter(r=>!m(r)); out={data:x.map(r=>({id:r.id})),error:null}; }
        else { for(const r of st.rows){ const row={...r}; if(!row.id) row.id='g'+Math.random(); const e=T.find(x=>x.id===row.id); e?Object.assign(e,row):T.push(row); } out={data:st.rows.map(r=>({id:r.id})),error:null}; }
        return Promise.resolve(out).then(res); } };
    return b; }
  return {from, channel(){const c={on(){return c;},subscribe(){return c;}};return c;},
    auth:{async signInWithPassword(){session={user:{id:'u-matt'}};return {data:{user:session.user},error:null};},async getSession(){return {data:{session}};},async signOut(){session=null;}}};
}};
""" % json.dumps(DB)
res=[]
def ok(c,m): res.append(c); print(('  PASS ' if c else '  FAIL ')+m)
with sync_playwright() as pw:
    b=pw.chromium.launch(); pg=b.new_page(viewport={'width':1280,'height':900})
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*supabase*', lambda r: r.abort()); pg.add_init_script(mock)
    pg.goto('file://'+SITE+'/showgear/index.html'); pg.wait_for_timeout(700)
    order=lambda: pg.eval_on_selector_all('.psec[data-pid]','els=>els.map(e=>e.dataset.pid)')
    print('1. Expand / Collapse all')
    pg.click('[data-action="expand-all"]'); pg.wait_for_timeout(150)
    ok(pg.eval_on_selector_all('.psec','els=>els.every(e=>e.classList.contains("open"))'),'Expand all opens every production and Unassigned')
    ok(pg.query_selector('[data-action="collapse-all"]') is not None,'button flips to Collapse all')
    pg.click('[data-action="collapse-all"]'); pg.wait_for_timeout(150)
    ok(pg.eval_on_selector_all('.psec','els=>els.every(e=>!e.classList.contains("open"))'),'Collapse all closes them')
    print('2. Hide empty type columns')
    pg.click('[data-action="expand-all"]'); pg.wait_for_timeout(150)
    bra=pg.query_selector('#ps-p-bra')
    ok(bra.query_selector('.tcols.n1') is not None and len(bra.query_selector_all('.tcol'))==1,'B/R Alert (beltpacks only): one full-width column, no empty Mics/IFBs boxes')
    ok('No mics or ifbs' in bra.inner_text(),'slim line: "No mics or IFBs"')
    etk=pg.query_selector('#ps-p-etk')
    ok(len(etk.query_selector_all('.tcol'))==2 and 'No ifbs' in etk.inner_text(),'ETK (BP + MIC): two columns plus "No IFBs"')
    wkb=pg.query_selector('#ps-p-wkb')
    ok('No gear assigned yet' in wkb.inner_text() and not wkb.query_selector('.tcol'),'Who Knows Ball (nothing): one "No gear assigned yet" line')
    print('3. Ended shows (today is after ETK ended Sep 16)')
    ok(etk.query_selector('.ended-badge') is not None and bra.query_selector('.ended-badge') is None,'ETK shows an Ended badge; running shows do not')
    ok(etk.query_selector('[data-action="archive-ended"]') is None,'no archive button while view-only')
    # sign in
    pg.click('#modeBtn'); pg.wait_for_timeout(100); pg.fill('#suUser','matt'); pg.fill('#suPw','x'); pg.click('#suGo'); pg.wait_for_timeout(300)
    pg.click('[data-action="expand-all"]') if pg.query_selector('[data-action="expand-all"]') else None; pg.wait_for_timeout(100)
    pg.click('#ps-p-etk [data-action="archive-ended"]'); pg.wait_for_timeout(150)
    ok('24 devices go back to unassigned' in pg.inner_text('#modal') or '29 devices' in pg.inner_text('#modal'),'confirm explains what gets freed: '+pg.inner_text('#modal .m-body').strip()[:90] if pg.query_selector('#modal .m-body') else 'confirm shown')
    pg.click('#cfmYes'); pg.wait_for_timeout(300)
    etkdb=pg.evaluate("window.__DB.gear_productions.find(p=>p.id==='p-etk')")
    freed=pg.evaluate("window.__DB.gear_devices.filter(d=>d.type==='BP'&&+d.label.slice(2)<=24).every(d=>d.status==='unassigned'&&d.production_ids.length===0)")
    ok(etkdb['archived'] and freed,'ETK archived and BP01–BP24 freed in the database')
    ok(pg.query_selector('#ps-p-etk') is None,'ETK leaves the Board')
    print('4. Drag to reorder (real mouse drag)')
    if pg.query_selector('[data-action="collapse-all"]'): pg.click('[data-action="collapse-all"]'); pg.wait_for_timeout(300)   # reorder with sections collapsed, as a person would
    before=order(); print('    before:', before)
    h=pg.query_selector('.psec[data-pid="p-wkb"] .psec-drag'); t=pg.query_selector('.psec[data-pid="p-bra"]')
    hb=h.bounding_box(); tb=t.bounding_box()
    pg.mouse.move(hb['x']+hb['width']/2, hb['y']+hb['height']/2); pg.mouse.down()
    for k in range(1,16): pg.mouse.move(hb['x']+hb['width']/2, hb['y']+hb['height']/2 + (tb['y']+10-(hb['y']+hb['height']/2))*k/15); pg.wait_for_timeout(15)
    pg.mouse.up(); pg.wait_for_timeout(300)
    after=order(); print('    after: ', after)
    ok(after[0]=='p-wkb','Who Knows Ball dragged to the top')
    saved=pg.evaluate("Object.fromEntries(window.__DB.gear_productions.filter(p=>!p.archived).map(p=>[p.code,p.board_order]))")
    ok(saved.get('WKB')==0,'new order saved to the database '+json.dumps(saved))
    # order persists after reload (carry the saved database into a fresh page), and the Matrix keeps date order
    saved_db=pg.evaluate("window.__DB")
    pg=b.new_page(viewport={'width':1280,'height':900}); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*supabase*', lambda r: r.abort()); pg.add_init_script(mock.replace(json.dumps(DB), json.dumps(saved_db)))
    pg.goto('file://'+SITE+'/showgear/index.html'); pg.wait_for_timeout(700)
    order=lambda: pg.eval_on_selector_all('.psec[data-pid]','els=>els.map(e=>e.dataset.pid)')
    ok(order()[0]=='p-wkb','order survives a reload')
    pg.click('[data-tab="matrix"]'); pg.wait_for_timeout(150)
    cols=pg.eval_on_selector_all('.mx-code','els=>els.map(e=>e.textContent)')
    ok(cols==['BRA','BBB','WKB'],'Matrix columns stay in date order '+str(cols))
    print('5. Move up / down in the production panel')
    pg.click('#modeBtn'); pg.wait_for_timeout(100); pg.fill('#suUser','matt'); pg.fill('#suPw','x'); pg.click('#suGo'); pg.wait_for_timeout(300)
    pg.click('[data-tab="board"]'); pg.wait_for_timeout(150)
    if pg.query_selector('[data-action="expand-all"]'): pg.click('[data-action="expand-all"]'); pg.wait_for_timeout(150)
    pg.click('.psec[data-pid="p-bbb"] [data-action="open-prod"]'); pg.wait_for_timeout(150)
    pg.click('#pUp'); pg.wait_for_timeout(200)
    pg.click('[data-action="close-modal"]'); pg.wait_for_timeout(200)
    ok(order()==['p-wkb','p-bbb','p-bra'],'Move up: B/R Big Board moved above B/R Alert '+str(order()))
    print('6. Archived section (edit mode) and trimmed tabs')
    ok(pg.eval_on_selector_all('[data-tab]','els=>els.map(e=>e.dataset.tab)')==['board','matrix','log'],'tabs: Board, Matrix, Log')
    ok(pg.query_selector('.psec.arch') is not None and 'ETK' in pg.eval_on_selector('.psec.arch','e=>e.textContent'),'archived ETK shows in the Archived section while editing')
    pg.click('.psec.arch .psec-hdr'); pg.wait_for_timeout(200)
    arch=pg.query_selector('.psec.arch'); arch.scroll_into_view_if_needed()
    arch.screenshot(path='/tmp/archived.png')
    ok('ETK' in pg.inner_text('.psec.arch'),'expanding Archived shows ETK with Edit and Restore')
    ok(not errs,'no page errors '+str(errs[:2]))
    pg.screenshot(path='/tmp/board-after.png', clip={'x':0,'y':0,'width':1280,'height':900})
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
