/* FPL VORTEX shared player-image service.
   Uses the official FPL player code and tries multiple Premier League asset sizes.
   No synthetic/AI portrait is substituted for a named real player. */
(function(){
  "use strict";

  const PLAYER_PATH = "/photos/players/";

  function cleanCode(value){
    return String(value || "").replace(/^p/i, "").replace(/\.png.*$/i, "").trim();
  }

  function codeFromUrl(src){
    const text = String(src || "");
    if(!text.includes(PLAYER_PATH)) return "";
    const match = text.match(/\/players\/(?:500x500|250x250|110x140)\/p?([^/?#]+?)\.png/i);
    return cleanCode(match && match[1]);
  }

  function urls(code){
    const c = encodeURIComponent(cleanCode(code));
    if(!c) return [];
    return [
      `https://resources.premierleague.com/premierleague25/photos/players/500x500/${c}.png`,
      `https://resources.premierleague.com/premierleague25/photos/players/250x250/${c}.png`,
      `https://resources.premierleague.com/premierleague/photos/players/250x250/p${c}.png`,
      `https://resources.premierleague.com/premierleague/photos/players/110x140/p${c}.png`
    ];
  }

  function initials(name){
    return String(name || "?")
      .split(/[\s.-]+/)
      .filter(Boolean)
      .slice(0,2)
      .map(x => x[0])
      .join("")
      .toUpperCase();
  }

  function ensureFallback(img){
    let fallback = img.nextElementSibling;
    if(fallback && fallback.tagName !== "IMG"){
      fallback.style.display = fallback.classList.contains("avatar-fallback") || fallback.classList.contains("pitch-fallback") ? "grid" : "block";
      return;
    }
    fallback = document.createElement("span");
    fallback.className = "vx-player-fallback";
    fallback.textContent = initials(img.alt || "Player");
    img.insertAdjacentElement("afterend", fallback);
  }

  function prepare(img){
    if(!(img instanceof HTMLImageElement)) return;
    const code = cleanCode(img.dataset.playerCode || codeFromUrl(img.currentSrc || img.src));
    if(!code) return;

    const chain = urls(code);
    img.dataset.vxPlayerPhoto = "1";
    img.dataset.playerCode = code;
    img.decoding = "async";
    img.referrerPolicy = "no-referrer-when-downgrade";

    const current = String(img.currentSrc || img.src || "");
    let index = chain.findIndex(x => x === current);
    if(index < 0) index = -1;
    img.dataset.vxPhotoIndex = String(index);
  }

  function nextSource(img){
    const code = cleanCode(img.dataset.playerCode || codeFromUrl(img.currentSrc || img.src));
    if(!code) return false;
    const chain = urls(code);
    let index = Number(img.dataset.vxPhotoIndex || -1);
    for(index += 1; index < chain.length; index++){
      if(chain[index] && chain[index] !== img.src){
        img.dataset.vxPhotoIndex = String(index);
        img.src = chain[index];
        return true;
      }
    }
    return false;
  }

  function scan(root){
    const base = root && root.querySelectorAll ? root : document;
    if(root instanceof HTMLImageElement) prepare(root);
    base.querySelectorAll('img[src*="resources.premierleague.com"][src*="/photos/players/"]').forEach(prepare);
  }

  window.FPLVortexImages = {
    urls,
    initials,
    primaryUrl(player){ return urls(player && player.photo_code)[0] || ""; },
    markup(player, className=""){
      const chain = urls(player && player.photo_code);
      const name = String(player && player.name || "Player").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
      if(!chain.length) return `<span class="vx-player-fallback">${initials(player && player.name)}</span>`;
      return `<img class="${className}" src="${chain[0]}" data-player-code="${cleanCode(player.photo_code)}" data-vx-player-photo="1" data-vx-photo-index="0" alt="${name}" loading="lazy" decoding="async"><span class="vx-player-fallback" style="display:none">${initials(player && player.name)}</span>`;
    }
  };

  window.addEventListener("error", function(event){
    const img = event.target;
    if(!(img instanceof HTMLImageElement)) return;
    if(!img.dataset.vxPlayerPhoto && !codeFromUrl(img.currentSrc || img.src)) return;
    prepare(img);
    if(nextSource(img)){
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    img.style.display = "none";
    ensureFallback(img);
    event.preventDefault();
    event.stopImmediatePropagation();
  }, true);

  const observer = new MutationObserver(records => {
    for(const record of records){
      record.addedNodes.forEach(node => {
        if(node.nodeType === 1) scan(node);
      });
    }
  });

  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", () => scan(document), {once:true});
  } else {
    scan(document);
  }
  observer.observe(document.documentElement, {childList:true, subtree:true});
})();
