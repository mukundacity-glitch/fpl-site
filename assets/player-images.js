/* FPL VORTEX shared player-image service.
   Identity source: official FPL player metadata only.
   FPL player ID -> player_code/photo_code -> Premier League photo chain -> VORTEX fallback.
   No name matching and no synthetic/AI portrait substitution. */
(function () {
  "use strict";

  const PLAYER_PATH = "/photos/players/";
  const FALLBACK_ATTRS = ["data-alt", "data-f1", "data-f2", "data-f3", "data-srcs"];

  function cleanCode(value) {
    return String(value || "")
      .replace(/^p/i, "")
      .replace(/\.png.*$/i, "")
      .trim();
  }

  function codeFromUrl(src) {
    const text = String(src || "");
    if (!text.includes(PLAYER_PATH)) return "";
    const match = text.match(/\/players\/(?:500x500|250x250|110x140)\/p?([^/?#]+?)\.png/i);
    return cleanCode(match && match[1]);
  }

  function urls(code) {
    const playerCode = encodeURIComponent(cleanCode(code));
    if (!playerCode) return [];
    return [
      `https://resources.premierleague.com/premierleague25/photos/players/500x500/${playerCode}.png`,
      `https://resources.premierleague.com/premierleague25/photos/players/250x250/${playerCode}.png`,
      `https://resources.premierleague.com/premierleague/photos/players/250x250/p${playerCode}.png`,
      `https://resources.premierleague.com/premierleague/photos/players/110x140/p${playerCode}.png`,
    ];
  }

  function initials(name) {
    return String(name || "?")
      .split(/[\s.-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase();
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[char]);
  }

  function showFallback(img) {
    let fallback = img.nextElementSibling;
    if (!fallback || fallback.tagName === "IMG") {
      fallback = document.createElement("span");
      fallback.className = "vx-player-fallback";
      fallback.textContent = initials(img.alt || "Player");
      img.insertAdjacentElement("afterend", fallback);
    }
    fallback.style.display = "grid";
  }

  function deleteOldImageLogic(img) {
    // One shared error pipeline must own player photos; old per-page handlers are removed in-place.
    img.onerror = null;
    img.removeAttribute("onerror");
    for (const attr of FALLBACK_ATTRS) img.removeAttribute(attr);
  }

  function prepare(img, forcePrimary = false) {
    if (!(img instanceof HTMLImageElement)) return false;

    const code = cleanCode(img.dataset.playerCode || codeFromUrl(img.currentSrc || img.src));
    if (!code) return false;

    const chain = urls(code);
    if (!chain.length) return false;

    const wasPrepared = img.dataset.vxPlayerPhoto === "1";
    deleteOldImageLogic(img);

    img.dataset.vxPlayerPhoto = "1";
    img.dataset.playerCode = code;
    img.decoding = "async";
    img.referrerPolicy = "no-referrer-when-downgrade";

    const current = String(img.currentSrc || img.src || "");
    const currentIndex = chain.indexOf(current);

    if (forcePrimary || (!wasPrepared && current !== chain[0])) {
      img.dataset.vxPhotoIndex = "0";
      img.src = chain[0];
      return true;
    }

    img.dataset.vxPhotoIndex = String(currentIndex >= 0 ? currentIndex : 0);
    return true;
  }

  function nextSource(img) {
    const code = cleanCode(img.dataset.playerCode || codeFromUrl(img.currentSrc || img.src));
    if (!code) return false;

    const chain = urls(code);
    let index = Number(img.dataset.vxPhotoIndex || 0);
    for (index += 1; index < chain.length; index += 1) {
      if (!chain[index]) continue;
      img.dataset.vxPhotoIndex = String(index);
      img.src = chain[index];
      return true;
    }
    return false;
  }

  function scan(root) {
    if (root instanceof HTMLImageElement) prepare(root);
    const base = root && root.querySelectorAll ? root : document;
    base
      .querySelectorAll('img[data-player-code], img[src*="resources.premierleague.com"][src*="/photos/players/"]')
      .forEach((img) => prepare(img));
  }

  window.FPLVortexImages = Object.freeze({
    urls,
    initials,
    primaryUrl(player) {
      return urls(player && player.photo_code)[0] || "";
    },
    markup(player, className = "") {
      const chain = urls(player && player.photo_code);
      const name = escapeHtml((player && player.name) || "Player");
      const fallback = escapeHtml(initials(player && player.name));
      if (!chain.length) return `<span class="vx-player-fallback">${fallback}</span>`;
      return `<img class="${escapeHtml(className)}" src="${chain[0]}" data-player-code="${escapeHtml(cleanCode(player.photo_code))}" data-vx-player-photo="1" data-vx-photo-index="0" alt="${name}" loading="lazy" decoding="async"><span class="vx-player-fallback" style="display:none">${fallback}</span>`;
    },
  });

  window.addEventListener(
    "error",
    function (event) {
      const img = event.target;
      if (!(img instanceof HTMLImageElement)) return;
      if (!img.dataset.vxPlayerPhoto && !codeFromUrl(img.currentSrc || img.src)) return;

      const wasPrepared = img.dataset.vxPlayerPhoto === "1";
      prepare(img, !wasPrepared);

      event.preventDefault();
      event.stopImmediatePropagation();

      // An old page-specific URL failed before normalization. Restart at the official 500x500 source.
      if (!wasPrepared) return;
      if (nextSource(img)) return;

      img.style.display = "none";
      showFallback(img);
    },
    true,
  );

  const observer = new MutationObserver((records) => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (node.nodeType === 1) scan(node);
      }
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => scan(document), { once: true });
  } else {
    scan(document);
  }
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
