let kind='focus',total=1500,left=1500,timer=null;const $=id=>document.getElementById(id);
const draw=()=>$('clock').textContent=String(Math.floor(left/60)).padStart(2,'0')+':'+String(left%60).padStart(2,'0');
function setMode(b){pause();kind=b.dataset.kind;total=left=+b.dataset.min*60;document.querySelectorAll('.mode').forEach(x=>x.classList.toggle('active',x===b));draw()}
function pause(){clearInterval(timer);timer=null}
async function done(){pause();new Audio('data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQAAAAA=').play().catch(()=>{});
  if(kind==='focus'){const r=await fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({minutes:total/60,subject_id:$('subj').value||null})});
    if(r.ok){const n=$('subj').selectedOptions[0].text;$('log').insertAdjacentHTML('beforeend',`<div class="slot study">${total/60} min · ${n}</div>`);$('cnt').textContent=+$('cnt').textContent+1}}
  alert(kind==='focus'?'Focus session recorded! Take a break.':'Break over!')}
$('start').onclick=()=>{if(timer)return;timer=setInterval(()=>{if(--left<=0){left=0;draw();done()}else draw()},1000)};
$('pause').onclick=pause;$('reset').onclick=()=>{pause();left=total;draw()};
document.querySelectorAll('.mode').forEach(b=>b.onclick=()=>setMode(b));setMode(document.querySelector('.mode'));
