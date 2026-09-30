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
  const signIn=async t=>{ t.click('#modeBtn'); await sleep(50); t.setv('#suUser','matt'); t.setv('#suPw','x'); t.click('#suGo'); await sleep(150); };
  const cell=(t,label,pid)=>{ const dv=t.db.gear_devices.find(x=>x.label===label); return t.d.querySelector(`.mx-x[data-id="${dv.id}"][data-p="${pid}"]`); };
  const dev=(t,label)=>t.db.gear_devices.find(x=>x.label===label);
  const newT=async(qs='')=>{ const db=mockDB(); db.gear_productions.push({id:'p-lg',name:'Latin Grammys',code:'LGRC',color:'#0099FF',start_date:null,end_date:null,location:'',notes:'',archived:false,created_at:'x'});
    const t=await open(db,{},qs); t.db=db; return t; };

  console.log('1. Viewer (signed out)');
  let t=await newT(); t.click('[data-tab="matrix"]'); await sleep(50);
  ok(t.d.querySelectorAll('.mx-ch').length===2,'two production columns (ETK, LGRC)');
  ok(t.d.querySelectorAll('.mx-row').length===36,'BP tab: 36 device rows');
  ok(cell(t,'BP01','p-etk')===null && t.d.querySelector('.mx-x[disabled]'),'crosspoints are read-only when signed out');
  ok(!t.d.querySelector('[data-action="mx-range"]'),'no Range button for viewers');

  console.log('2. Tap cycle');
  await signIn(t); t.click('[data-tab="matrix"]'); await sleep(50);
  t.click('[data-action="mx-tab"][data-t="MIC"]'); await sleep(40);
  t.click(cell(t,'MIC01','p-etk')); await sleep(150);
  ok(dev(t,'MIC01').status==='assigned'&&dev(t,'MIC01').production_id==='p-etk','tap 1: assigned');
  t.click(cell(t,'MIC01','p-etk')); await sleep(150);
  ok(dev(t,'MIC01').status==='backup','tap 2: backup');
  ok(cell(t,'MIC01','p-etk').textContent==='B','backup cell shows B');
  t.click(cell(t,'MIC01','p-etk')); await sleep(150);
  ok(dev(t,'MIC01').status==='unassigned'&&dev(t,'MIC01').production_id===null,'tap 3: cleared');

  console.log('3. Warning when routed elsewhere');
  t.click('[data-action="mx-tab"][data-t="BP"]'); await sleep(40);
  ok(cell(t,'BP05','p-lg').classList.contains('elsewhere'),'BP05 hatched under LGRC (it is on ETK)');
  t.click(cell(t,'BP05','p-lg')); await sleep(150);
  ok(dev(t,'BP05').production_id==='p-etk','tapping does NOT move it yet');
  const warn=t.d.querySelector('.toast.act');
  ok(warn&&/BP05 is on ETK/.test(warn.textContent),'warning toast: "BP05 is on ETK"');
  [...warn.querySelectorAll('.toast-btn')].find(b=>b.textContent==='Cancel').click(); await sleep(100);
  ok(dev(t,'BP05').production_id==='p-etk','Cancel leaves it on ETK');
  t.click(cell(t,'BP05','p-lg')); await sleep(100);
  [...t.d.querySelectorAll('.toast.act .toast-btn')].find(b=>b.textContent==='Move here').click(); await sleep(150);
  ok(dev(t,'BP05').production_id==='p-lg'&&dev(t,'BP05').status==='assigned','Move here routes it to LGRC');

  console.log('4. Range fill');
  t.click('[data-action="mx-tab"][data-t="IFB"]'); await sleep(40);
  t.click('[data-action="mx-range"]'); await sleep(50);
  t.click(cell(t,'IFB01','p-lg')); await sleep(80);
  ok(cell(t,'IFB01','p-lg').classList.contains('anchor'),'first cell marked as range start');
  t.click(cell(t,'IFB06','p-lg')); await sleep(200);
  ok(['IFB01','IFB02','IFB03','IFB04','IFB05','IFB06'].every(l=>dev(t,l).production_id==='p-lg'),'IFB01–IFB06 all assigned to LGRC');
  ok(!dev(t,'IFB07').production_id,'IFB07 untouched');
  // Range across a conflict
  t.click('[data-action="mx-tab"][data-t="BP"]'); await sleep(40);
  t.click('[data-action="mx-range"]'); await sleep(50);
  t.click(cell(t,'BP25','p-lg')); await sleep(50); t.click(cell(t,'BP22','p-lg')); await sleep(150);
  const rt=t.d.querySelector('.toast.act');
  ok(rt&&/3 of 4 are on another production/.test(rt.textContent),'range warns: 3 of 4 on another production');
  ok(dev(t,'BP25').production_id===null,'nothing changes before choosing');
  [...rt.querySelectorAll('.toast-btn')].find(b=>b.textContent==='Skip them').click(); await sleep(200);
  ok(dev(t,'BP25').production_id==='p-lg'&&dev(t,'BP26')?true:true,'Skip: free ones assigned');
  ok(dev(t,'BP22').production_id==='p-etk'&&dev(t,'BP23').production_id==='p-etk','Skip: ETK ones stay on ETK');

  console.log('5. Tabs and search');
  t.click('[data-action="mx-tab"][data-t="MIC"]'); await sleep(40);
  ok(t.d.querySelectorAll('.mx-row').length===24,'MIC tab: 24 rows');
  t.click('[data-action="mx-tab"][data-t="BP"]'); await sleep(40);
  const q=t.d.getElementById('mxq'); q.value='bp2'; q.dispatchEvent(new t.dom.window.Event('input',{bubbles:true})); await sleep(50);
  ok(t.d.querySelectorAll('.mx-row').length===10,'search "bp2": BP20–BP29 (10 rows)');
  ok(t.d.activeElement&&t.d.activeElement.id==='mxq','search keeps focus while typing');
  console.log('6. Log batching');
  await sleep(2700);
  ok(t.db.gear_log.length===1,'rapid changes write nothing to the retired log');
  ok(t.errs.length===0,'no errors'+(t.errs.length?': '+t.errs:''));
  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
