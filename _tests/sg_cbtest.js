const {JSDOM,VirtualConsole}=require('jsdom'); const fs=require('fs');
const HTML=fs.readFileSync('index.html','utf8').replace(/<script src="https:\/\/cdn\.jsdelivr[^"]*supabase[^"]*"><\/script>/,'');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let pass=0,fail=0; const ok=(c,m)=>{ console.log((c?'  PASS ':'  FAIL ')+m); c?pass++:fail++; };
const P=(id,name,code,color,start)=>({id,name,code,color,start_date:start,end_date:null,location:'',notes:'',archived:false,created_at:'x'});
function mockDB(){
  const prods=[P('p-bra','BRA','BRA','#FEFF2F','2026-09-01'),P('p-etk','ETK','ETK','#66E5E1','2026-10-01'),P('p-bbb','BBB','BBB','#5936BB','2026-10-05'),
               P('p-wkb','WKB','WKB','#E757F3','2026-10-10'),P('p-p5','Show 5','P5','#55D691','2026-10-20')];
  const dev=(type,n,st,pids)=>({id:type+n,type,label:type+String(n).padStart(2,'0'),model:'',serial:'',status:st||'unassigned',production_ids:pids||[],production_id:(pids||[])[0]||null,assignee:'',note:'',updated_at:'x'});
  const d=[]; for(let i=1;i<=36;i++) d.push(dev('BP',i,i<=24?'assigned':'',i<=24?['p-etk']:[]));
  for(let i=1;i<=24;i++) d.push(dev('MIC',i)); for(let i=1;i<=16;i++) d.push(dev('IFB',i));
  return {gear_productions:prods,gear_devices:d,gear_log:[],profiles:[{id:'u-matt',role:'admin'}]};
}
function client(db){
  let session=null;
  function from(table){
    const st={op:'select',f:[],single:false};
    const b={select(){return b;},order(){return b;},limit(){return b;},eq(c,v){st.f.push(r=>r[c]===v);return b;},in(c,v){st.f.push(r=>v.includes(r[c]));return b;},
      not(c){st.f.push(r=>r[c]!=null);return b;},maybeSingle(){st.single=true;return b;},upsert(r){st.op='up';st.rows=[].concat(r);return b;},insert(r){st.op='up';st.rows=[].concat(r);return b;},
      delete(){st.op='del';return b;},then(res,rej){return Promise.resolve().then(exec).then(res,rej);}};
    function exec(){ const T=db[table], m=r=>st.f.every(f=>f(r));
      if(st.op==='select'){ const o=T.filter(m); return st.single?{data:o[0]||null,error:null}:{data:JSON.parse(JSON.stringify(o)),error:null}; }
      if(st.op==='del'){ const x=T.filter(m); db[table]=T.filter(r=>!m(r)); return {data:x.map(r=>({id:r.id})),error:null}; }
      for(const r of st.rows){ const row={...r}; if(!row.id) row.id='g'+Math.random(); const e=T.find(x=>x.id===row.id); e?Object.assign(e,row):T.push(row); }
      return {data:st.rows.map(r=>({id:r.id})),error:null}; }
    return b; }
  return {from, channel(){const c={on(){return c;},subscribe(cb){cb&&cb('SUBSCRIBED');return c;}};return c;},
    auth:{async signInWithPassword(){session={user:{id:'u-matt'}};return {data:{user:session.user},error:null};},async getSession(){return {data:{session}};},async signOut(){session=null;}}};
}
// Stand-in PDF library that records what the export draws
function fakePdf(w, rec){
  class Doc{ constructor(){ this.pages=1; this.internal={pageSize:{getWidth:()=>612,getHeight:()=>792},getNumberOfPages:()=>this.pages}; }
    setFont(){} setFontSize(){} setTextColor(){} setFillColor(){} setDrawColor(){} setLineWidth(){} setCharSpace(){} rect(){} line(){} setPage(){}
    text(t,x,y){ rec.texts.push({t:String(t),y}); } splitTextToSize(t){return [t];}
    addPage(){ this.pages++; rec.addPages++; }
    autoTable(o){ rec.tables.push({head:o.head,body:o.body,startY:o.startY,page:this.pages}); const rows=(o.body||[]).length+1; this.lastAutoTable={finalY:o.startY+rows*20}; }
    output(){ return new w.Blob(['pdf']); } }
  w.jspdf={jsPDF:Doc};
}
async function open(db, qs=''){
  const errs=[]; const vc=new VirtualConsole(); vc.on('jsdomError',e=>errs.push(e.message.split('\n')[0]));
  const rec={tables:[],texts:[],addPages:0};
  const dom=new JSDOM(HTML,{url:'https://mattjoconnor.github.io/showgear/'+qs,runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
    beforeParse(w){ const c=client(db); w.supabase={createClient:()=>c}; w.matchMedia=()=>({matches:false}); w.Element.prototype.scrollTo=function(){};
      w.URL.createObjectURL=()=>'blob:x'; w.URL.revokeObjectURL=()=>{}; w.HTMLAnchorElement.prototype.click=function(){};
      const orig=w.HTMLHeadElement.prototype.appendChild;
      w.HTMLHeadElement.prototype.appendChild=function(el){ if(el.tagName==='SCRIPT'&&/jspdf|autotable/i.test(el.src||'')){ fakePdf(w,rec); setTimeout(()=>el.onload&&el.onload(),0); return el; } return orig.call(this,el); }; }});
  await sleep(400); const d=dom.window.document;
  const click=sel=>{ const el=typeof sel==='string'?d.querySelector(sel):sel; if(!el) throw new Error('missing '+sel); el.dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true})); };
  const setv=(sel,v)=>{ const el=d.querySelector(sel); el.value=v; el.dispatchEvent(new dom.window.Event('input',{bubbles:true})); };
  return {dom,d,click,setv,errs,rec,db};
}
(async()=>{
  const db=mockDB(); const t=await open(db);
  const signIn=async()=>{ t.click('#modeBtn'); await sleep(50); t.setv('#suUser','matt'); t.setv('#suPw','x'); t.click('#suGo'); await sleep(150); };
  const dev=l=>db.gear_devices.find(x=>x.label===l);
  const cell=(l,pid)=>t.d.querySelector(`.mx-x[data-id="${dev(l).id}"][data-p="${pid}"]`);
  const btn=txt=>[...t.d.querySelectorAll('.toast.act .toast-btn')].find(b=>b.textContent===txt);
  const share=async(l,pid)=>{ t.click(cell(l,pid)); await sleep(80); btn('Share').click(); await sleep(120); };

  console.log('1. Matrix tabs and controls');
  await signIn(); t.click('[data-tab="matrix"]'); await sleep(50);
  const tabs=[...t.d.querySelectorAll('.mx-tab')].map(b=>b.textContent);
  ok(JSON.stringify(tabs)==='["BP36","MIC24","IFB16"]','three type tabs with counts: BP 36, MIC 24, IFB 16');
  ok(t.d.querySelectorAll('.mx-row').length===36,'BP tab shows only the 36 beltpacks');
  ok(!t.d.querySelector('[data-action="mx-prod"]')&&!t.d.querySelector('.mx-grp'),'production toggles and group headers are gone');
  ok(t.d.querySelectorAll('.mx-ch').length===5,'all 5 productions shown as columns');
  t.click('[data-action="mx-tab"][data-t="MIC"]'); await sleep(40);
  ok(t.d.querySelectorAll('.mx-row').length===24&&t.d.querySelector('.mx-corner').textContent==='Mics','MIC tab: 24 rows');
  t.click('[data-action="mx-tab"][data-t="BP"]'); await sleep(40);

  console.log('2. Split cells in column order');
  t.click(cell('BP30','p-bra')); await sleep(120);                 // free -> BRA
  await share('BP30','p-wkb');
  let sp=cell('BP30','p-wkb').querySelector('.mx-split');
  ok(sp&&sp.children.length===2,'shared by 2: halves');
  ok(sp.children[0].style.background.includes('254, 255, 47')&&sp.children[1].style.background.includes('231, 87, 243'),'halves in column order: BRA yellow, then WKB magenta');
  ok(cell('BP30','p-bra').innerHTML===cell('BP30','p-wkb').innerHTML,'identical split in both columns');
  await share('BP30','p-bbb');
  ok(cell('BP30','p-bra').querySelector('.mx-split').children.length===3,'shared by 3: thirds');
  await share('BP30','p-etk');
  sp=cell('BP30','p-etk').querySelector('.mx-split');
  ok(sp.classList.contains('q')&&sp.children.length===4,'shared by 4: quadrants');

  console.log('3. Limit of 4 shows');
  t.click(cell('BP30','p-p5')); await sleep(80);
  ok(!btn('Share')&&!!btn('Move here'),'5th show: Share not offered, only Move');
  ok(/limit of 4 shows/.test(t.d.querySelector('.toast.act').textContent),'toast explains the limit');
  btn('Cancel').click(); await sleep(50);
  t.click([...t.d.querySelectorAll('.mx-dev')].find(b=>b.textContent.includes('BP30'))); await sleep(60);
  t.click(t.d.querySelector('#aProds .pchip[data-id="p-p5"]')); await sleep(30);
  ok(!t.d.querySelector('#aProds .pchip[data-id="p-p5"]').classList.contains('on'),'device editor blocks a 5th production');
  t.click('[data-action="close-modal"]'); await sleep(30);
  ok(dev('BP30').production_ids.length===4,'still on exactly 4 shows');

  console.log('4. Shared backup');
  await share('BP01','p-wkb');                                       // BP01 on ETK + WKB
  t.click([...t.d.querySelectorAll('.mx-dev')].find(b=>b.textContent.includes('BP01'))); await sleep(60);
  t.click('#seg [data-v="backup"]'); t.click('#dSave'); await sleep(150);
  t.click('[data-tab="matrix"]'); await sleep(40);
  const bc=cell('BP01','p-etk');
  ok(bc.querySelector('.mx-split.tint')&&bc.querySelector('.mx-bk').textContent==='B','shared backup: lighter split with B');

  console.log('5. Board tiles, colors, status, chips');
  t.click('[data-tab="board"]'); await sleep(50);
  const strip=t.d.querySelector('.tile.is-shared .tile-strip.split');
  ok(strip&&strip.children.length>=2,'shared tile gets a split color strip');
  const fg=t.dom.window.eval ? null : null;
  const html=t.d.documentElement.outerHTML;
  ok(/--pfg:#111111/.test(html),'light production colors get dark text (--pfg)');
  const css=[...t.d.querySelectorAll('style')].map(x=>x.textContent).join('');
  ok(/\.chip\.BP,\.chip\.IFB,\.chip\.MIC\{color:#FFFFFF;\}/.test(css),'type chips are one neutral style');
  ok(/\.status\.backup::before\{content:'B'/.test(css)&&/\.status\.unassigned::before\{background:none;border/.test(css),'status shapes: boxed B for backup, hollow ring for free');
  ok(/PALETTE = \['#FEFF2F','#66E5E1','#55D691','#E757F3','#D8282E','#5936BB','#FFFFFF','#8A8A8A'\]/.test(html),'Color bars palette in place');

  console.log('6. PDF');
  t.click(t.d.querySelector('[data-action="export-prod"][data-id="p-etk"]')); await sleep(250);
  const tabs1=t.rec.tables;
  ok(tabs1.length>=1&&tabs1[0].head[0][0].content==='Assigned'&&tabs1[0].body[0].length===8,'no names or notes yet: compact 8-across grid, not empty columns');
  ok(tabs1.flatMap(x=>x.body.flat()).some(c=>/^BP30  \+BRA BBB WKB$/.test(c)),'shared devices marked, e.g. "BP30 +BRA BBB WKB"');
  // Named devices print Device / Assigned to in two columns; a section that won't fit moves to the next page whole
  const db2=mockDB();
  db2.gear_devices.forEach(x=>{ x.status='assigned'; x.production_ids=['p-etk']; x.production_id='p-etk'; x.assignee='Crew '+x.label; x.note='Checked'; });
  const t2=await open(db2);
  t2.click(t2.d.querySelector('[data-action="export-prod"][data-id="p-etk"]')); await sleep(250);
  const [bl,br]=t2.rec.tables;
  ok(bl&&JSON.stringify(bl.head[0])==='["Device","Assigned to"]'&&bl.body.length===18&&br.body.length===18,'named beltpacks: Device / Assigned to, 36 split 18 | 18, no Note column');
  const mic=t2.rec.tables.find(x=>x.body[0]&&/^MIC/.test(x.body[0][0]));
  ok(t2.rec.addPages>=1&&mic&&mic.page===2,'Mics section starts on a new page instead of splitting');
  const micTitle=t2.rec.texts.find(x=>x.t==='Mics');
  ok(micTitle&&micTitle.y===50,'its heading moves with it (no orphaned title)');
  ok(t2.errs.length===0,'no errors (second export)'+(t2.errs.length?': '+t2.errs:''));
  ok(t.errs.length===0,'no errors'+(t.errs.length?': '+t.errs.join(' | '):''));
  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
