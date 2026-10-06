/* FPL VORTEX Expected Minutes — derived from current official usage + availability. */
(function(){
"use strict";
if(typeof TABS==='undefined'||typeof V==='undefined') return;
const vxmState={pos:'ALL',trend:'ALL',team:'ALL',maxPrice:99,sort:'xpts',search:''};
const vxmEvents=()=>[...(D?.events||[])].slice(0,5);
const vxmProjection=(p,gw)=>(p?.projections||[]).find(x=>n(x.gw)===n(gw));
function vxmMinutes(p,gw){
  const projection=vxmProjection(p,gw),fixtureCount=(projection?.fixtures||[]).length;
  if(!fixtureCount) return 0;
  const played=Math.max(1,n(D?.gw,Math.max(1,n(D?.first_gw)-1)));
  const starts=Math.max(0,n(p?.starts)),minutes=Math.max(0,n(p?.minutes));
  const startRate=Math.min(1,starts/played);
  let avgStart;
  if(starts>0) avgStart=Math.min(90,minutes/starts);
  else avgStart=Math.min(65,minutes/played);
  const roleFactor=starts>0?(.55+.45*Math.min(1,startRate*1.25)):.55;
  const availability=p?.chance==null?1:Math.max(0,Math.min(1,n(p.chance)/100));
  return Math.round(Math.max(0,Math.min(180,avgStart*roleFactor*availability*fixtureCount)));
}
function vxmPressure(p){return n(p?.price_signal?.score)}
function vxmPressureLabel(score){
  if(score>=70)return'Strong rise pressure';if(score>=30)return'Rising pressure';if(score>10)return'Slight rise pressure';
  if(score<=-70)return'Strong fall pressure';if(score<=-30)return'Falling pressure';if(score<-10)return'Slight fall pressure';return'Stable pressure';
}
function vxmFiltered(){
  let rows=players();
  if(vxmState.pos!=='ALL')rows=rows.filter(p=>p.pos===vxmState.pos);
  if(vxmState.trend==='RISING')rows=rows.filter(p=>vxmPressure(p)>10);
  if(vxmState.trend==='FALLING')rows=rows.filter(p=>vxmPressure(p)<-10);
  if(vxmState.team!=='ALL')rows=rows.filter(p=>p.team===vxmState.team);
  rows=rows.filter(p=>n(p.price)<=vxmState.maxPrice);
  const score=p=>vxmState.sort==='pressure'?Math.abs(vxmPressure(p)):vxmState.sort==='price'?n(p.price):vxmState.sort==='owned'?n(p.own):n(p.projection_total);
  rows.sort((a,b)=>score(b)-score(a));
  return rows;
}
function vxmToolbar(){
  const teams=[...(D?.teams||[])].sort((a,b)=>String(a.team).localeCompare(String(b.team)));
  return `<div class="vxm-controls">
    <div class="vxm-pills">
      ${['ALL','GKP','DEF','MID','FWD'].map(x=>`<button class="vxm-pill ${vxmState.pos===x?'active':''}" data-vxm-pos="${x}">${x==='ALL'?'All':x}</button>`).join('')}
      <span class="vxm-divider"></span>
      <button class="vxm-pill trend-up ${vxmState.trend==='RISING'?'active':''}" data-vxm-trend="RISING">▲ Rising</button>
      <button class="vxm-pill trend-down ${vxmState.trend==='FALLING'?'active':''}" data-vxm-trend="FALLING">▼ Falling</button>
      <button class="vxm-pill ${vxmState.trend==='ALL'?'active':''}" data-vxm-trend="ALL">All trends</button>
    </div>
    <div class="vxm-tools">
      <label class="vxm-search"><span>⌕</span><input id="vxmSearch" type="search" placeholder="Search any player" value="${e(vxmState.search)}"></label>
      <select class="vxm-select" id="vxmTeam"><option value="ALL">All teams</option>${teams.map(t=>`<option value="${e(t.team)}" ${vxmState.team===t.team?'selected':''}>${e(t.team)} · ${e(t.name)}</option>`).join('')}</select>
      <select class="vxm-select" id="vxmPrice"><option value="99">Any price</option>${[5,6,7.5,10,12].map(v=>`<option value="${v}" ${vxmState.maxPrice===v?'selected':''}>≤ £${v}m</option>`).join('')}</select>
      <select class="vxm-select" id="vxmSort"><option value="xpts" ${vxmState.sort==='xpts'?'selected':''}>Sort: 5GW xPts</option><option value="pressure" ${vxmState.sort==='pressure'?'selected':''}>Sort: price pressure</option><option value="owned" ${vxmState.sort==='owned'?'selected':''}>Sort: ownership</option><option value="price" ${vxmState.sort==='price'?'selected':''}>Sort: price</option></select>
    </div>
  </div>`;
}
function vxmCell(p,event){const proj=vxmProjection(p,event.gw),xp=n(proj?.xpts),mins=vxmMinutes(p,event.gw);return `<td class="vxm-gw"><b>${xp.toFixed(1)}</b><span>${mins}' VxM</span></td>`}
function vortexExpectedMinutes(){
  const events=vxmEvents(),rows=vxmFiltered(),shown=rows.slice(0,120);
  return `${sectionHead('Expected Minutes','Vortex expected-minutes model from season usage, starting frequency, availability and fixture count. Automatically refreshed with the FPL dataset.')}
  <div class="vxm-model-note"><b>VxM = Vortex Expected Minutes.</b> This is a transparent model estimate, not an official FPL probability. Price Pressure is also a directional Vortex signal, not a guaranteed price-change percentage.</div>
  ${vxmToolbar()}
  <section class="vxm-card">
    <div class="vxm-table-wrap"><table class="vxm-table"><thead><tr><th>Player</th><th>Price Pressure</th>${events.map(x=>`<th>GW${n(x.gw)}</th>`).join('')}<th>5GW xPts</th></tr></thead>
    <tbody>${shown.map(p=>{const pressure=vxmPressure(p),cls=pressure>10?'rise':pressure<-10?'fall':'flat';return `<tr class="vxm-row" data-search="${e((p.name+' '+p.team+' '+p.pos).toLowerCase())}"><td><div class="vxm-player">${thumb(p)}<div><strong>${e(p.name)}</strong><span>${e(p.team)} · ${e(p.pos)} · ${money(p.price)} · ${n(p.own).toFixed(1)}% owned</span></div></div></td><td><div class="vxm-pressure ${cls}"><b>${pressure>0?'+':''}${Math.round(pressure)}</b><span>${e(vxmPressureLabel(pressure))}</span></div></td>${events.map(x=>vxmCell(p,x)).join('')}<td class="vxm-total">${n(p.projection_total).toFixed(1)}</td></tr>`}).join('')}</tbody></table></div>
    <div class="vxm-foot"><span id="vxmCount">Showing ${shown.length} of ${rows.length} matching players</span><span>Expected points and VxM refresh automatically with validated FPL VORTEX data.</span></div>
  </section>`;
}
if(!TABS.some(x=>x[0]==='overview'))TABS.unshift(['overview','Dashboard','⌂']);
if(!TABS.some(x=>x[0]==='expected')){
  const dashIndex=TABS.findIndex(x=>x[0]==='overview');
  TABS.splice(dashIndex+1,0,['expected','Expected Minutes','◷']);
}
V.expected=vortexExpectedMinutes;
document.addEventListener('click',ev=>{
  const pos=ev.target.closest('[data-vxm-pos]');if(pos){vxmState.pos=pos.dataset.vxmPos;render();return}
  const trend=ev.target.closest('[data-vxm-trend]');if(trend){vxmState.trend=trend.dataset.vxmTrend;render();return}
});
document.addEventListener('change',ev=>{
  if(ev.target.id==='vxmTeam'){vxmState.team=ev.target.value;render()}
  if(ev.target.id==='vxmPrice'){vxmState.maxPrice=n(ev.target.value,99);render()}
  if(ev.target.id==='vxmSort'){vxmState.sort=ev.target.value;render()}
});
document.addEventListener('input',ev=>{
  if(ev.target.id!=='vxmSearch')return;vxmState.search=ev.target.value||'';const q=vxmState.search.trim().toLowerCase();let visible=0;document.querySelectorAll('.vxm-row').forEach(row=>{const on=!q||String(row.dataset.search||'').includes(q);row.style.display=on?'':'none';if(on)visible++});const count=document.getElementById('vxmCount');if(count)count.textContent=`Showing ${visible} matching players`;
});
if(typeof render==='function'&&D)render();
})();
