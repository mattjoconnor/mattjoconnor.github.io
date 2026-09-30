const fs=require('fs');
const DB={ profiles:[{id:'u-tm',role:'tm'},{id:'u-matt',role:'admin'}],
  push_subscriptions:[{endpoint:'tm-laptop',subscription:{e:'tm-laptop'},user_id:'u-tm'},{endpoint:'matt-phone',subscription:{e:'matt-phone'},user_id:'u-matt'}],
  device_claims:[{production_id:'ETK',device_id:'BP05',crew_name:'Priya',status:'confirmed',claimed_at:'2026-10-02T10:00:00Z'}] };
function from(t){ const st={f:[]}; const b={select(){return b;},eq(c,v){st.f.push(r=>r[c]===v);return b;},in(c,v){st.f.push(r=>v.includes(r[c]));return b;},order(){return b;},limit(){return b;},
  maybeSingle(){st.one=1;return b;}, delete(){st.del=1;return b;}, then(res){ const rows=(DB[t]||[]).filter(r=>st.f.every(f=>f(r))); return Promise.resolve({data: st.one?rows[0]||null:rows, error:null}).then(res);} }; return b; }
const sent=[];
global.createClient=()=>({from});
global.webpush={ setVapidDetails(){}, async sendNotification(sub,payload){ sent.push({to:sub.e, ...JSON.parse(payload)}); } };
const env={SUPABASE_URL:'x',SUPABASE_SERVICE_ROLE_KEY:'k',VAPID_PUBLIC_KEY:'p',VAPID_PRIVATE_KEY:'q',ETK_PUSH_SECRET:'s3cret'};
let handler; global.Deno={ env:{get:k=>env[k]}, serve:h=>{handler=h;} };
eval(fs.readFileSync(__dirname+'/out/fn.js','utf8').replace(/^export .*$/mg,''));
const req=(body,secret='s3cret')=>({ headers:{get:k=>k==='x-etk-secret'?secret:null}, json:async()=>body });
let pass=0,fail=0; const ok=(c,m)=>{console.log((c?'  PASS ':'  FAIL ')+m); c?pass++:fail++;};
(async()=>{
  let r=await handler(req({type:'INSERT',table:'messages',record:{sender_id:'u-tm',sender_role:'tm',body:'BP07 keeps dropping off CAMS'}}));
  ok(sent.length===1 && sent[0].to==='matt-phone' && sent[0].title==='ETK · TM' && sent[0].url.endsWith('#messages'),'TM message → only your phone: '+JSON.stringify(sent.map(s=>s.to+' | '+s.title+' | '+s.body)));
  sent.length=0;
  r=await handler(req({type:'INSERT',table:'messages',record:{sender_id:'u-matt',sender_role:'admin',sender_name:'Matt',body:'On my way'}}));
  ok(sent.length===1 && sent[0].to==='tm-laptop' && sent[0].title==='ETK · Matt','your reply → only the TM devices: '+JSON.stringify(sent.map(s=>s.to+' | '+s.title)));
  sent.length=0;
  r=await handler(req({type:'INSERT',table:'key_requests',record:{id:'k1',production_id:'ETK',device_id:'BP05',status:'open',note:JSON.stringify([{keyIndex:1,note:'TECH (PL)',latch:true}])}}));
  ok(sent.length===2 && sent.every(s=>s.title==='BP05 · Priya' && s.body==='Key 2 → TECH (latch)'),'key request → every device, unchanged: '+JSON.stringify(sent.map(s=>s.to+' | '+s.body)));
  sent.length=0;
  r=await handler(req({type:'INSERT',table:'messages',record:{sender_id:'u-tm',sender_role:'tm',body:'x'}},'wrong'));
  ok(r.status===401 && sent.length===0,'wrong password: refused, nothing sent');
  console.log(`\n${pass} passed, ${fail} failed`);
})();
