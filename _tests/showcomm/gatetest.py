import os
SITE=os.environ.get('SITE','/tmp/site')
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'etkflow.py')).read().split("res=[]")[0])
res=[]
def ok(c,m): res.append(bool(c)); print(('  PASS ' if c else '  FAIL ')+m)
H='http://localhost:8765/showcomm/etk/index.html'
with sync_playwright() as pw:
    b=pw.chromium.launch()
    def ctx(mock=True):
        c=b.new_context(viewport={'width':820,'height':1180}, has_touch=True); c.route('**/*supabase*', lambda r: r.abort())
        if mock: c.expose_function('__dbop', dbop); c.add_init_script(MOCK)
        return c
    print('1. Normal: gate, tap Crew')
    c1=ctx(); p=c1.new_page(); p.goto(H); p.wait_for_timeout(2500)
    ok(p.is_visible('.login-role-btn[data-role="crew"]') and p.query_selector('#etk-err') is None,'gate shows, no error box')
    ok('remembered role: none' in p.inner_text('#etk-gate-status'),'status line: '+p.inner_text('#etk-gate-status'))
    p.tap('.login-role-btn[data-role="crew"]'); p.wait_for_timeout(1500)
    ok('role=crew' in p.url and p.evaluate("getComputedStyle(document.getElementById('screen-crew')).display")=='flex','tap Crew → the cart')
    p.goto(H); p.wait_for_timeout(1500)
    ok(p.evaluate("getComputedStyle(document.getElementById('screen-crew')).display")=='flex','next launch with no role in the address → straight to the cart')
    print('2. Main script dies (simulated)')
    c2=ctx()
    def broken(route):
        r=route.fetch(); body=r.text()
        body=body.replace("window.__etkMainOk=true;","throw new Error('simulated startup failure'); window.__etkMainOk=true;",1)
        route.fulfill(response=r, body=body)
    c2.route('**/showcomm/etk/index.html*', broken)
    p=c2.new_page(); p.goto(H); p.wait_for_timeout(2600)
    box=p.inner_text('#etk-err') if p.query_selector('#etk-err') else ''
    ok("didn’t start" in box and 'simulated startup failure' in box,'red box: '+box[:110])
    p.tap('.login-role-btn[data-role="crew"]'); p.wait_for_timeout(800)
    ok('role=crew' in p.url and p.evaluate("localStorage.getItem('etk_mode')")=='crew','Crew still works (loads the cart address, remembers the role)')
    print('3. TM button')
    c3=ctx(); p=c3.new_page(); p.goto(H); p.wait_for_timeout(1500); p.tap('.login-role-btn[data-role="tm"]'); p.wait_for_timeout(300)
    ok(p.is_visible('#login-username'),'TM shows the sign-in form as before')
    print('4. Library can’t load')
    c4=ctx(mock=False); p=c4.new_page(); p.goto(H); p.wait_for_timeout(2600)
    st=p.inner_text('#etk-gate-status') if p.query_selector('#etk-gate-status') else ''
    ok('library: NOT loaded' in st,'status line reports it: '+st)
    b.close()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
