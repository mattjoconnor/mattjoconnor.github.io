import re
import os
SITE=os.environ.get('SITE','/tmp/site')
from playwright.sync_api import sync_playwright
import os, time, re
H='http://localhost:8765'; F=SITE+'/showgear/index.html'; ORIG=open(F,encoding='utf-8').read()
CUR=re.search(r"const SG_BUILD='([^']+)'", ORIG).group(1); NEWB=CUR+'-t2'
def bump():
    open(F,'w',encoding='utf-8').write(ORIG.replace("const SG_BUILD='%s'"%CUR,"const SG_BUILD='%s'"%NEWB)); t=time.time()+10; os.utime(F,(t,t))
MOCK="window.supabase={createClient:()=>({from(){const b={select(){return b;},order(){return b;},limit(){return b;},eq(){return b;},in(){return b;},maybeSingle(){return b;},then(r){return Promise.resolve({data:[],error:null}).then(r);}};return b;},channel(){const c={on(){return c;},subscribe(){return c;}};return c;},auth:{getSession:async()=>({data:{session:null}})}})};"
res=[]
def ok(c,m): res.append(bool(c)); print(('  PASS ' if c else '  FAIL ')+m)
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(); ctx.route('**/*supabase*', lambda r: r.abort()); ctx.add_init_script(MOCK)
    errs=[]
    try:
        board=ctx.new_page(); board.on('pageerror', lambda e: errs.append(str(e))); board.goto(H+'/showgear/'); board.wait_for_timeout(1200)
        show=ctx.new_page(); show.on('pageerror', lambda e: errs.append(str(e))); show.goto(H+'/showgear/?prod=ETK'); show.wait_for_timeout(1200)
        board.evaluate("sgCheckUpdate(false)"); board.wait_for_timeout(400)
        ok(board.query_selector('#sgUpdate') is None,'no prompt while unchanged')
        bump(); show.evaluate("window.__m=1")
        board.evaluate("sgCheckUpdate(false)"); board.wait_for_timeout(700)
        ok(board.query_selector('#sgUpdate') is not None,'board: "Update ready · tap to reload"')
        show.evaluate("sgCheckUpdate(false)"); show.wait_for_timeout(1500)
        ok(show.evaluate("typeof window.__m")=='undefined' and show.evaluate("sgBuild()")==NEWB,'QR show page: reloads itself onto the new build')
        board.click('[data-tab="log"]'); board.wait_for_timeout(200)
        ok(('build '+CUR) in board.inner_text('.sg-build'),'build number at the bottom of the Log')
    finally:
        open(F,'w',encoding='utf-8').write(ORIG)
    ok(not errs,'no page errors '+str(errs[:2]))
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
