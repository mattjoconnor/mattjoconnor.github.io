const {JSDOM,VirtualConsole}=require('jsdom'); const fs=require('fs');
const html=fs.readFileSync('index.html','utf8').replace(/<script src="https:\/\/cdn\.jsdelivr[^"]*"><\/script>/,'');
const errs=[]; const vc=new VirtualConsole(); vc.on('jsdomError',e=>errs.push(e.message.split('\n')[0]));
const dom=new JSDOM(html,{url:'https://x/etk/index.html?role=crew',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
  beforeParse(w){ w.supabase={createClient:()=>null}; w.matchMedia=()=>({matches:false,addListener(){},removeListener(){}}); }});
setTimeout(()=>{
  const E=c=>dom.window.eval(c), ok=(c,m)=>{console.log((c?'PASS ':'FAIL ')+m); if(!c) process.exitCode=1;};
  // Scenario A: CAMS already programmed on Key 3; crew opens Key 1
  E(`_crewAllKeys=[null,null,null,null]; _crewKeyNotes={}; _crewCurrentKeyState={2:{category:'PLs',label:'CAMS'}}; _crewPickerForceOpen={};`);
  const pick=E(`crewOptionPickerHTML(0)`);
  const d=new JSDOM(pick).window.document;
  const cams=[...d.querySelectorAll('.crew-picker-opt')].find(b=>b.textContent.startsWith('CAMS'));
  ok(cams&&cams.classList.contains('taken'),'CAMS grayed out on Key 1 picker');
  ok(cams&&cams.textContent.includes('On Key 3'),'CAMS labeled "On Key 3"');
  ok(cams&&cams.getAttribute('onclick').startsWith('crewPromptMove'),'tapping CAMS opens move prompt, not a pick');
  const tech=[...d.querySelectorAll('.crew-picker-opt')].find(b=>b.textContent==='TECH');
  ok(tech&&!tech.classList.contains('taken'),'untaken options stay normal');
  E(`crewMoveOption(0,'PLs','CAMS',2)`);
  ok(E(`JSON.stringify(_crewKeyNotes)`)==='{"0":{"category":"PLs","label":"CAMS","latch":false},"2":{"clear":true}}','programmed move → Key 1 CAMS + Key 3 CLEAR sent to TM');
  ok(E(`crewEffectiveKey(2)`)===null,'Key 3 now shows empty on crew side');
  // Scenario B: TECH only an unsent pick on Key 2 (Key 2 currently holds HOST)
  E(`_crewKeyNotes={1:{category:'PLs',label:'TECH'}}; _crewCurrentKeyState={1:{category:'IFBs',label:'HOST'}};`);
  ok(E(`crewFindKeyHolding('PLs','TECH',0)`)===1,'unsent pick also counts as taken');
  E(`crewMoveOption(0,'PLs','TECH',1)`);
  ok(E(`JSON.stringify(_crewKeyNotes)`)==='{"0":{"category":"PLs","label":"TECH","latch":false}}','unsent-pick move → no CLEAR, Key 2 reverts to HOST');
  ok(E(`crewEffectiveKey(1).label`)==='HOST','Key 2 back to HOST');
  // Parser + submit encoding
  ok(E(`etkParseRequestNote('CLEAR').clear`)===true,'TM parses CLEAR instruction');
  ok(errs.length===0,'no runtime errors'+(errs.length?': '+errs.join(' | '):''));
  process.exit();
},1500);
