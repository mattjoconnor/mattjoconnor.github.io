const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('fs');
const file=process.argv[2], role=process.argv[3];
const html=fs.readFileSync(file,'utf8').replace(/<script src="https:\/\/cdn\.jsdelivr[^"]*"><\/script>/,'');
const errors=[];
const vc=new VirtualConsole();
vc.on('jsdomError',e=>errors.push(e.message.split('\n')[0]));
const dom=new JSDOM(html,{url:'https://mattjoconnor.github.io/showcomm/etk/index.html?role='+role,runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
  beforeParse(w){ w.supabase={createClient:()=>null}; w.matchMedia=()=>({matches:false,addListener(){},removeListener(){}}); }});
setTimeout(()=>{
  const d=dom.window.document;
  const crew=d.getElementById('screen-crew');
  const active=d.querySelector('.crew-step.active');
  console.log(role.toUpperCase()+' | errors:',errors.length?errors:'none',
    '| crew screen:',crew?crew.style.display||'(default)':'missing',
    '| active step:',active?active.id:'none');
  process.exit(0);
},1500);
