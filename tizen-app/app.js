/* KFS Kitchen Display — signage client.
 * Polls the control server for a scene, renders it fullscreen.
 * Scene types: image, video, menu, url, blank
 */
(function () {
  "use strict";

  // ---- config: server IP/port. Set to the control server (this PC). ----
  var SERVER = "http://10.1.10.238:8080";
  var TV_ID = "menu1"; // rewritten per TV by scripts/build-install.sh
  // "iframe" keeps this app alive and polling while a web page is shown.
  // "navigate" replaces the app with the page: the TV then never polls again
  // and gets stuck on that page until the app is relaunched. The earlier
  // blank-iframe problem was most likely CSS `inset` (unsupported on 2020
  // Tizen 5.5 / Chromium M69) collapsing #stage to 0x0 - fixed in index.html.
  var URL_MODE = "iframe";
  var POLL_MS = 3000;

  var stage = document.getElementById("stage");
  var menuEl = document.getElementById("menu");
  var offlineEl = document.getElementById("offline");
  var statusEl = document.getElementById("status");
  var current = null;
  var offline = false;

  function setStatus(s) { statusEl.textContent = s; }

  function showOffline(on) {
    if (on === offline) return;
    offline = on;
    offlineEl.style.display = on ? "flex" : "none";
  }

  function clearStage() {
    stage.innerHTML = "";
    menuEl.style.display = "none";
  }

  function renderImage(url) {
    clearStage();
    var img = document.createElement("img");
    img.src = url;
    stage.appendChild(img);
  }

  function renderVideo(url, loop) {
    clearStage();
    var v = document.createElement("video");
    v.src = url;
    v.autoplay = true;
    v.loop = loop !== false;
    v.muted = true;
    v.playsInline = true;
    v.style.objectFit = "contain";
    stage.appendChild(v);
    v.play().catch(function () {});
  }

  function renderMenu(data) {
    clearStage();
    menuEl.style.display = "flex";
    var html = '<div class="header">' + esc(data.title || "MENU") + "</div>";
    html += '<div class="items">';
    (data.items || []).forEach(function (it) {
      html += '<div class="item"><span>' + esc(it.name) + "</span>" +
              '<span class="price">' + esc(it.price) + "</span></div>";
    });
    html += "</div>";
    if (data.footer) html += '<div class="footer">' + esc(data.footer) + "</div>";
    menuEl.innerHTML = html;
  }

  function renderUrl(url) {
    clearStage();
    var source = String(url || "");
    var target = /^https?:\/\//i.test(source)
      ? source
      : (SERVER + "/content/" + source.split("/").map(encodeURIComponent).join("/"));
    setStatus("loading page: " + target);
    if (URL_MODE === "navigate") { window.location.replace(target); return; }
    var f = document.createElement("iframe");
    f.src = target;
    stage.appendChild(f);
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function applyScene(scene) {
    if (!scene || !scene.type) return;
    // compare the whole scene so menu price edits / loop changes re-render
    var key = JSON.stringify(scene);
    if (key === current) return; // no change
    current = key;
    var base = SERVER;
    switch (scene.type) {
      case "image": renderImage(base + "/content/" + scene.src); break;
      case "video": renderVideo(base + "/content/" + scene.src, scene.loop); break;
      case "menu": renderMenu(scene); break;
      case "url": renderUrl(scene.src); break;
      case "blank": clearStage(); break;
      default: setStatus("unsupported scene: " + scene.type); return;
    }
    setStatus("scene: " + scene.type + " " + (scene.src || scene.title || ""));
  }

  function poll() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", SERVER + "/scene/" + TV_ID + "?t=" + Date.now(), true);
    xhr.timeout = 5000;
    xhr.onload = function () {
      if (xhr.status === 200) {
        showOffline(false);
        try { applyScene(JSON.parse(xhr.responseText.replace(/^\uFEFF/, ""))); }
        catch (e) {
          setStatus("bad scene JSON; loading menu fallback");
          applyScene({ type: "url", src: "menu-premium.html" });
        }
      } else { showOffline(true); }
    };
    xhr.onerror = function () { showOffline(true); };
    xhr.ontimeout = function () { showOffline(true); };
    xhr.send();
  }

  setInterval(poll, POLL_MS);
  poll();
  setStatus("KFS display " + TV_ID + " — connecting…");
})();
