const jsQR=require('jsqr');
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
// decode an on-screen QR (SVG path) with an independent reader
function decodeSvg(svg){
  const vb=+/viewBox="0 0 (\d+)/.exec(svg)[1], S=8, W=vb*S, px=new Uint8ClampedArray(W*W*4).fill(255);
  const re=/M(\d+) (\d+)h1v1h-1z/g; let m;
  while((m=re.exec(svg))){ const x=+m[1], y=+m[2]; for(let dy=0;dy<S;dy++) for(let dx=0;dx<S;dx++){ const i=((y*S+dy)*W+(x*S+dx))*4; px[i]=px[i+1]=px[i+2]=0; } }
  const r=jsQR(px,W,W); return r&&r.data;
}
// decode a QR drawn into the PDF (vector squares) the same way
function decodePdfRects(rects){
  const bg=rects.find(r=>r.fill==='255,255,255'&&r.w>40&&Math.abs(r.w-r.h)<0.5); if(!bg) return null;
  const S=4, W=Math.ceil(bg.w*S), px=new Uint8ClampedArray(W*W*4).fill(255);
  rects.filter(r=>r.fill==='0,0,0'&&r.x>=bg.x-0.1&&r.y>=bg.y-0.1&&r.x<bg.x+bg.w&&r.y<bg.y+bg.h).forEach(r=>{
    for(let y=Math.round((r.y-bg.y)*S);y<Math.round((r.y-bg.y+r.h)*S);y++) for(let x=Math.round((r.x-bg.x)*S);x<Math.round((r.x-bg.x+r.w)*S);x++){ if(x<W&&y<W){ const i=(y*W+x)*4; px[i]=px[i+1]=px[i+2]=0; } } });
  const res=jsQR(px,W,W); return res&&res.data;
}
(async()=>{
  const db=mockDB();
  // BP25–BP30 shared by BRA, BBB, WKB (like the real data), MIC01 assigned with a name
  db.gear_devices.forEach(d=>{ const n=+d.label.slice(2); if(d.type==='BP'&&n>=25&&n<=30){ d.status='assigned'; d.production_ids=['p-bra','p-bbb','p-wkb']; d.production_id='p-bra'; } });
  const t=await open(db);
  // extend the fake PDF to record rectangles with their fill colour
  const patch=()=>{ const J=t.dom.window.jspdf; if(!J||J.__p) return; const P=J.jsPDF.prototype; let fill='0,0,0';
    P.setFillColor=function(...c){ fill=c.join(','); }; P.rect=function(x,y,w,h,st){ (t.rec.rects=t.rec.rects||[]).push({x,y,w,h,st,fill,page:this.pages}); }; J.__p=true; };

  console.log('1. On-screen QR codes');
  t.click(t.d.querySelector('[data-action="show-qr"][data-id="p-etk"]')); await sleep(60);
  const svg=t.d.querySelector('.qr-svg').outerHTML;
  const got=decodeSvg(svg);
  ok(got==='https://mattjoconnor.github.io/showgear/?prod=ETK','ETK QR scans to …/showgear/?prod=ETK ('+got+')');
  ok(t.d.querySelector('.qr-url').textContent===got,'link printed under the code matches');
  t.click('[data-action="close-modal"]'); await sleep(30);
  // a brand-new production gets its QR with no extra steps
  db.gear_productions.push(P('p-new','Latin Grammys RC','LGRC','#D8282E','2026-11-13'));
  t.click('[data-tab="matrix"]'); await sleep(20); t.click('[data-tab="board"]'); await sleep(30);
  const t2=await open(db); t2.click(t2.d.querySelector('[data-action="show-qr"][data-id="p-new"]')); await sleep(60);
  ok(decodeSvg(t2.d.querySelector('.qr-svg').outerHTML)==='https://mattjoconnor.github.io/showgear/?prod=LGRC','new production (LGRC) gets a working QR automatically');

  console.log('2. QR sheet PDF');
  // warm-up export so the stand-in PDF library exists, then attach the recorder before the QR sheet
  t.click('[data-action="export"]'); await sleep(40); t.click('.xp[data-x="summary"]'); await sleep(300); patch();
  t.rec.tables.length=0; t.rec.texts.length=0; t.rec.rects=[];
  t.click('[data-action="export"]'); await sleep(50);
  ok(!!t.d.querySelector('.xp[data-x="qr"]')&&t.d.querySelectorAll('.xp-prod').length===5,'Export menu: QR codes entry + a row per production');
  ok([...t.d.querySelectorAll('.xp-prod')][0].querySelectorAll('.xp-b').length===3,'each production row: Sheet, Checklist, QR');
  t.click('.xp[data-x="qr"]'); await sleep(300);
  const p1=(t.rec.rects||[]).filter(r=>r.page===1);
  ok(decodePdfRects(p1)==='https://mattjoconnor.github.io/showgear/','page 1: printed board QR scans to the board');
  const cardsQr=(t.rec.rects||[]).filter(r=>r.page===2);
  ok(t.rec.texts.some(x=>x.t==='Productions')&&cardsQr.length>100,'page 2: production cards with QR codes');
  ok(t.rec.texts.filter(x=>/showgear\/\?prod=/.test(x.t)).length>=5,'every production card prints its link');

  console.log('3. Production sheet and checklist');
  t.rec.tables.length=0; t.rec.texts.length=0; t.rec.rects=[];
  t.click('[data-action="export"]'); await sleep(40); t.click('.xp-b[data-x="prod"][data-id="p-etk"]'); await sleep(300);
  ok(!t.rec.texts.some(x=>/assigned, \d+ backup  /.test(x.t)||/^Beltpacks: /.test(x.t)),'sheet: duplicate count line removed');
  ok(t.rec.texts.some(x=>x.t==='Scan for the live gear list'),'sheet: QR in the header corner, labeled for the show’s gear list');
  ok(decodePdfRects(t.rec.rects)==='https://mattjoconnor.github.io/showgear/?prod=ETK','sheet: header QR scans to ETK');
  t.rec.tables.length=0; t.rec.texts.length=0;
  t.click('[data-action="export"]'); await sleep(40); t.click('.xp-b[data-x="check"][data-id="p-etk"]'); await sleep(300);
  const [cl,cr]=t.rec.tables;
  ok(cl&&JSON.stringify(cl.head[0])==='["Device","Assigned to","Out","In"]','checklist: only Device / Assigned to / Out / In');
  ok(cl.body.length===12&&cr.body.length===12&&cl.body[0][0]==='BP01'&&cr.body[0][0]==='BP13','checklist: two side-by-side columns (BP01–BP12 | BP13–BP24)');
  ok(cl.startY===cr.startY,'both columns start at the same height');
  ok(!t.rec.texts.some(x=>/Checked out by|Returned by|Initials/.test(x.t)),'checklist: no sign-off lines or initials');

  console.log('4. Summary PDF');
  t.rec.tables.length=0; t.rec.texts.length=0;
  t.click('[data-action="export"]'); await sleep(40); t.click('.xp[data-x="summary"]'); await sleep(300);
  const prodT=t.rec.tables.find(x=>x.head[0][1]==='Production'), sharedT=t.rec.tables.find(x=>x.head[0][0]==='Devices');
  const bra=prodT.body.find(r=>r[1]==='BRA');
  ok(bra[4]==='6\n(6 shared)','production counts show shared: "6 (6 shared)"');
  ok(bra[5]==='–'&&bra[3]==='–','empty counts and location show a dash');
  ok(sharedT&&sharedT.body[0][0]==='BP25–BP30'&&sharedT.body[0][1]==='BRA + BBB + WKB','Shared gear section: "BP25–BP30  BRA + BBB + WKB"');
  const unT=t.rec.tables.find(x=>x.head[0][1]==='Devices'&&x.head[0][0]==='Type');
  ok(/^MIC01–MIC24$/.test(unT.body[1][1]),'unassigned list uses ranges (MIC01–MIC24)');
  ok(t.errs.length===0&&t2.errs.length===0,'no errors'+([...t.errs,...t2.errs].length?': '+[...t.errs,...t2.errs].join(' | '):''));
  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
