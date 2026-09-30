import os
SITE=os.environ.get('SITE','/tmp/site')
from playwright.sync_api import sync_playwright
import time, os
H='http://localhost:8765'
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(); ctx.route('**/*supabase*', lambda r: r.abort())
    pg=ctx.new_page(); pg.goto(H+'/'); pg.wait_for_timeout(1500)
    ok=0
    for path in ('/showcomm/etk/crew','/showcomm/etk/tm','/showcomm/etk/crew/','/showgear','/showcomm/etk/index.html?role=crew'):
        p=ctx.new_page()
        try: p.goto(H+path); p.wait_for_timeout(500); ok+=1
        except Exception as e: print('  FAIL', path, str(e)[:60])
        p.close()
    print(f'redirects: {ok}/5 load')
    # freshness: change the page on the server, reopen, the new version must show immediately
    f=SITE+'/showcomm/etk/index.html'; orig=open(f,encoding='utf-8').read()
    p=ctx.new_page(); p.goto(H+'/showcomm/etk/index.html?role=tm'); p.wait_for_timeout(500)
    open(f,'w',encoding='utf-8').write(orig.replace('<title>','<title>FRESHCHECK ',1)); os.utime(f,(time.time()+5,time.time()+5))
    p.close(); p=ctx.new_page(); p.goto(H+'/showcomm/etk/index.html?role=tm'); p.wait_for_timeout(500)
    print('fresh copy on reopen:', 'FRESHCHECK' in p.evaluate("document.documentElement.outerHTML.slice(0,4000)"))
    open(f,'w',encoding='utf-8').write(orig)
    b.close()
