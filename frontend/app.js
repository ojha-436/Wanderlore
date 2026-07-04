// Wanderlore app: auth guard, discover, storytelling (text + photo), itinerary, save.
import { getFirebaseAuth, getConfig } from "./firebase-init.js";
import {
  onAuthStateChanged,
  signOut,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const $ = (id) => document.getElementById(id);
let currentUser = null;
let lastDiscover = null;
const selected = new Map(); // id -> {id,name,category,duration_minutes}

const esc = (s) =>
  String(s == null ? "" : s)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const paras = (t) =>
  String(t || "").split(/\n\s*\n/).map((p) => `<p>${esc(p.trim())}</p>`).join("");

async function authFetch(url, opts = {}) {
  const headers = Object.assign({}, opts.headers);
  if (currentUser) {
    const token = await currentUser.getIdToken();
    if (token) headers["Authorization"] = "Bearer " + token;
  }
  return fetch(url, { ...opts, headers });
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg; t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

// ---------------------------------------------------------------- bootstrap
async function main() {
  const cfg = await getConfig();

  $("logout-btn").addEventListener("click", async () => {
    if (cfg.authRequired) {
      const auth = await getFirebaseAuth();
      await signOut(auth);
    }
    window.location.href = "/login.html";
  });

  if (!cfg.authRequired) {
    currentUser = { getIdToken: async () => "", email: "demo@wanderlore.app", displayName: "Demo Explorer" };
    return start();
  }
  const auth = await getFirebaseAuth();
  onAuthStateChanged(auth, (user) => {
    if (!user) { window.location.href = "/login.html"; return; }
    currentUser = user; start();
  });
}

async function start() {
  wire();
  await loadProfile();
}

async function loadProfile() {
  try {
    const p = await (await authFetch("/api/me")).json();
    $("p-name").textContent = p.display_name || currentUser.displayName || "Explorer";
    $("p-email").textContent = p.email || currentUser.email || "";
    const initial = (p.display_name || p.email || "E").trim().charAt(0).toUpperCase();
    if (p.photo_url) $("p-avatar").outerHTML = `<img class="avatar" id="p-avatar" src="${esc(p.photo_url)}" alt="">`;
    else $("p-avatar").textContent = initial;
    if (Array.isArray(p.interests) && p.interests.length) {
      const cbMap = {};
      $("interests-dropdown").querySelectorAll('input[type="checkbox"]').forEach(cb => {
        if (cb.value) cbMap[cb.value.toLowerCase()] = cb;
      });
      const custom = [];
      p.interests.forEach(i => {
        const v = i.toLowerCase();
        if (cbMap[v]) cbMap[v].checked = true;
        else custom.push(i);
      });
      if (custom.length) {
        $("interest-other-cb").checked = true;
        $("interest-other-wrap").style.display = "block";
        $("interest-other-text").value = custom.join(", ");
      }
      if ($("interest-other-cb")) $("interest-other-cb").dispatchEvent(new Event("change"));
    }
  } catch {
    $("p-name").textContent = currentUser.displayName || "Explorer";
    $("p-email").textContent = currentUser.email || "";
  }
}

// ---------------------------------------------------------------- discover
function splitCsv(v) { return (v || "").split(",").map((s) => s.trim()).filter(Boolean); }

async function discover() {
  const btn = $("discover-btn");
  $("discover-error").textContent = "";
  const body = {
    destination: $("dest").value.trim(),
    travel_dates: $("dates").value.trim() || null,
    num_days: parseInt($("days").value || "3", 10),
    interests: (() => {
      const cbs = Array.from($("interests-dropdown").querySelectorAll('input[type="checkbox"]:checked'))
        .filter(c => c.id !== "interest-other-cb" && c.value)
        .map(c => c.value);
      if ($("interest-other-cb").checked && $("interest-other-text").value.trim()) {
        cbs.push(...splitCsv($("interest-other-text").value));
      }
      return cbs;
    })(),
    pace: $("pace").value,
  };
  if (!body.destination) { $("discover-error").textContent = "Where would you like to go?"; return; }
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Exploring…';
  $("results").innerHTML = '<div class="loading"><span class="spinner"></span> Wandering the streets of ' + esc(body.destination) + '…</div>';
  try {
    const res = await authFetch("/api/discover", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Discovery failed");
    lastDiscover = await res.json();
    renderDiscover(lastDiscover);
  } catch (e) {
    $("results").innerHTML = "";
    $("discover-error").textContent = "Couldn't explore that destination: " + e.message;
  } finally {
    btn.disabled = false; btn.innerHTML = 'Discover <span class="arrow">→</span>';
  }
}

function placeCard(item, kind, idx) {
  const id = `${kind}-${idx}-${(item.name || "").toLowerCase().replace(/\s+/g, "-").slice(0, 24)}`;
  const dur = item.suggested_duration_minutes || 90;
  const cat = item.category || item.type || kind;
  const why = item.why_for_you || item.why_special || item.description || "";
  const meta = [];
  if (item.area) meta.push(esc(item.area));
  if (item.best_time) meta.push(esc(item.best_time));
  meta.push(`~${Math.round(dur / 60 * 10) / 10}h`);
  if (item.etiquette_tip) meta.push("etiquette ✓");
  const on = selected.has(id) ? "on" : "";
  const img = item.photo_url ? `<div style="height:140px; background:url('${esc(item.photo_url)}') center/cover; border-radius:12px 12px 0 0; margin: -20px -20px 16px -20px;"></div>` : "";
  const ratingStr = item.rating ? `<span style="float:right; color:var(--rust)">★ ${item.rating}</span>` : "";
  return `<div class="place-card">
    ${img}
    <button class="star-btn ${on}" data-id="${id}" data-name="${esc(item.name)}" data-cat="${esc(cat)}" data-dur="${dur}" title="Add to trip">★</button>
    <span class="pc-cat">${esc(cat)}${ratingStr}</span>
    <h3>${esc(item.name)}</h3>
    <p class="pc-why">${esc(why)}</p>
    <div class="pc-meta">${meta.map((m) => `<span>${m}</span>`).join("")}</div>
    <div class="pc-actions">
      <button class="pc-btn story-btn" data-place="${esc(item.name)}">Tell its story</button>
    </div>
  </div>`;
}

function section(num, title, tag, innerHtml) {
  return `<section class="result-section"><div class="rs-head"><span class="rs-num">${num}</span><h2>${title}</h2><span class="rs-tag">${tag}</span></div>${innerHtml}</section>`;
}

function renderDiscover(d) {
  const grid = (arr, kind) => `<div class="card-grid">${arr.map((it, i) => placeCard(it, kind, i)).join("")}</div>`;
  let html = "";
  html += `<section class="result-section"><div class="rs-head"><span class="rs-num">◦</span><h2>${esc(d.destination)}</h2><span class="rs-tag">overview</span><button class="btn btn-ghost" id="save-explore-btn" style="margin-left:auto; border-color:var(--rust); color:var(--rust)">Save Exploration</button></div><p class="summary-lead">${esc(d.summary)}</p></section>`;
  
  if (d.weather_advisory && !d.weather_advisory.error) {
    const w = d.weather_advisory;
    html += section("⛅", "Traveler Advisory", "weather", `<div class="event-card"><h3 style="margin-top:0">Forecast</h3><p style="margin-bottom:0">${esc(w.summary)}</p></div>`);
  }
  
  html += section("01", "Attractions for you", "recommend", grid(d.attractions || [], "attraction"));
  html += section("02", "Hidden gems", "discover", grid(d.hidden_gems || [], "gem"));
  html += section("06", "Authentic experiences", "connect", grid(d.experiences || [], "experience"));

  let eventsHtml = "";
  if ((d.events || []).length) {
    eventsHtml += (d.events).map((e) => `<div class="event-card"><span class="ev-when">${esc(e.when_hint || "during your trip")}</span><h3>${esc(e.name)}</h3><p>${esc(e.description)}</p><p style="color:var(--teal);font-weight:600">${esc(e.why_go)}</p></div>`).join("");
  } else {
    eventsHtml += `<p class="summary-lead" style="font-size:1rem">${esc(d.notes || "No dated events found.")}</p>`;
  }
  if ((d.event_citations || []).length) {
    eventsHtml += `<div class="citations"><div class="cl">Sources · grounded with Google Search</div>` +
      d.event_citations.map((c) => `<a class="citation" href="${esc(c.uri)}" target="_blank" rel="noopener">🔗 ${esc(c.title || c.uri)}</a>`).join("") + `</div>`;
  }
  html += section("05", "What's happening now", "events · grounded", eventsHtml);

  $("results").innerHTML = html;
  // wire dynamic buttons
  $("results").querySelectorAll(".star-btn").forEach((b) => b.addEventListener("click", onStar));
  $("results").querySelectorAll(".story-btn").forEach((b) => b.addEventListener("click", () => tellStory(b.dataset.place)));
  const saveExpBtn = $("save-explore-btn");
  if (saveExpBtn) saveExpBtn.addEventListener("click", saveTrip);
}

// ---------------------------------------------------------------- trip / star
function onStar(e) {
  const b = e.currentTarget;
  const id = b.dataset.id;
  if (selected.has(id)) { selected.delete(id); b.classList.remove("on"); }
  else {
    selected.set(id, { id, name: b.dataset.name, category: b.dataset.cat, duration_minutes: parseInt(b.dataset.dur, 10) });
    b.classList.add("on");
  }
  $("tray-n").textContent = selected.size;
  $("tray").classList.toggle("show", selected.size > 0);
}

async function buildItinerary() {
  if (!selected.size) return toast("Star a few places first");
  const btn = $("build-btn"); btn.disabled = true;
  try {
    const body = {
      items: [...selected.values()],
      num_days: parseInt($("days").value || "3", 10),
      daily_hours: parseFloat($("daily-hours").value || "8"),
    };
    const res = await authFetch("/api/itinerary", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Itinerary failed");
    renderItinerary(await res.json());
  } catch (e) { toast(e.message); } finally { btn.disabled = false; }
}

function renderItinerary(it) {
  let cont = $("itin");
  if (!cont) {
    cont = document.createElement("div"); cont.id = "itin";
    $("results").parentNode.insertBefore(cont, $("results"));
  }
  const days = it.days.map((d) => `<div class="day-col"><div class="day-h"><span class="dn">Day ${d.day_number}</span><span class="dm">${Math.round(d.minutes_used / 60 * 10) / 10}h</span></div>${
    d.items.length ? d.items.map((i) => `<div class="day-item"><span class="di-dur">${Math.round(i.duration_minutes / 60 * 10) / 10}h</span><span class="di-cat">${esc(i.category)}</span><br>${esc(i.name)}</div>`).join("") : '<div class="day-item" style="color:var(--ink-faint)">Open — leave room to wander</div>'
  }</div>`).join("");
  const overflow = it.overflow.length
    ? `<div class="overflow-note"><b>Didn't fit:</b> ${it.overflow.map((i) => esc(i.name)).join(", ")}. Add a day or raise hours/day.</div>` : "";
  cont.innerHTML = section("◇", "Your itinerary", "planned by Wanderlore", `<div class="itin-days">${days}</div>${overflow}`);
  cont.scrollIntoView({ behavior: "smooth" });
}

async function saveTrip() {
  if (!lastDiscover) return toast("Discover a destination first");
  try {
    const res = await authFetch("/api/trips", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        destination: lastDiscover.destination,
        label: lastDiscover.destination,
        payload: { discover: lastDiscover, selected: [...selected.values()] },
      }),
    });
    if (!res.ok) throw new Error("Save failed");
    toast("Trip saved to your journeys ✓");
  } catch (e) { toast(e.message); }
}

// ---------------------------------------------------------------- storytelling
function openDrawer(html) {
  $("drawer-content").innerHTML = html;
  $("drawer").classList.add("open"); $("overlay").classList.add("open");
}
function closeDrawer() { $("drawer").classList.remove("open"); $("overlay").classList.remove("open"); }

async function viewProfile() {
  openDrawer('<div class="loading"><span class="spinner"></span> Loading profile…</div>');
  try {
    const [pRes, tRes] = await Promise.all([
      authFetch("/api/me"),
      authFetch("/api/trips")
    ]);
    if (!pRes.ok) throw new Error("Couldn't load profile");
    const p = await pRes.json();
    const tripsData = tRes.ok ? await tRes.json() : { trips: [] };
    
    let html = `
      <div class="st-kicker">Traveler Profile</div>
      <h2>${esc(p.display_name || "Explorer")}</h2>
      <p style="color:var(--ink-faint)">${esc(p.email || "")}</p>
      
      <div class="st-note" style="margin-top:20px">
        <div class="lbl">Preferences</div>
        <p style="margin-top:6px"><b>Pace:</b> ${esc(p.travel_style || "Balanced")}</p>
        <p style="margin-top:6px"><b>Interests:</b> ${esc((p.interests || []).join(", ") || "None specified")}</p>
      </div>
      
      <h3 style="margin-top:30px; border-bottom:1px solid #ddd; padding-bottom:8px">Saved Explorations</h3>
    `;
    
    if (!tripsData.trips || !tripsData.trips.length) {
      html += `<p style="margin-top:16px; color:var(--ink-faint)">No saved explorations yet.</p>`;
    } else {
      html += `<div style="display:flex; flex-direction:column; gap:12px; margin-top:16px">`;
      for (const t of tripsData.trips) {
        let dateStr = "";
        if (t.createdAt) {
          dateStr = new Date(t.createdAt).toLocaleDateString();
        }
        html += `
          <div class="event-card" style="padding:12px">
            <h4 style="margin:0; font-size:1.1rem; color:var(--rust)">${esc(t.label || t.destination)}</h4>
            <div style="font-size:0.85rem; color:var(--ink-faint); margin-top:4px">${dateStr}</div>
          </div>
        `;
      }
      html += `</div>`;
    }
    openDrawer(html);
  } catch (e) {
    openDrawer(`<p>${esc(e.message)}</p>`);
  }
}

async function tellStory(place) {
  openDrawer(`<div class="loading"><span class="spinner"></span> Unfolding the story of ${esc(place)}…</div>`);
  try {
    const tone = $("photo-tone") ? $("photo-tone").value : "historical";
    const res = await authFetch("/api/story", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ place, destination_context: lastDiscover ? lastDiscover.destination : null, tone }),
    });
    if (!res.ok) throw new Error("Story failed");
    const s = await res.json();
    openDrawer(`
      <div class="st-kicker">Immersive story · heritage</div>
      <h2>${esc(s.title)}</h2>
      <div class="st-body">${paras(s.story)}</div>
      <div class="st-note"><div class="lbl">Living heritage</div><p style="margin-top:6px">${esc(s.heritage_note)}</p></div>
      <div class="st-note" style="border-color:var(--rust);margin-top:14px"><div class="lbl" style="color:var(--rust)">Did you know</div><p style="margin-top:6px">${esc(s.did_you_know)}</p></div>`);
  } catch (e) { openDrawer(`<p>${esc(e.message)}</p>`); }
}

async function photoStory(file) {
  openDrawer('<div class="loading"><span class="spinner"></span> Reading the landmark…</div>');
  try {
    const tone = $("photo-tone") ? $("photo-tone").value : "historical";
    const form = new FormData(); form.append("image", file); form.append("tone", tone);
    const res = await authFetch("/api/story/photo", { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Couldn't read the photo");
    const s = await res.json();
    if (!s.identified) {
      openDrawer(`<div class="st-kicker">Landmark</div><h2>Hmm, not sure</h2><p class="st-body">${esc(s.story || "We couldn't confidently identify a landmark in that photo. Try a clearer shot of a monument or notable place.")}</p>`);
      return;
    }
    openDrawer(`
      <div class="st-kicker">Identified · ${Math.round((s.confidence || 0) * 100)}% confident</div>
      <h2>${esc(s.name || s.title)}</h2>
      <div class="st-loc">${esc(s.location_guess || "")}</div>
      <div class="st-body">${paras(s.story)}</div>
      <div class="st-note"><div class="lbl">Living heritage</div><p style="margin-top:6px">${esc(s.heritage_note)}</p></div>`);
  } catch (e) { openDrawer(`<p>${esc(e.message)}</p>`); }
}

// ---------------------------------------------------------------- wire
function wire() {
  $("discover-btn").addEventListener("click", discover);
  $("build-btn").addEventListener("click", buildItinerary);
  $("save-btn").addEventListener("click", saveTrip);
  $("drawer-close").addEventListener("click", closeDrawer);
  $("overlay").addEventListener("click", closeDrawer);
  $("photo-input").addEventListener("change", (e) => { if (e.target.files[0]) photoStory(e.target.files[0]); });
  const pc = $("profile-chip");
  if (pc) pc.addEventListener("click", viewProfile);

  const intHdr = $("interests-header");
  const intDrop = $("interests-dropdown");
  const intDisp = $("interests-display");
  const otherCb = $("interest-other-cb");
  const otherWrap = $("interest-other-wrap");

  if (intHdr) {
    intHdr.addEventListener("click", (e) => {
      e.stopPropagation();
      intDrop.classList.toggle("show");
    });
    
    document.addEventListener("click", (e) => {
      if (!intDrop.contains(e.target) && !intHdr.contains(e.target)) {
        intDrop.classList.remove("show");
      }
    });

    intDrop.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.addEventListener("change", () => {
        if (cb.id === "interest-other-cb") {
          otherWrap.style.display = cb.checked ? "block" : "none";
        }
        
        const checked = Array.from(intDrop.querySelectorAll('input[type="checkbox"]:checked'))
          .filter(c => c.id !== "interest-other-cb")
          .map(c => c.parentElement.textContent.trim());
          
        if (otherCb.checked) checked.push("Other");

        if (checked.length === 0) {
          intDisp.textContent = "Select interests...";
          intDisp.style.color = "var(--ink-faint)";
        } else {
          intDisp.textContent = checked.join(", ");
          intDisp.style.color = "var(--ink)";
        }
      });
    });
    
    $("interest-other-text").addEventListener("click", e => e.stopPropagation());
  }
}

main().catch((e) => {
  document.body.insertAdjacentHTML("afterbegin", `<p class="auth-error" style="padding:20px">App failed to start: ${esc(e.message)}</p>`);
});
