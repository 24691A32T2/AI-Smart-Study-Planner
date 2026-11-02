document.getElementById('themeBtn').onclick=()=>{const h=document.documentElement,t=h.dataset.bsTheme==='dark'?'light':'dark';h.dataset.bsTheme=t;localStorage.setItem('theme',t)};
async function loadCharts(){
  const d=await (await fetch('/api/analytics')).json();
  const mk=(id,type,labels,data,label,colors)=>{const e=document.getElementById(id);if(!e)return;
    new Chart(e,{type,data:{labels,datasets:[{label,data,backgroundColor:colors||'#6d5ae6',borderColor:'#4f46e5',tension:.35}]},
      options:{plugins:{legend:{display:type==='doughnut'}},scales:type==='doughnut'?{}:{y:{beginAtZero:true}}}})};
  mk('cDaily','bar',d.daily.labels.map(x=>x.slice(5)),d.daily.data,'Hours');
  mk('cWeekly','line',d.weekly.labels,d.weekly.data,'Hours');
  mk('cSubject','bar',d.subjects.labels,d.subjects.data,'% complete');
  mk('cTasks','doughnut',d.tasks.labels,d.tasks.data,'Tasks',['#10b981','#f59e0b']);
  mk('cConsist','bar',d.consistency.labels.map(x=>x.slice(5)),d.consistency.data,'Studied',d.consistency.data.map(v=>v?'#4f46e5':'#cbd5e1'));
}
