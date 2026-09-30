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
  const db=mockDB();
  db.gear_productions.push({id:'p-bra',name:'BRA',code:'BRA',color:'#D4A017',archived:false,created_at:'x',location:'',notes:''},
                           {id:'p-wkb',name:'WKB',code:'WKB',color:'#E0307A',archived:false,created_at:'x',location:'',notes:''});
  const t=await open(db); t.db=db; await signIn(t); t.click('[data-tab="matrix"]'); await sleep(50);
  const dev=l=>db.gear_devices.find(x=>x.label===l);
  const cell=(l,pid)=>t.d.querySelector(`.mx-x[data-id="${dev(l).id}"][data-p="${pid}"]`);
  const btn=txt=>[...t.d.querySelectorAll('.toast.act .toast-btn')].find(b=>b.textContent===txt);

  console.log('1. Share a device');
  t.click(cell('BP30','p-bra')); await sleep(150);                     // free -> BRA
  t.click(cell('BP30','p-wkb')); await sleep(100);                     // on BRA -> warning
  ok(!!btn('Share')&&!!btn('Move here'),'warning offers Share and Move here');
  btn('Share').click(); await sleep(150);
  ok(JSON.stringify(dev('BP30').production_ids)==='["p-bra","p-wkb"]','Share: BP30 on BRA and WKB');
  ok(dev('BP30').status==='assigned','status unchanged (assigned)');
  ok(cell('BP30','p-bra').classList.contains('shared')&&cell('BP30','p-wkb').classList.contains('shared'),'both crosspoints marked shared');
  ok(t.d.querySelectorAll('.mx-row .mx-dot').length>0 && [...t.d.querySelectorAll('.mx-row')].find(r=>r.textContent.includes('BP30')).querySelectorAll('.mx-dot').length===2,'row shows two production dots');

  console.log('2. Same everywhere: assignee applies to all shows');
  t.click([...t.d.querySelectorAll('.mx-dev')].find(b=>b.textContent.includes('BP30'))); await sleep(50);
  ok(t.d.querySelectorAll('#aProds .pchip.on').length===2,'editor shows BRA + WKB selected');
  t.setv('#aWho','A2'); t.click('#dSave'); await sleep(150);
  ok(dev('BP30').assignee==='A2','"A2" saved once, shared by both shows');

  console.log('3. Tap on a shared crosspoint un-shares only that show');
  t.click('[data-tab="matrix"]'); await sleep(30);
  t.click(cell('BP30','p-wkb')); await sleep(150);
  ok(JSON.stringify(dev('BP30').production_ids)==='["p-bra"]'&&dev('BP30').status==='assigned'&&dev('BP30').assignee==='A2','removed from WKB; still assigned on BRA as A2');
  t.click(cell('BP30','p-bra')); await sleep(150);
  ok(dev('BP30').status==='backup','single-show device cycles normally again (→ backup)');

  console.log('4. Move replaces');
  t.click(cell('BP01','p-wkb')); await sleep(80); btn('Move here').click(); await sleep(150);
  ok(JSON.stringify(dev('BP01').production_ids)==='["p-wkb"]','Move here: BP01 only on WKB');

  console.log('5. Range with Share');
  t.click('[data-action="mx-range"]'); await sleep(30);
  t.click(cell('BP10','p-bra')); await sleep(50); t.click(cell('BP12','p-bra')); await sleep(100);
  ok(!!btn('Share them')&&!!btn('Move them')&&!!btn('Skip them'),'range conflict offers Share / Move / Skip');
  btn('Share them').click(); await sleep(150);
  ok(['BP10','BP11','BP12'].every(l=>dev(l).production_ids.includes('p-etk')&&dev(l).production_ids.includes('p-bra')),'BP10–BP12 shared ETK + BRA');

  console.log('6. Board, archive, exports');
  t.click('[data-tab="board"]'); await sleep(50);
  ok([...t.d.querySelectorAll('.tile-shared')].some(x=>x.textContent==='+BRA'),'Board tile shows "+BRA" on ETK');
  // archive BRA: shared devices keep ETK, BRA-only devices become free
  t.click('[data-tab="board"]'); await sleep(30);
  t.click(t.d.querySelector('.psec [data-action="open-prod"][data-id="p-bra"]')); await sleep(50);
  t.d.getElementById('pArch').checked=true; t.click('#pSave'); await sleep(200);
  ok(JSON.stringify(dev('BP11').production_ids)==='["p-etk"]'&&dev('BP11').status==='assigned','archive BRA: shared BP11 stays on ETK');
  ok(dev('BP30').status==='unassigned'&&dev('BP30').production_ids.length===0,'archive BRA: BRA-only BP30 released');
  const archRow=t.d.querySelector('.arch-row');
  ok(archRow&&archRow.textContent.includes('BRA'),'BRA now listed in the Board’s Archived section');
  t.click('[data-action="restore-prod"][data-id="p-bra"]'); await sleep(200);
  ok(db.gear_productions.find(p=>p.id==='p-bra').archived===false&&!!t.d.querySelector('#ps-p-bra'),'Restore brings BRA back onto the Board');
  await sleep(2700);
  ok(db.gear_log.length===1,'sharing writes nothing to the retired log');
  ok(t.errs.length===0,'no errors'+(t.errs.length?': '+t.errs:''));
  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
