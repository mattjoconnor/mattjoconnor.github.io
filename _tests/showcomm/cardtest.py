import os
SITE=os.environ.get('SITE','/tmp/site')
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'etkflow.py')).read().split('res=[]')[0])
res=[]
def ok(c,m): res.append(bool(c)); print(('  PASS ' if c else '  FAIL ')+m)
import sys
names={1:'Zach',2:'Dante',3:'Nick (A2)',4:'A Cam',5:'B Cam',6:'C Cam',7:'D Cam',9:'Culinary 1',10:'Fonz',11:'Katy',12:'Mike Grabowski',13:'Jason Camera Dept',14:'Megan Walsh 2nd AD',15:'Nolan AC',16:'Anabelle',17:'Jason AC',18:'Culinary 2',19:'DJ Lighting',20:'Erin AD',21:'Chapman (Producer)',22:'Prompter (Producer)',23:'Abby (Producer)',24:'Kirstin (Producer)'}
STORE['device_claims']=[x for x in STORE['device_claims'] if False]
for i,n in names.items():
    STORE['device_claims'].append({'id':f'c{i}','production_id':'ETK','device_type':'beltpack','device_id':f'BP{i:02d}','crew_name':n,'crew_position':'','status':'confirmed','claimed_at':iso(now-datetime.timedelta(hours=2))})
F=SITE+'/showcomm/etk/index.html'
with sync_playwright() as pw:
    b=pw.chromium.launch()
    for (w,h,name) in ((1080,810,'iPad 10.2 sideways'),(1180,820,'iPad Air sideways'),(1133,744,'iPad mini sideways'),(810,1080,'iPad 10.2 upright'),(744,1133,'iPad mini upright')):
        ctx=b.new_context(viewport={'width':w,'height':h}); ctx.route('**/*supabase*', lambda r: r.abort()); ctx.expose_function('__dbop', dbop); ctx.add_init_script(MOCK)
        c=ctx.new_page(); c.goto('file://'+F+'?role=crew'); c.wait_for_timeout(1300)
        m=c.evaluate("""(()=>{const cards=[...document.querySelectorAll('.crew-device-card')]; const hs=[...new Set(cards.map(e=>Math.round(e.getBoundingClientRect().height)))];
          const spill=cards.filter(cd=>{ const r=cd.getBoundingClientRect(); return [...cd.querySelectorAll('*')].some(el=>{ const rg=document.createRange(); rg.selectNodeContents(el); const t=rg.getBoundingClientRect(); return t.width && (t.left<r.left-0.5||t.right>r.right+0.5); }); }).map(cd=>cd.querySelector('.crew-device-card-id').textContent);
          const cut=[...document.querySelectorAll('.crew-device-card-status')].filter(e=>e.scrollHeight>e.clientHeight+2).map(e=>e.textContent);
          const badges=[...new Set([...document.querySelectorAll('.crew-device-card-state')].map(e=>Math.round(e.getBoundingClientRect().bottom - e.closest('.crew-device-card').getBoundingClientRect().top)))];
          const last=cards[cards.length-1].getBoundingClientRect().bottom;
          return {hs, spill, cut, badges, lastBottom:Math.round(last), win:innerHeight}})()""")
        ok(len(m['hs'])==1 and len(m['badges'])==1 and not m['spill'] and not m['cut'] and m['lastBottom']<=m['win'],
           f"{name}: cards {m['hs']}, badges {m['badges']}, spilling {m['spill'] or 'none'}, cut {m['cut'] or 'none'}, grid ends {m['lastBottom']} of {m['win']}")
        ctx.close()
    b.close()

print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed")
