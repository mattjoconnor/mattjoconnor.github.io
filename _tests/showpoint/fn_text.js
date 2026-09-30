const fs=require('fs'); const webpush=require('web-push');
const src=fs.readFileSync(__dirname+'/../../_supabase/functions/etk-push/index.ts','utf8');
const start=src.indexOf('function describe'), fn=src.slice(start, src.indexOf('\n}\n', start)+3).replace('(noteJson: string): string','(noteJson)').replace('let entries: any[]','let entries');
eval(fn);
const J=(...e)=>JSON.stringify(e.map(([k,n,l])=>Object.assign({keyIndex:k,label:'Key '+(k+1),note:n}, l?{latch:true}:{})));
let pass=0,fail=0; const ok=(c,m)=>{console.log((c?'  PASS ':'  FAIL ')+m); c?pass++:fail++;};
console.log('1. Message text');
ok(describe(J([0,'CAMS (PL)',1],[1,'AUD (PL)']))==='Key 1 → CAMS (latch), Key 2 → AUD','"Key 1 → CAMS (latch), Key 2 → AUD"');
ok(describe(J([2,'CLEAR']))==='Key 3 → clear','"Key 3 → clear"');
ok(describe(J([0,'CHEF 1 (IFB)']))==='Key 1 → CHEF 1','IFB names with spaces');
ok(describe('not json')==='','bad data is ignored, not a crash');
console.log('2. Keys and encryption');
const v=webpush.generateVAPIDKeys();   // throwaway keys for this test run only
webpush.setVapidDetails('mailto:showpoint@example.com', v.publicKey, v.privateKey);
// a well-formed browser subscription (real P-256 key and auth secret) to encrypt against
const crypto=require('crypto'); const ecdh=crypto.createECDH('prime256v1'); ecdh.generateKeys();
const sub={endpoint:'https://fcm.googleapis.com/fcm/send/test-endpoint', keys:{p256dh:ecdh.getPublicKey().toString('base64url'), auth:crypto.randomBytes(16).toString('base64url')}};
const det=webpush.generateRequestDetails(sub, JSON.stringify({title:'BP05 · Priya', body:'Key 2 → TECH'}), {TTL:3600, urgency:'high'});
ok(det.method==='POST' && /^vapid t=/.test(det.headers.Authorization) && det.headers['Content-Encoding']==='aes128gcm' && det.body.length>0,'signed with your keys, payload encrypted for the phone ('+det.body.length+' bytes)');
ok(det.headers.Urgency==='high' && det.headers.TTL===3600,'marked high urgency so locked phones wake');
console.log(`\n${pass} passed, ${fail} failed`);
