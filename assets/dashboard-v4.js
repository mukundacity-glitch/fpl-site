/* FPL VORTEX dashboard v4 — full player explorer + official image fallbacks */
(function(){
"use strict";
const v4={page:0,size:20,sort:'points',pos:'ALL',search:'',installed:false};
const N=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const E=v=>String(v??'').replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const initials=name=>String(name||'?').split(/[\s.-]+/).filter(Boolean).slice(0,2).map(x=>x[0]).join('').toUpperCase();
function photoUrls(p){
  const code=String(p?.photo_code||'').replace(/\.(jpg|png)$/i,'');
  if(!code)return[];
  return [
    `https://resources.premierleague.com/premierleague25/photos/players/500x500/${encodeURIComponent(code)}.png`,
    `https://resources.premierleague.com/premierleague25/photos/players/250x250/${encodeURIComponent(code)}.png`,
    `https://resources.premierleague.com/premierleague25/photos/players/110x140/${encodeURIComponent(code)}.png`,
    `https://resources.premierleague.com/premierleague/photos/players/250x250/p${encodeURIComponent(code)}.png`
  ];
}
function playerImg(p){
  const u=photoUrls(p),fallback=E(initials(p?.name));
  if(!u.length)return`<span class="v4-img-fallback">${fallback}</span>`;
  return `<img class="v4-player-img" src="${u[0]}" data-f1="${u[1]}" data-f2="${u[2]}" data-f3="${u[3]}" alt="${E(p?.name||'Player')}" loading="lazy" onerror="if(this.dataset.f1){this.src=this.dataset.f1;this.dataset.f1=''}else if(this.dataset.f2){this.src=this.dataset.f2;this.dataset.f2=''}else if(this.dataset.f3){this.src=this.dataset.f3;this.dataset.f3=''}else{this.style.display='none';this.nextElementSibling.style.display='grid'}"><span class="v4-img-fallback" style="display:none">${fallback}</span>`;
}
function score(p){
  if(v4.sort==='xpts')return N(p.xpts);
  if(v4.sort==='five')return N(p.projection_total);
  if(v4.sort==='owned')return N(p.own);
  if(v4.sort==='value')return N(p.total_points)/Math.max(3.5,N(p.price));
  return N(p.total_points,N(p.xpts));
}
function filtered(){
  let a=[...(D?.players||[])];
  if(v4.pos!=='ALL')a=a.filter(p=>p.pos===v4.pos);
  const q=v4.search.trim().toLowerCase();
  if(q)a=a.filter(p=>`${p.name||''} ${p.team||''} ${p.pos||''}`.toLowerCase().includes(q));
  a.sort((x,y)=>score(y)-score(x)||N(y.xpts)-N(x.xpts)||String(x.name).localeCompare(String(y.name)));
  return a;
}
function playerRows(){
  const a=filtered(),pages=Math.max(1,Math.ceil(a.length/v4.size));v4.page=Math.min(v4.page,pages-1);const start=v4.page*v4.size,list=a.slice(start,start+v4.size);
  const rows=list.map((p,i)=>{
    const chance=p.chance==null?null:N(p.chance),avail=chance==null?(p.status==='a'?'Available':'Flagged'):`${chance.toFixed(0)}%`;
    const availCls=chance!=null&&chance<75?'v4-bad':p.status&&p.status!=='a'?'v4-warn':'v4-good';
    return `<tr><td><div class="v4-player-cell"><span class="v4-imgbox">${playerImg(p)}</span><div><div class="v4-player-name">${E(p.name)}</div><div class="v4-player-sub">${E(p.team)} · ${E(p.pos)}</div></div></div></td><td>${E(p.team)}</td><td>${E(p.pos)}</td><td class="v4-num">£${N(p.price).toFixed(1)}m</td><td class="v4-num">${Math.round(N(p.total_points))}</td><td class="v4-num v4-good">${N(p.xpts).toFixed(1)}</td><td class="v4-num">${N(p.projection_total).toFixed(1)}</td><td>${N(p.own).toFixed(1)}%</td><td>${N(p.form).toFixed(1)}</td><td class="${availCls}">${E(avail)}</td></tr>`;
  }).join('');
  return {rows,a,pages,start};
}
function allPlayers(){
  const x=playerRows();
  return `<section class="premium-panel v4-player-panel" id="v4AllPlayers"><div class="v4-player-head"><div class="v4-player-title">All Players<small>Browse the complete automated FPL VORTEX player pool — not only the top ten.</small></div><div class="v4-player-count">${x.a.length} players</div></div>
  <div class="v4-player-controls"><input class="v4-search" id="v4Search" type="search" placeholder="Search player or club" value="${E(v4.search)}">${['ALL','GKP','DEF','MID','FWD'].map(p=>`<button class="v4-filter ${v4.pos===p?'active':''}" data-v4-pos="${p}">${p==='ALL'?'All':p}</button>`).join('')}<span style="flex:1"></span>${[['points','Points'],['xpts','GW xPts'],['five','5GW xPts'],['owned','Owned'],['value','Value']].map(([k,l])=>`<button class="v4-sort ${v4.sort===k?'active':''}" data-v4-sort="${k}">${l}</button>`).join('')}</div>
  <div class="v4-table-wrap"><table class="v4-table"><thead><tr><th>Player</th><th>Club</th><th>Pos</th><th>Price</th><th>Points</th><th>GW xPts</th><th>5GW xPts</th><th>Owned</th><th>Form</th><th>Availability</th></tr></thead><tbody>${x.rows||'<tr><td colspan="10">No matching players.</td></tr>'}</tbody></table></div>
  <div class="v4-pager"><button class="v4-page-btn" data-v4-page="prev" ${v4.page<=0?'disabled':''}>‹ Previous</button><span class="v4-page-status">Page ${v4.page+1} of ${x.pages} · showing ${x.a.length?x.start+1:0}-${Math.min(x.start+v4.size,x.a.length)} of ${x.a.length}</span><button class="v4-page-btn" data-v4-page="next" ${v4.page>=x.pages-1?'disabled':''}>Next ›</button></div></section>`;
}
function install(){
  if(v4.installed||typeof V==='undefined'||typeof D==='undefined'||!D)return false;
  if(typeof V.overview!=='function'||V.overview.name!=='premiumOverview')return false;
  const base=V.overview;
  V.overview=function vortexDashboardV4(){return base()+allPlayers()};
  v4.installed=true;
  if(currentTab==='overview')render();
  return true;
}
let searchTimer=null;
document.addEventListener('click',ev=>{
  const sort=ev.target.closest?.('[data-v4-sort]');if(sort){v4.sort=sort.dataset.v4Sort;v4.page=0;render();return}
  const pos=ev.target.closest?.('[data-v4-pos]');if(pos){v4.pos=pos.dataset.v4Pos;v4.page=0;render();return}
  const page=ev.target.closest?.('[data-v4-page]');if(page&&!page.disabled){v4.page+=page.dataset.v4Page==='next'?1:-1;render();setTimeout(()=>document.getElementById('v4AllPlayers')?.scrollIntoView({behavior:'smooth',block:'start'}),30);return}
});
document.addEventListener('input',ev=>{
  if(ev.target.id!=='v4Search')return;
  v4.search=ev.target.value||'';v4.page=0;clearTimeout(searchTimer);const cursor=v4.search.length;
  searchTimer=setTimeout(()=>{render();setTimeout(()=>{const el=document.getElementById('v4Search');if(el){el.focus();try{el.setSelectionRange(cursor,cursor)}catch{}}},20)},180);
});
const timer=setInterval(()=>{if(install())clearInterval(timer)},80);setTimeout(()=>clearInterval(timer),12000);
})();
