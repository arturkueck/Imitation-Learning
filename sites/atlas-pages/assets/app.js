/* Beyond the Demonstrated Task - page logic */
(function () {
  const D = window.SITE_DATA || { journal: [], results: {} };
  const R = D.results;
  const { el } = Charts;
  const $ = s => document.querySelector(s);

  /* ---------------- isometric cubes ---------------- */
  const COLORS = {
    blue: ['#9fc4f1', '#2a78d6', '#1c5cab'],
    orange: ['#f7b796', '#eb6834', '#b9471d'],
    aqua: ['#8edcc0', '#1baf7a', '#127e58'],
    ink: ['#d9dde1', '#9aa6b0', '#6f7c87']
  };
  function cube(parent, cx, ground, a, color, opts = {}) {
    const k = 0.866 * a, cy = ground - 1.5 * a;
    const g = el('g', { class: opts.cls || '' }, parent);
    const [top, left, right] = COLORS[color];
    const dash = opts.ghost ? { fill: 'none', stroke: 'var(--accent)', 'stroke-width': 1.6, 'stroke-dasharray': '5 4' } : null;
    const face = (pts, f) => el('polygon', Object.assign({ points: pts.map(p => p.join(',')).join(' '), 'stroke-linejoin': 'round' }, dash || { fill: f, stroke: '#fff', 'stroke-width': 1 }), g);
    face([[cx, cy - a / 2], [cx + k, cy], [cx, cy + a / 2], [cx - k, cy]], top);
    face([[cx - k, cy], [cx, cy + a / 2], [cx, cy + 1.5 * a], [cx - k, cy + a]], left);
    face([[cx + k, cy], [cx, cy + a / 2], [cx, cy + 1.5 * a], [cx + k, cy + a]], right);
    if (opts.ghost) { const t = el('text', { x: cx, y: cy + a * 0.75 + 6, 'text-anchor': 'middle', fill: 'var(--accent)', 'font-size': a * 0.7, 'font-weight': 700, 'font-family': 'var(--serif)' }, g); t.textContent = '?'; }
    return g;
  }
  function txt(parent, x, y, s, attrs = {}) {
    const t = el('text', Object.assign({ x, y, 'text-anchor': 'middle', fill: 'var(--ink-2)', 'font-size': 13, 'font-family': 'var(--sans)' }, attrs), parent); t.textContent = s; return t;
  }

  // logo
  (function () { const g = $('#logo-cubes'); cube(g, 15, 29, 8, 'blue'); cube(g, 15, 21, 8, 'orange'); cube(g, 15, 13, 8, 'ink', { ghost: false }); })();

  // hero
  (function () {
    const s = $('#hero-svg'); const a = 44, G = 236;
    const style = el('style', {}, s);
    style.textContent = '@keyframes bob{0%,100%{transform:translateY(-6px)}50%{transform:translateY(4px)}}.cube-anim{animation:bob 3.2s ease-in-out infinite}';
    // table lines
    el('line', { x1: 40, x2: 220, y1: G + 2, y2: G + 2, stroke: 'var(--line-2)', 'stroke-width': 2 }, s);
    el('line', { x1: 340, x2: 520, y1: G + 2, y2: G + 2, stroke: 'var(--line-2)', 'stroke-width': 2 }, s);
    cube(s, 130, G, a, 'blue'); cube(s, 130, G - a, a, 'orange');
    cube(s, 430, G, a, 'blue'); cube(s, 430, G - a, a, 'orange');
    const g = el('g', { class: 'cube-anim' }, s);
    cube(g, 430, G - 2 * a - 34, a, 'aqua', { ghost: true });
    // gripper
    el('path', { d: `M410 ${G - 4 * a - 34} v-16 h40 v16 M418 ${G - 4 * a - 50} v-14 M442 ${G - 4 * a - 50} v-14 M430 ${G - 4 * a - 64} v-14`, fill: 'none', stroke: 'var(--ink-2)', 'stroke-width': 3, 'stroke-linecap': 'round' }, g);
    // arrow
    el('path', { d: 'M238 150 C 270 130, 300 130, 322 150', fill: 'none', stroke: 'var(--ink)', 'stroke-width': 2, 'marker-end': 'url(#arr)' }, s);
    const defs = el('defs', {}, s); const m = el('marker', { id: 'arr', viewBox: '0 0 10 10', refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse' }, defs);
    el('path', { d: 'M0,0 L10,5 L0,10 z', fill: 'var(--ink)' }, m);
    txt(s, 280, 118, 'own attempts', { 'font-weight': 600, fill: 'var(--ink)' });
    txt(s, 280, 172, 'success / failure', { 'font-size': 12, fill: 'var(--muted)' });
    txt(s, 130, 272, 'DEMONSTRATED', { 'font-family': 'var(--mono)', 'font-size': 12, 'font-weight': 600, 'letter-spacing': '.1em', fill: 'var(--ink)' });
    txt(s, 130, 290, 'two-cube stacking', { 'font-size': 12.5 });
    txt(s, 430, 272, 'ASKED FOR', { 'font-family': 'var(--mono)', 'font-size': 12, 'font-weight': 600, 'letter-spacing': '.1em', fill: 'var(--accent)' });
    txt(s, 430, 290, 'three-cube tower, never shown', { 'font-size': 12.5 });
  })();

  // differences figure
  (function () {
    const s = $('#diff-svg'); const a = 24, G = 150;
    const cols = [
      { x: 105, title: 'Carried higher', sub: 'lift above a 2-cube tower' },
      { x: 310, title: 'Target is a tower', sub: 'not a single cube' },
      { x: 515, title: 'Tower in the way', sub: 'collisions & recovery unseen' }
    ];
    cols.forEach(c => {
      el('line', { x1: c.x - 70, x2: c.x + 70, y1: G + 2, y2: G + 2, stroke: 'var(--line-2)', 'stroke-width': 1.5 }, s);
      txt(s, c.x, G + 26, c.title, { 'font-weight': 600, fill: 'var(--ink)', 'font-size': 14 });
      txt(s, c.x, G + 44, c.sub, { 'font-size': 12, fill: 'var(--muted)' });
    });
    // 1: height arrow
    cube(s, 95, G, a, 'blue'); cube(s, 95, G - a, a, 'orange'); cube(s, 95, G - 2 * a - 22, a, 'aqua', { ghost: true });
    el('path', { d: `M150 ${G} V ${G - 3 * a - 30}`, stroke: 'var(--accent)', 'stroke-width': 2, 'marker-end': 'url(#arr2)', fill: 'none' }, s);
    const defs = el('defs', {}, s); const m = el('marker', { id: 'arr2', viewBox: '0 0 10 10', refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: 'auto' }, defs);
    el('path', { d: 'M0,0 L10,5 L0,10 z', fill: 'var(--accent)' }, m);
    // 2: target outline on stack
    cube(s, 310, G, a, 'blue'); cube(s, 310, G - a, a, 'orange');
    el('ellipse', { cx: 310, cy: G - 2.5 * a, rx: 30, ry: 15, fill: 'none', stroke: 'var(--accent)', 'stroke-width': 2, 'stroke-dasharray': '4 3' }, s);
    // 3: carrying cube next to tower
    cube(s, 490, G, a, 'blue'); cube(s, 490, G - a, a, 'orange');
    cube(s, 548, G - 22, a, 'aqua');
    el('path', { d: `M528 ${G - 40} q -10 -6 -16 -2`, stroke: 'var(--bad)', 'stroke-width': 2, fill: 'none' }, s);
    txt(s, 530, G - 76, '⚡', { 'font-size': 16, fill: 'var(--bad)' });
  })();

  /* ---------------- compound calculator ---------------- */
  (function () {
    const p = $('#p'), n = $('#n');
    const upd = () => {
      const pv = +p.value / 100, nv = +n.value, v = Math.pow(pv, nv) * 100;
      $('#p-out').textContent = Charts.fmtPct(+p.value);
      $('#n-out').textContent = nv;
      $('#calc-out').textContent = Charts.fmtPct(Math.round(v * 10) / 10);
      $('#calc-text').textContent = `of ${nv}-step tasks complete when each step succeeds ${Charts.fmtPct(+p.value)} of the time.`;
      Charts.compound($('#compound-chart'), pv, nv);
    };
    p.addEventListener('input', upd); n.addEventListener('input', upd); upd();
  })();

  /* ---------------- stages ---------------- */
  (function () {
    const st = [['Approach', 'move above cube'], ['Descend', 'lower to grasp'], ['Close', 'close gripper'], ['Lift', 'raise cube'], ['Travel', 'carry to tower'], ['Open', 'release'], ['Retreat', 'clear the tower']];
    $('#stages').innerHTML = '<div style="flex-basis:100%;font:600 12px var(--mono);color:var(--muted);letter-spacing:.08em">SECOND PLACEMENT (CUBE 3 → ON TOWER)</div>' +
      st.map((s, i) => `<div class="stage${i < 3 ? ' hot' : ''}"${i === 1 || i === 2 ? ' style="--x:0"' : ''}><b>${s[0]}</b><small>${s[1]}</small></div>`).join('');
    // show label only once
    document.querySelectorAll('#stages .stage.hot').forEach((e, i) => { if (i) e.classList.add('nolabel'); });
    const css = document.createElement('style'); css.textContent = '.stage.nolabel::after{display:none}'; document.head.appendChild(css);
  })();

  /* ---------------- flow diagram ---------------- */
  (function () {
    const s = $('#flow-svg');
    const defs = el('defs', {}, s); const m = el('marker', { id: 'arr3', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto' }, defs);
    el('path', { d: 'M0,0 L10,5 L0,10 z', fill: 'var(--ink-2)' }, m);
    const box = (x, y, w, h, title, sub, stroke = 'var(--line-2)', fill = 'var(--card)') => {
      el('rect', { x, y, width: w, height: h, rx: 10, fill, stroke, 'stroke-width': 1.5 }, s);
      txt(s, x + w / 2, y + h / 2 - (sub ? 3 : -5), title, { 'font-weight': 600, fill: 'var(--ink)', 'font-size': w < 150 ? 13 : 14.5 });
      if (sub) txt(s, x + w / 2, y + h / 2 + 15, sub, { 'font-size': 12, fill: 'var(--muted)' });
    };
    const arrow = d => el('path', { d, fill: 'none', stroke: 'var(--ink-2)', 'stroke-width': 1.6, 'marker-end': 'url(#arr3)' }, s);
    box(10, 120, 150, 60, 'Two-cube demos', 'scripted expert');
    box(210, 120, 140, 60, 'BC policy', 'per-stage networks', 'var(--ink)');
    arrow('M160 150 H 206');
    const ys = [30, 120, 210];
    box(560, ys[0], 210, 60, 'BC (unchanged)', 'reference', 'var(--base)');
    box(560, ys[1], 210, 60, 'Actor–Critic · new critic', 'critic starts untrained', 'var(--s2)');
    box(560, ys[2], 210, 60, 'Actor–Critic · IL-informed', 'critic pretrained', 'var(--s1)');
    box(392, ys[2] + 4, 136, 52, 'Critic pretraining', 'on BC attempts', 'var(--s1)', '#eef4fc');
    arrow(`M350 140 C 380 140, 380 ${ys[0] + 30}, 556 ${ys[0] + 30}`);
    arrow(`M350 150 H 556`);
    arrow(`M350 160 C 372 160, 372 ${ys[2] + 30}, 388 ${ys[2] + 30}`);
    arrow(`M528 ${ys[2] + 30} H 556`);
    el('rect', { x: 820, y: 100, width: 170, height: 100, rx: 10, fill: '#fdf4f5', stroke: 'var(--accent)', 'stroke-width': 1.5 }, s);
    txt(s, 905, 140, 'Same test scenes', { 'font-weight': 600, fill: 'var(--ink)', 'font-size': 14.5 });
    txt(s, 905, 165, 'normal · challenging', { 'font-size': 12, fill: 'var(--muted)' });
    txt(s, 905, 182, '+ two-cube check', { 'font-size': 12, fill: 'var(--muted)' });
    ys.forEach(y => arrow(`M770 ${y + 30} C 795 ${y + 30}, 795 150, 816 150`));
    txt(s, 665, 292, 'equal attempt budget for both actor–critic arms', { 'font-size': 12, fill: 'var(--muted)', 'font-style': 'italic' });
  })();

  /* ---------------- evidence chain ---------------- */
  const ARM = { A: { label: 'A · phase-balanced', color: 'var(--base)' }, B: { label: 'B · mixed order', color: 'var(--s1)' }, C: { label: 'C · ordered X→XY→XYZ', color: 'var(--s2)' } };
  const sum = (arr) => arr.reduce((a, [s, n]) => [a[0] + s, a[1] + n], [0, 0]);
  const chain = [
    {
      id: 'BC-002', title: 'Demonstration order', result: 'No consistent gain', status: 'refuted',
      headline: 'Does training easy-to-hard (curriculum) help?',
      body: 'Three BC variants were trained for 30,000 updates. B and C see exactly the same batches, only in a different order, so B vs C isolates ordering. Each model was tested on 100 new three-cube scenes.',
      chart: c => {
        const rows = ['seed1', 'seed2', 'seed3'].map((sd, i) => ({ label: 'Seed ' + (i + 1), values: { A: R.abc.A[sd].three, B: R.abc.B[sd].three, C: R.abc.C[sd].three } }));
        Charts.dots(c, rows, ['A', 'B', 'C'].map(k => ({ key: k, ...ARM[k] })), { label: 'Three-cube success per seed for arms A, B, C', domain: [0, 80], ticks: [0, 20, 40, 60, 80] });
      },
      means: 'Ordering is not the lever. The proposal therefore treats two→three cubes as a transfer question and explicitly does not optimize task order.',
      limit: 'C beats B in one of three seeds. Two-cube success stays at 35–39/40 for all arms.'
    },
    {
      id: 'BC-003', title: 'Time-feature fix', result: '+60 successes, 0 losses', status: 'supported',
      headline: 'An execution bug, found and fixed before comparing methods',
      body: 'The policy input contains a phase clock. In long three-cube episodes it ran past the training range. Bounding it at 0.85 required zero optimizer updates and was compared on fresh paired scenes.',
      chart: c => {
        const nice = k => k.replace('mixed_seed', 'Mixed · seed ').replace('curriculum_seed', 'Curriculum · seed ');
        Charts.dumbbell(c, R.clock.map(m => ({ label: nice(m.model), before: m.before, after: m.after, n: m.n, note: `${m.gains} gains · ${m.losses} losses` })), { beforeLabel: 'Original clock', afterLabel: 'Bounded clock', label: 'Three-cube success before and after bounding the clock feature' });
      },
      means: 'All later comparisons, including the critic pipeline, use the corrected clock - so measured differences come from learning, not from this artifact.',
      limit: `${R.clockHeadline.pairs} paired episodes, ${R.clockHeadline.negative_pairs} two-cube controls unchanged.`
    },
    {
      id: 'BC-004', title: 'Where it fails', result: 'Second approach is the bottleneck', status: 'diagnosis',
      headline: 'Letting the expert take over one stage at a time',
      body: 'In paired runs the programmed expert replaced exactly one stage of the second grasp, then BC continued. No learning happens here - it only locates the problem.',
      chart: c => {
        const a = R.ablation; const L = { control: 'BC alone', close: 'Expert: close only', descend: 'Expert: descend only', approach: 'Expert: approach only', full_grasp: 'Expert: full grasp' };
        Charts.hbars(c, ['control', 'close', 'descend', 'approach', 'full_grasp'].map(k => ({ label: L[k], s: a[k].success[0], n: a[k].success[1], color: k === 'control' ? 'var(--base)' : k === 'approach' || k === 'full_grasp' ? 'var(--s2)' : '#f2a07d', emph: k === 'approach', tip: `${a[k].gains} gains · ${a[k].losses} losses vs BC` })), { label: 'Full three-cube success with single-stage expert takeover', padL: 180 });
      },
      means: 'Fixing only the approach to the second grasp recovers as much as fixing the whole grasp. This is the situation the project wants the robot to learn from its own attempts - without the expert.',
      limit: 'Each expert takeover replaces action and stage-completion together. Expert help is diagnostic only and is excluded from the main study.'
    },
    {
      id: 'BC-005', title: 'Targeted corrections', result: '118/150 vs 85/150', status: 'supported',
      headline: 'Can BC learn the fix from expert corrections?',
      body: `New expert corrections were collected from the second-approach states that BC actually reached (${R.dataset.train_frames.toLocaleString('en')} training frames). Actions and stage completion were learned in separate copies (5,000 updates each) and tested on 50 fresh scenes × 3 models.`,
      chart: c => {
        const C = R.correction; const L = { baseline: 'Original BC (B)', completion: 'New completion only', replay: 'Replay (more updates)', action: 'New actions only', combined: 'Actions + completion' };
        Charts.hbars(c, ['baseline', 'completion', 'replay', 'action', 'combined'].map(k => ({ label: L[k], s: C[k].total[0], n: C[k].total[1], color: k === 'baseline' ? 'var(--base)' : k === 'combined' ? 'var(--s1)' : '#86b6ef', emph: k === 'combined', tip: 'Per seed: ' + C[k].perSeed.map(p => p.join('/')).join(' · ') })), { label: 'Confirmation success of correction variants', padL: 180 });
      },
      means: 'Data from the states where BC fails helps a lot - but it needs an expert. The proposal asks whether success/failure of the robot\'s own attempts can play that role instead.',
      limit: 'A follow-up (BC-006) found no extra benefit from where corrections were collected: targeted 359/450 vs standard 362/450. 150 model-scene pairs share 50 scenes.'
    },
    {
      id: 'AC-001', title: 'First critic trial', result: '47/60 → 0/60', status: 'refuted',
      headline: 'The main risk, observed early',
      body: 'A critic pretrained on IL rollouts passed its accuracy gate. But the actor was then updated online without a limit on how far it may move from the BC behavior.',
      chart: c => {
        Charts.hbars(c, [{ label: 'Before online updates', s: 47, n: 60, color: 'var(--base)' }, { label: 'After (every arm)', s: 0, n: 60, color: 'var(--bad)', emph: true, tip: 'All arms collapsed to zero' }], { label: 'Development success before and after unconstrained actor-critic updates', padL: 180 });
      },
      means: 'An accurate critic is not enough. The proposal adds an AWAC-style limit on policy change and checks the critic separately before it may steer the actor.',
      limit: 'Three paired parents on 20 shared development scenes, repeated.'
    }
  ];
  (function () {
    const list = $('#chain-list'), panels = $('#chain-panels');
    chain.forEach((c, i) => {
      const li = document.createElement('li');
      li.innerHTML = `<button role="tab" id="tab-${i}" aria-controls="panel-${i}" aria-selected="${i === 0}"><span class="n">0${i + 1}</span><span class="t">${c.title}<span class="r">${c.result}</span></span></button>`;
      list.appendChild(li);
      const p = document.createElement('div'); p.className = 'chain-panel card'; p.id = 'panel-' + i; p.setAttribute('role', 'tabpanel'); p.setAttribute('aria-labelledby', 'tab-' + i); p.hidden = i !== 0;
      p.innerHTML = `<div style="display:flex;gap:10px;align-items:center;margin-bottom:10px"><span class="chip ${c.status}">${({ supported: 'Supported', refuted: 'Not supported', diagnosis: 'Diagnosis' })[c.status]}</span><span class="mono" style="font-size:12.5px;color:var(--muted)">${c.id}</span></div>
        <h3>${c.headline}</h3><p style="color:var(--ink-2)">${c.body}</p><div class="chart" id="chain-chart-${i}"></div>
        <div class="means"><b>For the proposal</b><span>${c.means}</span></div><p class="limit">${c.limit}</p>
        <div class="chain-nav">${i ? `<button class="btn ghost" data-go="${i - 1}">← ${chain[i - 1].title}</button>` : '<span></span>'}${i < chain.length - 1 ? `<button class="btn primary" data-go="${i + 1}">${chain[i + 1].title} →</button>` : '<a class="btn primary" href="#now">Current status →</a>'}</div>`;
      panels.appendChild(p);
    });
    const drawn = new Set();
    const select = i => {
      list.querySelectorAll('button').forEach((b, j) => b.setAttribute('aria-selected', j === i));
      panels.querySelectorAll('.chain-panel').forEach((p, j) => p.hidden = j !== i);
      if (!drawn.has(i)) { chain[i].chart($('#chain-chart-' + i)); drawn.add(i); }
    };
    list.addEventListener('click', e => { const b = e.target.closest('button'); if (b) select([...list.querySelectorAll('button')].indexOf(b)); });
    list.addEventListener('keydown', e => {
      const btns = [...list.querySelectorAll('button')], i = btns.indexOf(document.activeElement);
      if (i < 0) return; const d = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? 1 : e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? -1 : 0;
      if (d) { e.preventDefault(); const j = (i + d + btns.length) % btns.length; btns[j].focus(); select(j); }
    });
    panels.addEventListener('click', e => { const b = e.target.closest('[data-go]'); if (b) { select(+b.dataset.go); $('#evidence').scrollIntoView({ behavior: 'smooth' }); } });
    select(0);
  })();

  /* ---------------- status track ---------------- */
  (function () {
    const J = (id, first) => { const m = D.journal.filter(j => j.id === id); return (first ? m[0] : m[m.length - 1]) || {}; };
    const items = [
      { id: 'AC-002', cls: 'done', icon: '✓', title: 'Difficulty calibration', chip: ['diagnosis', 'Diagnosis'], text: 'Long horizontal carry distances define the challenging panel: on 100 calibration families the longest third was weakest for every parent (103/300 overall). Thresholds frozen.' },
      { id: 'AC-003', first: true, cls: 'done', icon: '✓', title: 'Pilot protocol recorded', chip: ['documented', 'Documented'], text: 'Paired BC parents, separate scene panels, fixed critic and smoke-test gates written down before any data was collected.' },
      { id: 'AC-004', cls: 'done', icon: '✓', title: 'N2-1 · Critic data collected', chip: ['passed', 'Gate passed'], text: '900/900 episodes, 325 successes, 575 failures, 684,709 transitions, zero policy updates.' },
      { id: 'AC-005', cls: 'done', icon: '✓', title: 'N2-2 · Critic validated', chip: ['passed', 'Gate passed'], text: 'All three critics beat the phase-only baseline on regular validation (AUC 0.853 / 0.886 / 0.817). On the difficult panel, parent 3\'s interval includes zero.' },
      { id: 'AC-006', cls: 'stopped', icon: '✕', title: 'N2-3 · Constrained actor–critic smoke test', chip: ['stopped', 'Technical stop'], text: 'δ_max = 0.05: 6/6 runs leave the allowed Q range. Drift, sample size and lost-success gates were met (2 of 3 allowed lost parent successes).' },
      { id: 'AC-003', cls: 'paused', icon: '❚❚', title: 'Pilot decision', chip: ['paused', 'Paused'], text: 'Steps N2-4 and N3-1 open; test families remain closed until the pilot path is cleared.' },
      { id: '', cls: 'todo', icon: '', title: 'Main comparison & test-scene evaluation', chip: ['todo', 'Not started'], text: 'BC vs AC-new vs AC-IL on identical test scenes, normal and challenging panels reported separately.' }
    ];
    $('#track').innerHTML = items.map(it => {
      const j = it.id ? J(it.id, it.first) : {};
      return `<li class="${it.cls}"><span class="dot">${it.icon}</span><h4>${it.title} <span class="chip ${it.chip[0]}">${it.chip[1]}</span></h4><p>${it.text}</p>${it.id ? `<div class="meta">${it.id}${j.when ? ' · ' + j.when : ''}</div>` : ''}</li>`;
    }).join('');
    Charts.split($('#critic-data-chart'), [{ label: 'Tower stands (success)', v: 325, color: 'var(--s3)', short: 'successes' }, { label: 'Failure', v: 575, color: 'var(--base)', short: 'failures' }], { label: '325 of 900 critic-data episodes succeeded' });
  })();

  /* ---------------- gantt ---------------- */
  (function () {
    const rows = [
      ['Define test conditions', 0.04, 0.96, false, ['inprog', 'In progress']],
      ['Critic data and pilot runs', 0.54, 1.96, false, ['paused', 'Paused']],
      ['Fix limits and number of runs', 1.54, 2.46, false, ['blocked', 'Blocked']],
      ['Main comparison runs', 2.04, 3.96, false, ['todo', 'Not started']],
      ['Evaluate on test scenes', 4.04, 4.96, false, ['todo', 'Not started']],
      ['Vision and real-robot transfer', 3.04, 4.96, true, ['todo', 'Groundwork']],
      ['Write, revise and submit', 3.04, 5.96, false, ['todo', 'Not started']]
    ];
    const ms = [0.5, 1.5, 3.5, 4.5, 5.5];
    const halves = ['I', 'II', 'I', 'II', 'I', 'II'];
    let h = `<div class="g2"><div class="gl gh">Work package</div><div class="gr gh"><div class="gmonths">${[1, 2, 3].map(m => `<span>Month ${m}</span>`).join('')}</div><div class="ghalves">${halves.map(x => `<span>${x}</span>`).join('')}</div></div>`;
    rows.forEach(r => {
      h += `<div class="gl"><span>${r[0]}</span><span class="chip ${r[4][0]}">${r[4][1]}</span></div><div class="gr"><div class="gtrack"><span class="gbar${r[3] ? ' sec' : ''}" style="left:${r[1] / 6 * 100}%;width:${(r[2] - r[1]) / 6 * 100}%"></span></div></div>`;
    });
    h += `<div class="gl gms">Milestones</div><div class="gr"><div class="gtrack">${ms.map((x, i) => `<span class="gmark" style="left:${x / 6 * 100}%">M${i + 1}</span>`).join('')}</div></div></div>`;
    $('#gantt').innerHTML = h;
    const css = document.createElement('style');
    css.textContent = `.g2{display:grid;grid-template-columns:minmax(200px,300px) 1fr;border:1px solid var(--line);border-radius:var(--radius);background:var(--card);overflow:hidden;font-size:14px}
    .g2>div{border-bottom:1px solid var(--line);min-height:46px;display:flex;align-items:center}
    .gl{padding:8px 14px;gap:8px;justify-content:space-between;border-right:1px solid var(--line)}
    .gl .chip{font-size:11px;padding:2px 8px}
    .gh{background:var(--paper-2);font:600 12px var(--mono);color:var(--muted);flex-direction:column;align-items:stretch!important;justify-content:center}
    .gl.gh{flex-direction:row;align-items:center!important;justify-content:flex-start}
    .gmonths,.ghalves{display:grid;grid-template-columns:repeat(3,1fr);text-align:center;padding:3px 0}.ghalves{grid-template-columns:repeat(6,1fr);font-weight:400}
    .gr{padding:0;position:relative;background:repeating-linear-gradient(90deg,transparent 0,transparent calc(100%/6 - 1px),var(--line) calc(100%/6 - 1px),var(--line) calc(100%/6))}
    .gr.gh{background:var(--paper-2)}
    .gtrack{position:relative;width:100%;height:46px}
    .gbar{position:absolute;top:15px;height:16px;border-radius:5px;background:var(--ink)}.gbar.sec{background:#a7b3bd}
    .gmark{position:absolute;top:12px;transform:translateX(-50%);font:700 12px var(--mono);color:#fff;background:var(--accent);padding:3px 7px;border-radius:5px}
    .gms{font-weight:600}
    .g2>div:nth-last-child(-n+2){border-bottom:0}
    @media(max-width:700px){.g2{grid-template-columns:140px 1fr;font-size:12px}.gl .chip{display:none}}`;
    document.head.appendChild(css);
    const M = [
      ['M1', 'Protocol fixed', 'Month 1, midpoint', 'Scene sets, difficulty classes, success criterion and budgets defined; BC policy reproduced.', ['inprog', 'In progress']],
      ['M2', 'Pilot complete', 'End of month 1', 'Three runs per variant; fixes the policy-change limit, smallest relevant effect and number of runs.', ['blocked', 'Blocked by AC-006']],
      ['M3', 'Models frozen', 'End of month 2', 'Main comparison done, critic checked separately, final models chosen on validation scenes only.', ['todo', 'Not started']],
      ['M4', 'Evaluation complete', 'Month 3, midpoint', 'Test scenes run once; normal, challenging and two-cube results per run, with attempt and compute cost.', ['todo', 'Not started']],
      ['M5', 'Project submitted', 'End of month 3', 'Report, experiment protocol and reproduction scripts.', ['todo', 'Not started']]
    ];
    $('#milestones').innerHTML = M.map(m => `<div class="milestone"><div class="id">${m[0]} · ${m[2]}</div><h4>${m[1]}</h4><p>${m[3]}</p><span class="chip ${m[4][0]}">${m[4][1]}</span></div>`).join('');
  })();

  /* ---------------- journal ---------------- */
  (function () {
    const J = D.journal;
    const STATUS_COLOR = { supported: '#0f7b3f', passed: '#5fb383', partial: '#c98500', running: '#e0b44d', paused: '#e0b44d', refuted: '#b42318', stopped: '#e3807a', diagnosis: '#2a5fa8', unclear: '#2a5fa8', planned: '#c9c2b2', documented: '#c9c2b2', other: '#c9c2b2' };
    const STATUS_NAME = { supported: 'Supported', partial: 'Partly supported', refuted: 'Not supported', diagnosis: 'Diagnosis', passed: 'Gate passed', stopped: 'Stopped', paused: 'Paused', running: 'Started', planned: 'Planned', documented: 'Documented', unclear: 'Inconclusive', other: 'Other' };
    const fams = ['All', ...new Set(J.map(j => j.family))];
    const stats = ['all', ...new Set(J.map(j => j.status))];
    let fam = 'All', st = 'all', q = '';
    $('#ffamily').innerHTML = fams.map(f => `<button class="fbtn" data-f="${f}" aria-pressed="${f === 'All'}">${f}${f !== 'All' ? ` <span style="opacity:.6">${J.filter(j => j.family === f).length}</span>` : ''}</button>`).join('');
    $('#fstatus').innerHTML = stats.map(s => `<button class="fbtn" data-s="${s}" aria-pressed="${s === 'all'}">${s === 'all' ? 'Any outcome' : `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${STATUS_COLOR[s]};margin-right:6px"></span>` + STATUS_NAME[s]}</button>`).join('');
    const esc = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
    const md = s => esc(s).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    const render = () => {
      const ql = q.toLowerCase();
      const list = J.map((j, i) => ({ j, i })).filter(({ j }) => (fam === 'All' || j.family === fam) && (st === 'all' || j.status === st) &&
        (!ql || [j.id, j.topic, j.question, j.test, j.result, j.decision].join(' ').toLowerCase().includes(ql)));
      $('#jsummary').textContent = `${list.length} of ${J.length} entries · newest first`;
      list.reverse();
      $('#jstrip').innerHTML = J.map((j, i) => `<span data-i="${i}" style="background:${STATUS_COLOR[j.status]};opacity:${list.some(l => l.i === i) ? 1 : .18}" title="${j.date} · ${j.id} · ${STATUS_NAME[j.status]}"></span>`).join('');
      $('#jlist').innerHTML = list.map(({ j, i }) => `<details class="entry" id="j-${i}"><summary><span class="d">${j.date}</span><span class="id">${j.id}</span><span class="q">${md(j.question)}<small>${md(j.topic)} · ${j.family}</small></span><span class="chip ${j.status}">${j.statusLabel}</span></summary>
        <div class="body"><div><h5>Test / criterion</h5>${md(j.test)}</div><div><h5>Result</h5>${md(j.result)}</div><div><h5>Decision / next step</h5>${md(j.decision)}</div>
        <div class="ev"><h5>Evidence</h5>${j.evidence.length ? j.evidence.map(e => e.url ? `<a href="${e.url}" target="_blank" rel="noopener">${esc(e.label)}</a> <code>${esc(e.path)}</code>` : `<code>${esc(e.path)}</code>`).join(' ') : '—'} <span style="margin-left:6px">${esc(j.when)}</span></div></div></details>`).join('');
    };
    $('#ffamily').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; fam = b.dataset.f; $('#ffamily').querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b)); render(); });
    $('#fstatus').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; st = b.dataset.s; $('#fstatus').querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b)); render(); });
    $('#jsearch').addEventListener('input', e => { q = e.target.value; render(); });
    $('#jstrip').addEventListener('click', e => { const sp = e.target.closest('span'); if (!sp) return; const d = document.getElementById('j-' + sp.dataset.i); if (d) { d.open = true; d.scrollIntoView({ behavior: 'smooth', block: 'center' }); } });
    render();
  })();

  /* ---------------- references ---------------- */
  (function () {
    const refs = [
      ['DAgger', 'Ross, Gordon & Bagnell · AISTATS 2011', 'https://proceedings.mlr.press/v15/ross11a.html', 'Imitation drifts into states the demos never covered; fixed by letting an expert label the states the robot actually reaches.', 'Gap: needs an expert for the target task'],
      ['DeCo', 'Chen et al. · arXiv 2025', 'https://arxiv.org/abs/2505.00527', 'Splits demonstrated tasks into reusable skills and recombines them for longer, never-demonstrated tasks.', 'Gap: skills are not improved when they fail'],
      ['AWAC', 'Nair et al. · arXiv 2020', 'https://arxiv.org/abs/2006.09359', 'Starts from existing data, continues with own attempts, and keeps the actor close to the data while it improves.', 'Used: the policy-change limit'],
      ['ResFiT', 'Ankile et al. · ICLR 2026', 'https://arxiv.org/abs/2509.19301', 'Keeps a BC policy fixed and learns small residual corrections from success/failure of own attempts.', 'Related: sparse-reward finetuning of BC'],
      ['Actor–Critic Pretraining for PPO', 'Kernbach et al. · arXiv 2026', 'https://arxiv.org/abs/2602.23804', 'Trains the critic on the BC policy\'s own attempts before RL; fewer attempts needed across 15 simulated tasks.', 'Open: multi-step, end-only reward, undemonstrated task']
    ];
    $('#refs').innerHTML = refs.map((r, i) => `<article class="ref"><div class="n">[${i + 1}]</div><h4><a href="${r[2]}" target="_blank" rel="noopener">${r[0]}</a></h4><div class="by">${r[1]}</div><p>${r[3]}</p><span class="role">${r[4]}</span></article>`).join('');
  })();

  /* ---------------- nav, progress, reveal, lightbox ---------------- */
  (function () {
    const links = [...document.querySelectorAll('.steps-nav a')];
    const secs = links.map(a => document.querySelector(a.getAttribute('href')));
    const onScroll = () => {
      const y = window.scrollY + 120; let cur = -1;
      secs.forEach((s, i) => { if (s.offsetTop <= y) cur = i; });
      links.forEach((a, i) => { a.classList.toggle('active', i === cur); a.classList.toggle('done', i < cur); });
      const h = document.documentElement; $('#progress').style.width = (100 * h.scrollTop / (h.scrollHeight - h.clientHeight)) + '%';
    };
    window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .08 });
    document.querySelectorAll('.reveal').forEach(e => io.observe(e));
    const lb = $('#lightbox');
    document.querySelectorAll('.figs img').forEach(img => img.addEventListener('click', () => { lb.querySelector('img').src = img.src; lb.querySelector('img').alt = img.alt; lb.classList.add('open'); }));
    lb.addEventListener('click', () => lb.classList.remove('open'));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') lb.classList.remove('open'); });
    $('#generated').textContent = `Data generated ${D.generated || '–'} from the project repository`;
  })();
})();
