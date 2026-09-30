const {JSDOM,VirtualConsole}=require('jsdom'); const fs=require('fs');
const HTML=fs.readFileSync('index.html','utf8').replace(/<script src="https:\/\/cdn\.jsdelivr[^"]*supabase[^"]*"><\/script>/,'');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let pass=0,fail=0; const ok=(c,m)=>{ console.log((c?'  PASS ':'  FAIL ')+m); c?pass++:fail++; };

function mockDB(){
  const etk={id:'p-etk',name:'ETK',code:'ETK',color:'#FF5500',start_date:'2026-10-01',end_date:'2026-10-16',location:'',notes:'',archived:false,showcomm_production_id:'ETK',created_at:'x'};
  const dev=(type,n,st,pid)=>({id:type+n,type,label:type+String(n).padStart(2,'0'),model:'',serial:'',status:st||'unassigned',production_id:pid||null,assignee:'',note:'',updated_at:'x'});
  const devices=[]; for(let i=1;i<=36;i++) devices.push(dev('BP',i,i<=24?'assigned':'',i<=24?'p-etk':null));
  for(let i=1;i<=24;i++) devices.push(dev('MIC',i)); for(let i=1;i<=16;i++) devices.push(dev('IFB',i));
  return {gear_productions:[etk],gear_devices:devices,gear_log:[{id:'l1',ts:'2026-09-28T00:00:00Z',text:'Inventory set up'}],
    profiles:[{id:'u-matt',role:'admin'},{id:'u-tm',role:'tm'}]};
}
function mockClient(db,opts={}){
  let session=null; const users={'matt@showcomm.local':'u-matt','tm@showcomm.local':'u-tm'}; let n=0;
  const isAdmin=()=>!opts.forceDeny && session && db.profiles.some(p=>p.id===session.user.id&&p.role==='admin');
  function from(table){
    const st={op:'select',f:[],single:false};
    const b={ select(){return b;}, order(){return b;}, limit(){return b;},
      eq(c,v){st.f.push(r=>r[c]===v);return b;}, in(c,v){st.f.push(r=>v.includes(r[c]));return b;},
      not(c){st.f.push(r=>r[c]!=null);return b;}, maybeSingle(){st.single=true;return b;},
      upsert(r){st.op='upsert';st.rows=[].concat(r);return b;}, insert(r){st.op='insert';st.rows=[].concat(r);return b;},
      delete(){st.op='delete';return b;}, then(res,rej){ return Promise.resolve().then(exec).then(res,rej); } };
    function exec(){
      if(opts.loadFail&&st.op==='select'&&table!=='profiles') return {data:null,error:{message:'network down'}};
      const T=db[table], m=r=>st.f.every(f=>f(r));
      if(st.op==='select'){ const out=T.filter(m); return st.single?{data:out[0]||null,error:null}:{data:JSON.parse(JSON.stringify(out)),error:null}; }
      db.writes=(db.writes||0)+1;
      if(!isAdmin()){ return st.op==='delete'?{data:[],error:null}:{data:null,error:{message:'new row violates row-level security policy'}}; }
      if(st.op==='delete'){ const d=T.filter(m); db[table]=T.filter(r=>!m(r)); return {data:d.map(r=>({id:r.id})),error:null}; }
      for(const r of st.rows){
        const row={...r}; if(!row.id) row.id='gen'+(++n); if(table==='gear_log'&&!row.ts) row.ts=new Date().toISOString();
        if(table==='gear_devices'&&T.some(x=>x.id!==row.id&&x.label.toUpperCase()===row.label.toUpperCase())) return {data:null,error:{code:'23505',message:'duplicate label'}};
        const ex=T.find(x=>x.id===row.id); ex?Object.assign(ex,row):T.push(row);
      }
      return {data:st.rows.map(r=>({id:r.id})),error:null};
    }
    return b;
  }
  return { from, channel(){ const c={on(){return c;},subscribe(cb){cb&&cb('SUBSCRIBED');return c;}}; return c; },
    auth:{ async signInWithPassword({email}){ const id=users[email]; if(!id) return {data:null,error:{message:'bad'}}; session={user:{id}}; return {data:{user:session.user},error:null}; },
      async getSession(){ return {data:{session}}; }, async signOut(){ session=null; } } };
}
async function open(db,opts={},qs=''){
  const errs=[]; const vc=new VirtualConsole(); vc.on('jsdomError',e=>errs.push(e.message.split('\n')[0]));
  const dom=new JSDOM(HTML,{url:'https://mattjoconnor.github.io/showgear/'+qs,runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
    beforeParse(w){ const c=mockClient(db,opts); w.supabase={createClient:()=>c}; w.matchMedia=()=>({matches:false});
      w.Element.prototype.scrollTo=function(){}; }});
  await sleep(400); const d=dom.window.document;
  const click=sel=>{ const el=typeof sel==='string'?d.querySelector(sel):sel; if(!el) throw new Error('missing '+sel); el.dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true})); };
  const setv=(sel,v)=>{ const el=d.querySelector(sel); el.value=v; el.dispatchEvent(new dom.window.Event('input',{bubbles:true})); };
  const text=()=>d.getElementById('main').textContent;
  return {dom,d,click,setv,text,errs};
}

(async()=>{
  console.log('1. Anonymous QR viewer');
  let db=mockDB(); let t=await open(db);
  ok(t.text().includes('1 active production, 76 devices'),'board loads real inventory (76 devices, ETK)');
  ok(!t.d.querySelector('[data-tab="data"]'),'no Data tab (sample/erase/PIN removed)');
  ok(t.d.getElementById('modeBtn').textContent.includes('View only'),'starts view-only');
  t.click('#modeBtn'); await sleep(50);
  ok(t.d.getElementById('suUser')&&!t.d.getElementById('pin'),'Unlock asks for a real sign-in, not a PIN');
  ok(t.errs.length===0,'no errors'+(t.errs.length?': '+t.errs:''));

  console.log('2. Admin editing');
  t.setv('#suUser','matt'); t.setv('#suPw','x'); t.click('#suGo'); await sleep(150);
  ok(t.d.getElementById('modeBtn').textContent.includes('Editing'),'admin sign-in unlocks editing');
  ok(!!t.d.querySelector('[data-action="sign-out"]'),'Sign out button shown');
  // Add gear: IFB17–IFB18
  t.click('[data-action="add-devices"]'); await sleep(50);
  t.d.getElementById('gType').value='IFB'; t.d.getElementById('gType').onchange();
  t.setv('#gFrom','17'); t.setv('#gTo','18'); t.click('#gAdd'); await sleep(200);
  ok(db.gear_devices.some(x=>x.label==='IFB17')&&db.gear_devices.some(x=>x.label==='IFB18'),'Add gear writes IFB17 + IFB18 to the database');
  ok(db.gear_log.length===1,'the retired change log gets no new entries');
  // Picker: MIC01 to ETK
  t.click('[data-action="pick-gear"]'); await sleep(50);
  t.click([...t.d.querySelectorAll('.pk')].find(b=>b.textContent==='MIC01')); t.click('#pkGo'); await sleep(200);
  const m1=db.gear_devices.find(x=>x.label==='MIC01');
  ok(m1.status==='assigned'&&m1.production_id==='p-etk','picker assigns MIC01 to ETK in the database');
  // New production
  ok(JSON.stringify([...t.d.querySelectorAll('[data-tab]')].map(b=>b.dataset.tab))==='["board","matrix"]','two tabs: Board, Matrix');
  t.click('[data-tab="board"]'); await sleep(30); t.click('[data-action="new-prod"]'); await sleep(50);
  t.setv('#pName','Latin Grammys RC'); t.setv('#pCode','lgrc'); t.click('#pSave'); await sleep(200);
  const lg=db.gear_productions.find(p=>p.name==='Latin Grammys RC');
  ok(lg&&lg.code==='LGRC'&&/^[0-9a-f-]{36}$/.test(lg.id),'new production saved with a real UUID id');
  // Delete IFB18
  const ifb18=db.gear_devices.find(x=>x.label==='IFB18');
  t.click('[data-tab="matrix"]'); await sleep(30); t.click('[data-action="mx-tab"][data-t="IFB"]'); await sleep(30);
  t.click(t.d.querySelector(`.mx-dev[data-id="${ifb18.id}"]`)); await sleep(50);
  ok(!t.d.getElementById('dModel')&&!t.d.getElementById('dSerial')&&!t.d.getElementById('aNote'),'device panel: no model, serial or note fields');
  t.click('#dDel'); await sleep(50);
  t.setv('#delCode','1234'); t.click('#delGo'); await sleep(150);
  ok(db.gear_devices.some(x=>x.label==='IFB18')&&/isn’t right/.test(t.d.getElementById('delErr').textContent),'wrong code: nothing deleted, clear message');
  t.setv('#delCode','1633'); t.click('#delGo'); await sleep(200);
  ok(!db.gear_devices.some(x=>x.label==='IFB18'),'code 1633: device deleted from the database');
  // Rename to duplicate blocked
  const bp30=db.gear_devices.find(x=>x.label==='BP30');
  t.click('[data-action="mx-tab"][data-t="BP"]'); await sleep(30);
  t.click(t.d.querySelector(`.mx-dev[data-id="${bp30.id}"]`)); await sleep(50); t.setv('#dLabel','bp29'); t.click('#dSave'); await sleep(100);
  ok(t.d.getElementById('dErr').textContent.includes('already exists')&&db.gear_devices.find(x=>x.id===bp30.id).label==='BP30','duplicate label blocked');
  ok(t.errs.length===0,'no errors'+(t.errs.length?': '+t.errs:''));

  console.log('3. Database refuses a write');
  db=mockDB(); t=await open(db,{forceDeny:true});
  t.click('#modeBtn'); await sleep(50); t.setv('#suUser','matt'); t.setv('#suPw','x'); t.click('#suGo'); await sleep(150);
  // forceDeny makes role lookup still admin in UI but writes refused -> simulate by allowing UI edit
  t.dom.window.eval(''); // UI decides by profile role; writes still refused by mock
  const before=JSON.stringify(db.gear_devices);
  if(t.d.querySelector('[data-action="pick-gear"]')){
    t.click('[data-action="pick-gear"]'); await sleep(50);
    t.click([...t.d.querySelectorAll('.pk')].find(b=>b.textContent==='MIC02')); t.click('#pkGo'); await sleep(250);
    ok(JSON.stringify(db.gear_devices)===before,'refused write leaves the database untouched');
    ok([...t.d.querySelectorAll('.toast.bad')].some(x=>/Couldn’t save/.test(x.textContent)),'user told it didn’t save');
    const tile=[...t.d.querySelectorAll('.tile')].some(x=>x.textContent.includes('MIC02'));
    ok(!tile,'screen reloads to the true state (MIC02 not shown as assigned)');
  } else ok(false,'edit mode not reached');

  console.log('4. TM login (non-admin)');
  db=mockDB(); t=await open(db);
  t.click('#modeBtn'); await sleep(50); t.setv('#suUser','tm'); t.setv('#suPw','x'); t.click('#suGo'); await sleep(150);
  ok(t.d.getElementById('suErr').textContent.includes('doesn’t have edit access'),'TM can sign in but not edit');
  ok(t.d.getElementById('modeBtn').textContent.includes('View only'),'stays view-only');

  console.log('5. Load failure');
  db=mockDB(); t=await open(db,{loadFail:true});
  ok(t.text().includes('Couldn’t reach the gear database'),'shows a clear error with Try again');
  ok(!db.writes,'writes NOTHING — no sample data over the real inventory');

  console.log('6. QR deep links');
  db=mockDB(); t=await open(db,{},'?prod=etk');
  ok(t.d.querySelector('.fx-title')&&t.d.querySelector('.fx-title').textContent==='ETK'&&!t.d.querySelector('.psec'),'?prod=ETK opens ETK’s own page (no board)');
  ok(t.d.body.classList.contains('focus-mode'),'tabs and sign-in hidden on the show page');
  ok(t.d.querySelectorAll('.fx-sec').length===1&&t.d.querySelectorAll('.fx-chip').length===24,'only ETK’s gear: its 24 beltpacks, empty types skipped');
  ok(t.d.querySelector('.fx-full').getAttribute('href')==='https://mattjoconnor.github.io/showgear/','Full board link goes to the whole board');
  t.click(t.d.querySelector('.fx-chip')); await sleep(50);
  ok(!!t.d.querySelector('#overlay.show')&&!t.d.getElementById('dSave'),'tapping a device shows its details, read-only');
  db=mockDB(); t=await open(db,{},'?prod=NOPE');
  ok(/Show not found/.test(t.d.querySelector('.fx').textContent),'unknown code: clear "Show not found" message');
  db=mockDB(); db.gear_productions[0].archived=true; t=await open(db,{},'?prod=ETK');
  ok(/ETK has wrapped/.test(t.d.querySelector('.fx').textContent),'archived show: "ETK has wrapped"');

  console.log('7. Enter saves');
  db=mockDB(); t=await open(db);
  t.click('#modeBtn'); await sleep(50); t.setv('#suUser','matt'); t.setv('#suPw','x'); t.click('#suGo'); await sleep(150);
  t.click('[data-tab="matrix"]'); await sleep(30);
  t.click(t.d.querySelector('.mx-dev[data-id="BP5"]')); await sleep(50);
  t.setv('#aWho','Stage manager');
  t.d.getElementById('aWho').dispatchEvent(new t.dom.window.KeyboardEvent('keydown',{key:'Enter',bubbles:true})); await sleep(150);
  ok(db.gear_devices.find(x=>x.label==='BP05').assignee==='Stage manager'&&!t.d.querySelector('#overlay.show'),'device editor: Enter saves and closes');
  t.click('[data-tab="board"]'); await sleep(30);
  t.click(t.d.querySelector('.psec [data-action="open-prod"][data-id="p-etk"]')); await sleep(50);
  t.setv('#pLoc','Studio A');
  t.d.getElementById('pLoc').dispatchEvent(new t.dom.window.KeyboardEvent('keydown',{key:'Enter',bubbles:true})); await sleep(150);
  ok(db.gear_productions[0].location==='Studio A','production editor: Enter saves');
  db=mockDB(); t=await open(db,{},'?type=MIC');
  ok(t.d.querySelectorAll('.mx-row').length===24&&t.d.querySelector('.mx-tab.on').dataset.t==='MIC','?type=MIC opens the Matrix on the MIC tab');
  ok(t.errs.length===0,'no errors'+(t.errs.length?': '+t.errs:''));

  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
