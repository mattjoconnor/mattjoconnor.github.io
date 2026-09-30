// The etk-push Supabase function: message text, signed/encrypted push, and who gets what.
// Runs the real function source with a stand-in database and push sender.
const fs=require('fs'), path=require('path'), ts=require('typescript'), webpush=require('web-push'), crypto=require('crypto');
const SITE=process.env.SITE||'/tmp/site';
const src=fs.readFileSync(path.join(SITE,'_supabase/etk-push/index.ts'),'utf8').split('\n').filter(l=>!l.startsWith('import ')).join('\n');
const js=ts.transpileModule(src,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.None}}).outputText.replace(/^export .*$/mg,'');
let pass=0,fail=0; const ok=(c,m)=>{console.log((c?'  PASS ':'  FAIL ')+m); c?pass++:fail++;};
// 1. keys + encryption with throwaway keys
const v=webpush.generateVAPIDKeys(); webpush.setVapidDetails('mailto:ci@example.com', v.publicKey, v.privateKey);
const ecdh=crypto.createECDH('prime256v1'); ecdh.generateKeys();
const det=webpush.generateRequestDetails({endpoint:'https://fcm.googleapis.com/fcm/send/x',keys:{p256dh:ecdh.getPublicKey().toString('base64url'),auth:crypto.randomBytes(16).toString('base64url')}},'{"title":"t"}',{TTL:3600,urgency:'high'});
ok(det.method==='POST' && /^vapid t=/.test(det.headers.Authorization) && det.headers['Content-Encoding']==='aes128gcm','push is signed and encrypted');
// 2. run the function
const DB={ profiles:[{id:'u-tm',role:'tm'},{id:'u-matt',role:'admin'}],
  push_subscriptions:[{endpoint:'tm-laptop',subscription:{e:'tm-laptop'},user_id:'u-tm'},{endpoint:'matt-phone',subscription:{e:'matt-phone'},user_id:'u-matt'}],
  device_claims:[{production_id:'ETK',device_id:'BP05',crew_name:'Priya',status:'confirmed',claimed_at:'2026-10-02T10:00:00Z'}] };
function from(t){ const st={f:[]}; const b={select(){return b;},eq(c,v){st.f.push(r=>r[c]===v);return b;},in(c,v){st.f.push(r=>v.includes(r[c]));return b;},order(){return b;},limit(){return b;},
  maybeSingle(){st.one=1;return b;}, delete(){return b;}, then(res){ const rows=(DB[t]||[]).filter(r=>st.f.every(f=>f(r))); return Promise.resolve({data: st.one?rows[0]||null:rows, error:null}).then(res);} }; return b; }
const sent=[]; const env={SUPABASE_URL:'x',SUPABASE_SERVICE_ROLE_KEY:'k',VAPID_PUBLIC_KEY:'p',VAPID_PRIVATE_KEY:'q',ETK_PUSH_SECRET:'s3cret'};
let handler;
new Function('createClient','webpush','Deno', js)(()=>({from}), {setVapidDetails(){}, async sendNotification(sub,p){ sent.push({to:sub.e,...JSON.parse(p)}); }}, {env:{get:k=>env[k]}, serve:h=>{handler=h;}});
const req=(body,secret='s3cret')=>({headers:{get:k=>k==='x-etk-secret'?secret:null}, json:async()=>body});
(async()=>{
  await handler(req({type:'INSERT',table:'key_requests',record:{id:'k1',production_id:'ETK',device_id:'BP05',status:'open',note:JSON.stringify([{keyIndex:0,note:'CAMS (PL)',latch:true},{keyIndex:2,note:'CLEAR'}])}}));
  ok(sent.length===2 && sent.every(s=>s.title==='BP05 · Priya' && s.body==='Key 1 → CAMS (latch), Key 3 → clear'),'key request → every device: '+JSON.stringify(sent.map(s=>s.to+' | '+s.body)));
  sent.length=0;
  await handler(req({type:'INSERT',table:'messages',record:{sender_id:'u-tm',sender_role:'tm',body:'BP07 dropping'}}));
  ok(sent.length===1 && sent[0].to==='matt-phone' && sent[0].title==='ETK · TM','TM message → admins only');
  sent.length=0;
  await handler(req({type:'INSERT',table:'messages',record:{sender_id:'u-matt',sender_role:'admin',sender_name:'Matt',body:'On it'}}));
  ok(sent.length===1 && sent[0].to==='tm-laptop' && sent[0].title==='ETK · Matt','Matt’s reply → TMs only');
  sent.length=0;
  const r=await handler(req({type:'INSERT',table:'messages',record:{sender_id:'u-tm',sender_role:'tm',body:'x'}},'wrong'));
  ok(r.status===401 && sent.length===0,'wrong password refused');
  console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
})();
