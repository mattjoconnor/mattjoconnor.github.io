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

import sys, os
AUDIT=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','showcomm','audit.js')).read()
TAG=sys.argv[1] if len(sys.argv)>1 else 'sg'
os.makedirs(f'/tmp/ui/{TAG}', exist_ok=True)
issues={}
def audit(pg, state):
    rows=pg.evaluate(AUDIT)
    bad=[r for r in rows if (r['fs']<12 or (not r['imgBg'] and r['contrast']<r['need']))]
    for r in bad:
        k=(r['cls'] or '(no class)', r['text'][:28]); issues.setdefault(k, []).append((state, r['fs'], r['contrast']))
    pg.screenshot(path=f'/tmp/ui/{TAG}/{state}.png')
    print(f'  {state:28} {len(rows):4} text elements, {len(bad):3} failing')

res=[]
def ok(c,m): res.append(bool(c)); print(('  PASS ' if c else '  FAIL ')+m)
with sync_playwright() as pw:
    b=pw.chromium.launch(); errs=[]
    def page(ctx, qs=''):
        pg=ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.goto('file://'+SITE+'/showgear/index.html'+qs); pg.wait_for_timeout(900); return pg
    for scheme in ('light','dark'):
        ctx=b.new_context(viewport={'width':390,'height':844}, color_scheme=scheme, device_scale_factor=2); ctx.route('**/*supabase*', lambda r: r.abort()); ctx.add_init_script(mock(copy.deepcopy(BASE)))
        pg=page(ctx)
        if scheme=='light':
            print('Phone header and bottom bar')
            ok(pg.eval_on_selector('.ribbon','e=>Math.round(e.getBoundingClientRect().height)')<=58,'header is one row')
            nav=pg.eval_on_selector('#nav','e=>{const r=e.getBoundingClientRect();return [Math.round(r.bottom),getComputedStyle(e).position]}')
            ok(nav==[844,'fixed'],'tab bar pinned to the bottom')
            lab=pg.eval_on_selector_all('#nav .rt-label','els=>els.map(e=>Math.round(e.getBoundingClientRect().bottom))')
            ok(all(l<=844 for l in lab) and pg.is_visible('#nav .rt-label'),'labels fully on screen '+str(lab))
            vis=pg.eval_on_selector_all('#nav .ribbon-tab','els=>els.map(e=>{const r=e.getBoundingClientRect();return [e.dataset.tab,Math.round(r.right)]})')
            ok([v[0] for v in vis]==['board','matrix'] and all(v[1]<=390 for v in vis),'Board and Matrix on screen')
            ok(pg.is_visible('#modeBtn .mb-ico') and not pg.is_visible('#modeBtn .mb-txt'),'View only shows as a lock icon')
            ok(pg.get_attribute('#modeBtn','aria-label').startswith('View only'),'lock still announces "View only"')
            ok(pg.is_visible('.sg-live-dot') and not pg.is_visible('.sg-live-txt'),'Live shows as a dot')
            ok(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),'nothing spills sideways')
            pg.screenshot(path='/tmp/ui/sg-phone-view.png')
            pg.click('#modeBtn'); pg.wait_for_timeout(100); pg.fill('#suUser','matt'); pg.fill('#suPw','x'); pg.click('#suGo'); pg.wait_for_timeout(500)
            ok(pg.is_visible('#modeBtn .mb-ico') and 'editing' in pg.get_attribute('#modeBtn','class'),'editing: open-lock icon')
            ok(not pg.is_visible('.sg-signout-head'),'Sign out out of the header')
            pg.screenshot(path='/tmp/ui/sg-phone-edit.png')
            pg.click('#nav .ribbon-tab[data-tab="matrix"]'); pg.wait_for_timeout(400)
            ok('view-enter' in (pg.get_attribute('#main','class') or ''),'(tab switch)')
            pg.click('#nav .ribbon-tab[data-tab="board"]'); pg.wait_for_timeout(400)
            ok(pg.query_selector('.sg-signout-phone') is not None,'Sign out at the bottom of the Board')
            ok('view-enter' in (pg.get_attribute('#main','class') or ''),'switching tabs fades the view in')
            pg.evaluate("document.getElementById('main').classList.remove('view-enter')"); pg.wait_for_timeout(100)
            pg.evaluate("window.dispatchEvent(new Event('resize'))")
            ok('view-enter' not in (pg.get_attribute('#main','class') or ''),'no fade on redraws that aren’t tab switches')
            lb=pg.eval_on_selector('.sg-build','e=>Math.round(e.getBoundingClientRect().bottom)'); pg.evaluate("document.getElementById('main').scrollTop=99999"); pg.wait_for_timeout(200)
            sb=pg.eval_on_selector('.sg-signout-phone','e=>Math.round(e.getBoundingClientRect().bottom)'); bt=pg.eval_on_selector('#nav','e=>Math.round(e.getBoundingClientRect().top)')
            ok(sb<=bt,'scrolled to the end, Sign out clears the bar (%d ≤ %d)'%(sb,bt))
            print('Offline banner')
            ctx.set_offline(True); pg.wait_for_timeout(500)
            ok(pg.is_visible('#sg-conn-banner') and 'board may be out of date' in pg.inner_text('#sg-conn-banner'),'offline: red banner')
            ok('offline' in pg.get_attribute('.sg-live-dot','class'),'Live dot turns red')
            ctx.set_offline(False); pg.wait_for_timeout(300)
            print('QR show page')
            sp=page(ctx,'?prod=ETK')
            ok(not sp.is_visible('#nav'),'no tab bar on show pages')
        else:
            pg.screenshot(path='/tmp/ui/sg-phone-dark.png')
        ctx.close()
    print('Laptop')
    ctx=b.new_context(viewport={'width':1280,'height':900}); ctx.route('**/*supabase*', lambda r: r.abort()); ctx.add_init_script(mock(copy.deepcopy(BASE)))
    lp=page(ctx)
    ok(lp.eval_on_selector('#nav','e=>getComputedStyle(e).position')!='fixed' and not lp.is_visible('.rt-ico'),'tabs in the header, text only')
    ok(lp.is_visible('.sg-live-txt') and lp.is_visible('#modeBtn .mb-txt'),'Live and View only as words')
    lp.screenshot(path='/tmp/ui/sg-laptop.png')
    ok(not errs,'no page errors '+str(errs[:2]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
