/* Replays real three-cube test episodes from simulator traces (data/replays.js) on a canvas. */
(function () {
  const R = window.REPLAYS; const root = document.getElementById('replay');
  if (!R || !root) return;
  const PHASES = ['Approach', 'Descend', 'Close', 'Lift', 'Travel', 'Lower', 'Release'];
  const PHASE_COL = ['#9ec5f4', '#5598e7', '#256abf', '#f7b796', '#eb6834', '#8edcc0', '#1baf7a'];
  const CUBE = [['#9fc4f1', '#2a78d6', '#1c5cab'], ['#f7b796', '#eb6834', '#b9471d'], ['#8edcc0', '#1baf7a', '#127e58']];
  const HALF = 20, TABLE_Z = HALF * -1; // cube half size (mm); z is shifted so the table top is 0
  const canvas = root.querySelector('canvas'), ctx = canvas.getContext('2d');
  const strip = root.querySelector('.rp-strip'), sctx = strip.getContext('2d');
  const $ = s => root.querySelector(s);
  let ep, t = 0, playing = false, speed = 2, last = 0, grip = 0, view;

  // ---- projection (axonometric, viewer at +x/+y, above) ----
  function setupView() {
    const W = canvas.width, H = canvas.height;
    let xs = [], ys = [];
    const push = (x, y, z) => { const p = raw(x, y, z); xs.push(p[0]); ys.push(p[1]); };
    for (const [x, y] of [[-260, -260], [260, -260], [-260, 260], [260, 260]]) push(x, y, 0);
    for (let i = 0; i < ep.eef.length; i += 5) { const e = ep.eef[i]; push(e[0], e[1], e[2] - ep.z0 + 60); }
    const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys);
    const k = Math.min((W - 60) / (maxx - minx), (H - 60) / (maxy - miny));
    view = { k, ox: W / 2 - k * (minx + maxx) / 2, oy: H / 2 - k * (miny + maxy) / 2 };
  }
  function raw(x, y, z) { return [(x - y) * 0.866, (x + y) * 0.5 - z]; }
  function P(x, y, z) { const r = raw(x, y, z); return [view.ox + view.k * r[0], view.oy + view.k * r[1]]; }
  function poly(pts, fill, stroke) {
    ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath();
    if (fill) { ctx.fillStyle = fill; ctx.fill(); } if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.stroke(); }
  }
  function box(cx, cy, cz, h, cols) { // axis-aligned cube centred at (cx,cy,cz)
    const a = h, x0 = cx - a, x1 = cx + a, y0 = cy - a, y1 = cy + a, z0 = cz - a, z1 = cz + a;
    poly([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], cols[0], 'rgba(255,255,255,.7)');
    poly([P(x1, y0, z1), P(x1, y1, z1), P(x1, y1, z0), P(x1, y0, z0)], cols[2], 'rgba(255,255,255,.5)');
    poly([P(x0, y1, z1), P(x1, y1, z1), P(x1, y1, z0), P(x0, y1, z0)], cols[1], 'rgba(255,255,255,.5)');
  }
  function shadow(x, y, z, r, a) {
    const p = P(x, y, 0), s = Math.max(.25, 1 - z / 400);
    ctx.save(); ctx.globalAlpha = a * s; ctx.fillStyle = '#14212b';
    ctx.beginPath(); ctx.ellipse(p[0], p[1], Math.max(1, r * view.k * 1.1), Math.max(1, r * view.k * .6), 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  }

  function draw() {
    const W = canvas.width, H = canvas.height; ctx.clearRect(0, 0, W, H);
    // table
    poly([P(-260, -260, 0), P(260, -260, 0), P(260, 260, 0), P(-260, 260, 0)], '#efece4', '#d6d0c2');
    ctx.strokeStyle = 'rgba(0,0,0,.05)';
    for (let g = -200; g <= 200; g += 50) { let a = P(g, -260, 0), b = P(g, 260, 0); ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); a = P(-260, g, 0); b = P(260, g, 0); ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
    const c = ep.cubes[t], e = ep.eef[t], z0 = ep.z0;
    // eef trail
    ctx.strokeStyle = 'rgba(190,30,60,.35)'; ctx.lineWidth = 1.5; ctx.beginPath();
    for (let i = Math.max(0, t - 80); i <= t; i++) { const q = ep.eef[i], p = P(q[0], q[1], q[2] - z0); i === Math.max(0, t - 80) ? ctx.moveTo(...p) : ctx.lineTo(...p); }
    ctx.stroke();
    // shadows
    for (let i = 0; i < 3; i++) shadow(c[3 * i], c[3 * i + 1], c[3 * i + 2] - z0 + HALF, HALF, .18);
    shadow(e[0], e[1], e[2] - z0, 14, .14);
    // painter's order: cubes and gripper sorted by depth
    const items = [0, 1, 2].map(i => ({ d: c[3 * i] + c[3 * i + 1] + (c[3 * i + 2] - z0) * .2, f: () => box(c[3 * i], c[3 * i + 1], c[3 * i + 2] - z0 + HALF - HALF, HALF, CUBE[i]) }));
    items.push({ d: e[0] + e[1] + 25, f: () => gripper(e[0], e[1], e[2] - z0) });
    items.sort((a, b) => a.d - b.d).forEach(it => it.f());
  }
  function gripper(x, y, z) {
    const target = ep.grip[t] > 0 ? 1 : 0; grip += (target - grip) * .35;
    const held = ep.held[t].some(Boolean);
    const gap = held ? HALF + 2 : 40 - 36 * grip; // mm between finger centres / 2
    const fz = z - 6; // end-effector point sits between the fingertips
    ctx.lineCap = 'round';
    // rod
    let a = P(x, y, z + 50), b = P(x, y, z + 300); ctx.strokeStyle = '#6f7c87'; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke();
    // palm
    a = P(x, y - gap - 6, z + 46); b = P(x, y + gap + 6, z + 46); ctx.strokeStyle = '#44505a'; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke();
    // fingers
    ctx.strokeStyle = '#14212b'; ctx.lineWidth = 4;
    for (const s of [-1, 1]) { a = P(x, y + s * gap, z + 46); b = P(x, y + s * gap, fz); ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke(); }
  }

  function drawStrip() {
    const W = strip.width, H = strip.height, n = ep.phase.length; sctx.clearRect(0, 0, W, H);
    for (let i = 0; i < n; i++) { sctx.fillStyle = ep.retreat[i] ? '#c9c2b2' : PHASE_COL[ep.phase[i]]; sctx.fillRect(Math.floor(i / n * W), ep.stage[i] === 1 ? 0 : H / 2, Math.ceil(W / n) + 1, H / 2 - 1); }
    sctx.fillStyle = '#14212b'; sctx.fillRect(Math.round(t / (n - 1) * (W - 2)), 0, 2, H);
  }
  function hud() {
    const st = ep.stage[t], ph = ep.phase[t], held = ep.held[t];
    $('.rp-step').textContent = `step ${t + 1} / ${ep.shown}${ep.shown < ep.steps ? ' (of ' + ep.steps + ')' : ''} · ${(t / 20).toFixed(1)} s`;
    $('.rp-stage').textContent = st === 1 ? 'Placement 1 · orange cube onto blue' : 'Placement 2 · green cube onto the tower';
    $('.rp-phase').innerHTML = ep.retreat[t] ? '<i style="background:#c9c2b2"></i>Retreat (fixed rule)' : `<i style="background:${PHASE_COL[ph]}"></i>${PHASES[ph]}`;
    $('.rp-held').textContent = held.some(Boolean) ? `holding ${['blue', 'orange', 'green'][held.indexOf(1)]} cube` : 'gripper empty';
    const end = t >= ep.shown - 1;
    const o = $('.rp-outcome'); o.hidden = !end; o.className = 'rp-outcome ' + (ep.success ? 'ok' : 'fail');
    o.textContent = ep.success ? '✓ Stable three-cube tower' : '✕ ' + ep.title;
    $('.rp-scrub').value = t;
  }
  function render() { draw(); drawStrip(); hud(); }
  function loop(ts) {
    if (!playing) return;
    if (ts - last >= 50 / speed) { last = ts; if (t < ep.shown - 1) { t++; render(); } else { playing = false; setBtn(); } }
    requestAnimationFrame(loop);
  }
  function setBtn() { $('.rp-play').textContent = playing ? '❚❚ Pause' : (t >= ep.shown - 1 ? '↺ Replay' : '▶ Play'); }
  function load(i) {
    ep = R.episodes[i]; ep.z0 = ep.cubes[0][2] - HALF; // table top
    t = 0; grip = 0; size(); setupView();
    root.querySelectorAll('.rp-ep').forEach((b, j) => b.setAttribute('aria-pressed', j === i));
    $('.rp-note').textContent = ep.note; $('.rp-scrub').max = ep.shown - 1; render();
        playing = true; setBtn(); requestAnimationFrame(loop);
  }

  // ---- UI ----
  root.querySelector('.rp-eps').innerHTML = R.episodes.map((e, i) => `<button class="rp-ep" aria-pressed="false"><b class="${e.success ? 'ok' : 'fail'}">${e.success ? '✓' : '✕'}</b>${e.title}<small>scene ${e.seed}</small></button>`).join('');
  root.querySelectorAll('.rp-ep').forEach((b, i) => b.onclick = () => load(i));
  $('.rp-play').onclick = () => { if (t >= ep.shown - 1) t = 0; playing = !playing; setBtn(); if (playing) requestAnimationFrame(loop); };
  $('.rp-scrub').oninput = e => { t = +e.target.value; playing = false; setBtn(); render(); };
  root.querySelectorAll('.rp-speed button').forEach(b => b.onclick = () => { speed = +b.dataset.s; root.querySelectorAll('.rp-speed button').forEach(x => x.setAttribute('aria-pressed', x === b)); });
  strip.onclick = e => { const r = strip.getBoundingClientRect(); t = Math.round((e.clientX - r.left) / r.width * (ep.shown - 1)); render(); };
  // HiDPI canvas
  function size() {
    const dpr = window.devicePixelRatio || 1, w = canvas.clientWidth || canvas.parentElement.clientWidth || 800;
    canvas.width = w * dpr; canvas.height = w * .62 * dpr; canvas.style.height = w * .62 + 'px';
    strip.width = strip.clientWidth * dpr; strip.height = 18 * dpr;
    if (ep) { setupView(); render(); }
  }
  window.addEventListener('resize', size); size();
  // start when scrolled into view
  let started = false;
  const io = new IntersectionObserver(es => { if (es[0].isIntersecting && !started) { started = true; load(0); } }, { threshold: .3 });
  io.observe(root);
  $('.rp-legend').innerHTML = PHASES.map((p, i) => `<span><i style="background:${PHASE_COL[i]}"></i>${p}</span>`).join('') + '<span><i style="background:#c9c2b2"></i>Retreat</span>';
})();
