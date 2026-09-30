// Runs inside a page: every visible element with its own text -> size, weight, contrast vs. its real background
(() => {
  const parse = s => { const m = /rgba?\(([^)]+)\)/.exec(s||''); if(!m) return null; const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}; };
  const over = (top, under) => ({ r: top.r*top.a + under.r*(1-top.a), g: top.g*top.a + under.g*(1-top.a), b: top.b*top.a + under.b*(1-top.a), a: 1 });
  const lum = c => { const f = v => { v/=255; return v<=.03928 ? v/12.92 : Math.pow((v+.055)/1.055, 2.4); }; return .2126*f(c.r)+.7152*f(c.g)+.0722*f(c.b); };
  const ratio = (a,b) => { const x=lum(a), y=lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
  function background(el){
    const stack=[]; let e=el, img=false;
    while(e && e.nodeType===1){ const cs=getComputedStyle(e); if(cs.backgroundImage && cs.backgroundImage!=='none') img=true; const c=parse(cs.backgroundColor); if(c && c.a>0) stack.push(c); if(c && c.a>=1) break; e=e.parentElement; }
    let bg={r:255,g:255,b:255,a:1}; for(let i=stack.length-1;i>=0;i--) bg=over(stack[i],bg); return {bg, img};
  }
  const out=[];
  for(const el of document.querySelectorAll('body *')){
    if(['SCRIPT','STYLE','svg','path','OPTION'].includes(el.tagName)) continue;
    const own=[...el.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join(' ').trim(); if(!own) continue;
    const cs=getComputedStyle(el); if(cs.display==='none'||cs.visibility==='hidden') continue;
    const r=el.getBoundingClientRect(); if(r.width<1||r.height<1) continue;
    let op=1, e=el; while(e && e.nodeType===1){ op*=+getComputedStyle(e).opacity; e=e.parentElement; } if(op<0.05) continue;
    if(el.closest('[aria-hidden="true"]')) continue;
    if(el.closest('button:disabled,.disabled')) continue;          // disabled controls may be dim
    const fs=parseFloat(cs.fontSize), fw=+cs.fontWeight||400;
    const {bg,img}=background(el); let fg=parse(cs.color); fg={...fg, a:fg.a*op};
    const c=ratio(over(fg,bg),bg), large = fs>=24 || (fs>=18.66 && fw>=700);
    out.push({text:own.slice(0,40), cls:(el.className&&el.className.baseVal===undefined?el.className:'').toString().slice(0,40), fs:+fs.toFixed(1), fw, contrast:+c.toFixed(2), need: large?3:4.5, imgBg:img, y:Math.round(r.top)});
  }
  return out;
})()
