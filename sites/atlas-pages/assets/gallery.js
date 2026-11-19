/* Renders video pairs, galleries, the vision charts and the project timeline. */
(function () {
  const M = window.MEDIA, $ = s => document.querySelector(s);
  const MB = (document.body.dataset.base || '') + 'media/';
  const vid = (src, extra = '') => `<video src="${MB}${src}.mp4" poster="${MB}${src}.jpg" muted loop playsinline preload="none" ${extra}></video>`;
  const badge = ok => ok === true ? '<span class="vbadge ok">✓</span>' : ok === false ? '<span class="vbadge fail">✕</span>' : '';

  // play videos only while visible; click toggles
  function wire(root) {
    root.querySelectorAll('video').forEach(v => {
      v.addEventListener('click', () => v.paused ? v.play() : v.pause());
      v.setAttribute('title', 'Click to pause or play');
    });
    const io = new IntersectionObserver(es => es.forEach(e => {
      const v = e.target; if (e.isIntersecting) { v.preload = 'auto'; v.play().catch(() => {}); } else v.pause();
    }), { threshold: .35 });
    root.querySelectorAll('video').forEach(v => io.observe(v));
  }

  // side-by-side pairs with synchronised playback
  const pairs = $('#pairs');
  if (pairs) {
    pairs.innerHTML = M.pairs.map((p, i) => `<article class="pair card">
      <div class="pair-head"><h4>${p.title}</h4><span class="mono">${p.id} · ${p.date}</span></div>
      <div class="pair-grid">
        <figure>${vid(p.left.src, `data-pair="${i}"`)}<figcaption>${badge(p.left.ok)}${p.left.label}<small>${p.left.tag}</small></figcaption></figure>
        <figure>${vid(p.right.src, `data-pair="${i}"`)}<figcaption>${badge(p.right.ok)}${p.right.label}<small>${p.right.tag}</small></figcaption></figure>
      </div><p>${p.text}</p><button class="table-toggle" data-restart="${i}">↺ Restart both from the same frame</button></article>`).join('');
    pairs.addEventListener('click', e => {
      const b = e.target.closest('[data-restart]'); if (!b) return;
      pairs.querySelectorAll(`video[data-pair="${b.dataset.restart}"]`).forEach(v => { v.currentTime = 0; v.play().catch(() => {}); });
    });
    wire(pairs);
  }
  // galleries
  function gallery(el, items) {
    if (!el) return;
    el.innerHTML = items.map(m => `<figure class="vcard">${vid(m.src)}<figcaption>${badge(m.ok)}<b>${m.title}</b><span class="mono">${m.id} · ${m.date}</span><p>${m.text}</p></figcaption></figure>`).join('');
    wire(el);
  }
  gallery($('#robot-gallery'), M.robot);
  gallery($('#vision-gallery'), M.vision);

  // ---------- vision results chart ----------
  const vc = $('#vision-chart');
  if (vc) {
    const rows = [
      { label: 'New scenes, like training · 2 fixed cameras', s: 8852, n: 10000, color: 'var(--s1)', tip: 'mean position error 5.95 mm · object count correct 96.4%' },
      { label: 'New scenes, like training · fixed + hand', s: 9189, n: 10000, color: 'var(--s1)', emph: true, tip: 'mean position error 5.11 mm · object count correct 96.7%' },
      { label: 'Changed cuboid shapes · 2 fixed cameras', s: 2589, n: 10000, color: 'var(--s2)', tip: 'mean position error 17.43 mm · object count correct 60.0%' },
      { label: 'Changed cuboid shapes · fixed + hand', s: 3537, n: 10000, color: 'var(--s2)', tip: 'mean position error 14.92 mm · object count correct 66.5%' }
    ];
    Charts.hbars(vc, rows, { label: 'Share of objects detected and placed within 10 mm', padL: 270, rowH: 40 });
    // replace n-based value labels with percentages
    vc.querySelectorAll('.value-label').forEach((t, i) => t.textContent = (rows[i].s / 100).toFixed(1) + '%');
    const tb = vc.querySelector('table'); if (tb) tb.querySelectorAll('tbody tr').forEach((tr, i) => { tr.children[1].textContent = (rows[i].s / 100).toFixed(1) + '%'; tr.children[2].textContent = 'object share'; });
  }

  // ---------- project timeline ----------
  const tl = $('#timeline');
  if (tl) {
    const tracks = [
      { k: 'base', label: 'Baselines & tasks', color: '#8b877d' },
      { k: 'diag', label: 'Two-cube diagnostics', color: '#6da7ec' },
      { k: 'si', label: 'Self-imitation & phase BC', color: '#eb6834' },
      { k: 'vis', label: 'Vision & cameras', color: '#1baf7a' },
      { k: 'bc', label: 'BC curriculum & corrections', color: '#2a78d6' },
      { k: 'ac', label: 'Critic / actor–critic', color: '#be1e3c' }
    ];
    const E = [ // [date MM-DD, track, name]
      ['09-29', 'base', 'Lift BC + local extension'], ['09-30', 'base', 'Square: BC / RNN / Transformer'], ['09-30', 'base', 'Square multi-view & overnight'], ['09-30', 'base', 'Additional tasks: two/four cubes, handover'], ['09-30', 'base', 'Four-cube night run'], ['09-30', 'diag', 'Robustness suite'],
      ['10-01', 'base', 'Workday baselines'], ['10-01', 'base', 'Diffusion baselines'], ['10-01', 'diag', 'Balance at lift/transport'], ['10-01', 'diag', 'Direct regressor vs diffusion'], ['10-01', 'diag', 'Dynamics features'], ['10-01', 'diag', 'Scheduler follow-up'], ['10-01', 'diag', 'Normalisation 2×2'], ['10-01', 'diag', 'Placement diagnosis'], ['10-01', 'diag', 'Replication & synthesis'], ['10-01', 'diag', 'Switch diagnosis'], ['10-01', 'diag', 'Transport diagnosis'],
      ['10-02', 'diag', 'Diffusion sanity: lift + transport'], ['10-03', 'diag', 'Sanity repeat'], ['10-03', 'diag', 'Causal diagnosis from expert phases'], ['10-04', 'diag', 'Lift dynamics validity (6 h)'], ['10-04', 'diag', 'Overnight diffusion C'],
      ['10-23', 'si', 'Composition: relative inputs'], ['10-23', 'si', 'Phase-based 8 h run'], ['10-23', 'si', 'Self-imitation on own towers'], ['10-23', 'si', 'Five-cube curriculum'], ['10-23', 'si', 'Five-cube proposal'], ['10-24', 'si', 'Transition quality weighting'], ['10-28', 'si', 'Literature: 6 new papers'],
      ['10-31', 'vis', 'Visual cube transfer pilot'], ['11-01', 'vis', 'Vision overnight V1'], ['11-01', 'vis', 'Vision V2: up to 5 objects'], ['11-01', 'vis', 'Vision V3 design'], ['11-01', 'vis', 'Active camera planning'], ['11-02', 'vis', 'V4 paired side views'], ['11-03', 'vis', 'Quality of 3D proposals'], ['11-03', 'vis', 'Edge refinement'],
      ['11-04', 'si', 'Partial self-imitation'], ['11-04', 'si', 'Retreat gate'], ['11-04', 'ac', 'Critic warm-start'], ['11-07', 'ac', 'IL action feasibility'],
      ['11-10', 'bc', 'Ordering curriculum 30k'], ['11-10', 'bc', '60k continuation'], ['11-11', 'bc', 'Fixed completion'], ['11-11', 'bc', 'Completion 10 h'], ['11-12', 'bc', 'Release diagnosis'], ['11-12', 'bc', 'Clock validation'], ['11-12', 'bc', 'A/B/C comparison'], ['11-12', 'bc', 'Phase skill audit'], ['11-13', 'bc', 'Grasp phase ablation'], ['11-13', 'bc', 'Approach correction'],
      ['11-17', 'base', 'Baseline comparability audit'], ['11-17', 'bc', 'Correction budget v1/v2'], ['11-18', 'bc', 'Residual phase diagnosis'], ['11-18', 'bc', 'Completion & placement'], ['11-18', 'bc', 'Selective completion'], ['11-18', 'bc', 'First-grasp clearance'], ['11-18', 'bc', 'First-grasp query'], ['11-19', 'ac', 'Three-cube transfer pipeline']
    ];
    const day = s => { const [m, d] = s.split('-').map(Number); return (m === 9 ? d - 29 : m === 10 ? d + 1 : d + 32); }; // days since 29 Sep
    const max = day('11-21');
    const W = 1000, rowH = 34, padL = 200, top = 26, H = top + tracks.length * rowH + 10;
    const x = d => padL + (W - padL - 10) * d / max;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Timeline of ${E.length} experiment families from late September to November 2026">`;
    [['Oct', day('10-01')], ['15 Oct', day('10-15')], ['Nov', day('11-01')], ['15 Nov', day('11-15')]].forEach(([l, d]) => {
      s += `<line x1="${x(d)}" x2="${x(d)}" y1="${top - 6}" y2="${H - 6}" stroke="var(--line)"/><text x="${x(d)}" y="${top - 12}" text-anchor="middle" font-size="11" fill="var(--muted)">${l}</text>`;
    });
    tracks.forEach((t, i) => {
      const y = top + i * rowH + rowH / 2;
      s += `<text x="${padL - 12}" y="${y + 4}" text-anchor="end" font-size="12.5" fill="var(--ink)">${t.label}</text><line x1="${padL}" x2="${W - 10}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-dasharray="2 4"/>`;
    });
    const seen = {};
    E.forEach(([d, k, name], j) => {
      const i = tracks.findIndex(t => t.k === k), key = d + k; seen[key] = (seen[key] || 0) + 1;
      const y = top + i * rowH + rowH / 2 + (seen[key] % 2 ? -1 : 1) * Math.floor(seen[key] / 2) * 5;
      s += `<circle class="tl-dot" data-j="${j}" cx="${x(day(d)) + (seen[key] - 1) * 3}" cy="${y}" r="5.5" fill="${tracks[i].color}" stroke="var(--card)" stroke-width="1.5"/>`;
    });
    s += '</svg>';
    tl.innerHTML = s;
    tl.querySelectorAll('.tl-dot').forEach(c => { const e = E[+c.dataset.j]; Charts.bindTip(c, `<strong>${e[2]}</strong><br>${new Date('2026-' + e[0]).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })} · ${tracks.find(t => t.k === e[1]).label}`); });
    const cnt = $('#tl-count'); if (cnt) cnt.textContent = E.length;
  }
})();
