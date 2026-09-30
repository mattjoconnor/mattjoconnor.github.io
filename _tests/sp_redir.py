from playwright.sync_api import sync_playwright
import sys
H='http://localhost:8765'
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context()
    ctx.route('**/*supabase*', lambda r: r.abort())
    pg=ctx.new_page(); pg.goto(H+'/'); pg.wait_for_timeout(1500)   # install the site-wide worker
    for path in ('/showcomm/etk/crew','/showcomm/etk/tm','/showcomm/etk/crew/','/showgear','/showcomm/etk/index.html?role=crew'):
        p=ctx.new_page()
        try:
            p.goto(H+path, wait_until='load'); p.wait_for_timeout(700)
            print(f"{path:38} OK   -> {p.url.replace(H,'')}")
        except Exception as e:
            print(f"{path:38} FAIL -> {str(e).splitlines()[0][:70]}")
        p.close()
    b.close()
