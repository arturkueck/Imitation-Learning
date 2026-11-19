/* Minimal SVG chart helpers - no dependencies. Each chart ships a hover tooltip and a table view. */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const tip = () => document.getElementById('tooltip');
  const pct = (a, b) => (100 * a / b);
  const fmtPct = v => (Math.round(v * 10) / 10).toString().replace(/\.0$/, '') + '%';

  function el(tag, attrs = {}, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function svg(container, w, h, label) {
    container.innerHTML = '';
    const s = el('svg', { viewBox: `0 0 ${w} ${h}`, role: 'img', 'aria-label': label || '' });
    container.appendChild(s);
    return s;
  }
  function showTip(html, evt) {
    const t = tip(); t.innerHTML = html; t.classList.add('show');
    const x = Math.min(evt.clientX + 14, window.innerWidth - t.offsetWidth - 10);
    const y = Math.max(evt.clientY - t.offsetHeight - 12, 8);
    t.style.left = x + 'px'; t.style.top = y + 'px';
  }
  function hideTip() { tip().classList.remove('show'); }
  function bindTip(node, html) {
    node.addEventListener('mousemove', e => showTip(typeof html === 'function' ? html() : html, e));
    node.addEventListener('mouseleave', hideTip);
    node.setAttribute('tabindex', '0');
    node.addEventListener('focus', () => { const r = node.getBoundingClientRect(); showTip(typeof html === 'function' ? html() : html, { clientX: r.right, clientY: r.top }); });
    node.addEventListener('blur', hideTip);
  }
  function tableView(container, headers, rows) {
    const btn = document.createElement('button');
    btn.className = 'table-toggle'; btn.type = 'button'; btn.textContent = 'Show data table';
    const t = document.createElement('table'); t.className = 'data'; t.hidden = true;
    t.innerHTML = '<thead><tr>' + headers.map((h, i) => `<th class="${i ? 'r' : ''}">${h}</th>`).join('') + '</tr></thead><tbody>' +
      rows.map(r => '<tr>' + r.map((c, i) => `<td class="${i ? 'r' : ''}">${c}</td>`).join('') + '</tr>').join('') + '</tbody>';
    btn.onclick = () => { t.hidden = !t.hidden; btn.textContent = t.hidden ? 'Show data table' : 'Hide data table'; };
    container.appendChild(btn); container.appendChild(t);
  }
  function legend(container, items) {
    const d = document.createElement('div'); d.className = 'legend';
    d.innerHTML = items.map(i => `<span><i class="${i.dot ? 'dot' : ''}" style="background:${i.color}"></i>${i.label}</span>`).join('');
    container.appendChild(d);
  }
  function xAxis(s, x, y0, y1, ticks, fmt) {
    const g = el('g', { class: 'grid' }, s);
    ticks.forEach(t => {
      el('line', { x1: x(t), x2: x(t), y1: y0, y2: y1 }, g);
      const tx = el('text', { x: x(t), y: y1 + 16, 'text-anchor': 'middle', class: 'axis' }, s); tx.textContent = fmt(t);
      tx.setAttribute('fill', 'var(--muted)'); tx.style.fontSize = '11.5px';
    });
  }

  /* Horizontal bars: items {label, s, n, color, tip, emph} - value is successes/n as % */
  function hbars(container, items, opts = {}) {
    const W = 640, rowH = opts.rowH || 38, padL = opts.padL || 170, padR = 70, top = 8;
    const H = top + items.length * rowH + 28;
    const wrap = document.createElement('div'); container.innerHTML = ''; container.appendChild(wrap);
    if (opts.legend) legend(container, opts.legend);
    const s = svg(wrap, W, H, opts.label);
    container.appendChild(wrap);
    const max = opts.max || 100;
    const x = v => padL + (W - padL - padR) * v / max;
    xAxis(s, x, top, top + items.length * rowH, opts.ticks || [0, 25, 50, 75, 100], v => v + '%');
    items.forEach((it, i) => {
      const y = top + i * rowH + 8, h = rowH - 16, v = pct(it.s, it.n);
      const lab = el('text', { x: padL - 12, y: y + h / 2 + 4, 'text-anchor': 'end' }, s);
      lab.textContent = it.label; if (it.emph) lab.style.fontWeight = 700; lab.setAttribute('fill', 'var(--ink)');
      const w = Math.max(x(v) - padL, 2);
      el('path', { d: `M${padL},${y} h${w - 4} a4,4 0 0 1 4,4 v${h - 8} a4,4 0 0 1 -4,4 h-${w - 4} z`, fill: it.color }, s);
      const vl = el('text', { x: x(v) + 8, y: y + h / 2 + 4, class: 'value-label' }, s);
      vl.textContent = `${it.s}/${it.n}`;
      const hit = el('rect', { x: 0, y: y - 6, width: W, height: rowH - 4, class: 'hit' }, s);
      bindTip(hit, `<strong>${it.label}</strong><br><b>${it.s}/${it.n}</b> = ${fmtPct(v)}${it.tip ? '<br>' + it.tip : ''}`);
    });
    tableView(container, ['Arm', 'Successes', 'Episodes', 'Rate'], items.map(i => [i.label, i.s, i.n, fmtPct(pct(i.s, i.n))]));
  }

  /* Dot plot: rows = groups (e.g. seeds); series = arms with colors */
  function dots(container, rows, series, opts = {}) {
    const W = 640, rowH = 46, padL = 90, padR = 30, top = 10;
    const H = top + rows.length * rowH + 30;
    container.innerHTML = '';
    legend(container, series.map(s => ({ label: s.label, color: s.color, dot: true })));
    const wrap = document.createElement('div'); container.appendChild(wrap);
    const s = svg(wrap, W, H, opts.label);
    const [lo, hi] = opts.domain || [0, 100];
    const x = v => padL + (W - padL - padR) * (v - lo) / (hi - lo);
    xAxis(s, x, top, top + rows.length * rowH, opts.ticks || [0, 20, 40, 60, 80, 100], v => v + '%');
    rows.forEach((r, i) => {
      const y = top + i * rowH + rowH / 2;
      const lab = el('text', { x: padL - 14, y: y + 4, 'text-anchor': 'end' }, s); lab.textContent = r.label; lab.setAttribute('fill', 'var(--ink)');
      const vals = series.map(se => pct(...r.values[se.key]));
      el('line', { x1: x(Math.min(...vals)), x2: x(Math.max(...vals)), y1: y, y2: y, stroke: 'var(--line-2)', 'stroke-width': 2 }, s);
      series.forEach(se => {
        const [a, b] = r.values[se.key];
        const c = el('circle', { cx: x(pct(a, b)), cy: y, r: 8, fill: se.color, stroke: 'var(--card)', 'stroke-width': 2 }, s);
        bindTip(c, `<strong>${se.label}</strong> · ${r.label}<br><b>${a}/${b}</b> = ${fmtPct(pct(a, b))}`);
      });
    });
    tableView(container, ['Group', ...series.map(s => s.label)], rows.map(r => [r.label, ...series.map(se => r.values[se.key].join('/'))]));
  }

  /* Dumbbell: rows {label, before, after, n, note} */
  function dumbbell(container, rows, opts = {}) {
    const W = 640, rowH = 34, padL = 150, padR = 60, top = 10;
    const H = top + rows.length * rowH + 30;
    container.innerHTML = '';
    legend(container, [{ label: opts.beforeLabel || 'Before', color: 'var(--base)', dot: true }, { label: opts.afterLabel || 'After', color: 'var(--s1)', dot: true }]);
    const wrap = document.createElement('div'); container.appendChild(wrap);
    const s = svg(wrap, W, H, opts.label);
    const x = v => padL + (W - padL - padR) * v / 100;
    xAxis(s, x, top, top + rows.length * rowH, [0, 20, 40, 60, 80, 100], v => v + '%');
    rows.forEach((r, i) => {
      const y = top + i * rowH + rowH / 2;
      const lab = el('text', { x: padL - 14, y: y + 4, 'text-anchor': 'end' }, s); lab.textContent = r.label; lab.setAttribute('fill', 'var(--ink)');
      const b = pct(r.before, r.n), a = pct(r.after, r.n);
      el('line', { x1: x(b), x2: x(a), y1: y, y2: y, stroke: 'var(--s1)', 'stroke-width': 2, opacity: .45 }, s);
      el('circle', { cx: x(b), cy: y, r: 6, fill: 'var(--base)', stroke: 'var(--card)', 'stroke-width': 2 }, s);
      el('circle', { cx: x(a), cy: y, r: 7, fill: 'var(--s1)', stroke: 'var(--card)', 'stroke-width': 2 }, s);
      const d = el('text', { x: x(a) + 12, y: y + 4, class: 'value-label' }, s); d.textContent = `+${r.after - r.before}`;
      const hit = el('rect', { x: 0, y: y - rowH / 2, width: W, height: rowH, class: 'hit' }, s);
      bindTip(hit, `<strong>${r.label}</strong><br>${opts.beforeLabel || 'Before'}: <b>${r.before}/${r.n}</b><br>${opts.afterLabel || 'After'}: <b>${r.after}/${r.n}</b>${r.note ? '<br>' + r.note : ''}`);
    });
    tableView(container, ['Model', opts.beforeLabel || 'Before', opts.afterLabel || 'After', 'n'], rows.map(r => [r.label, r.before, r.after, r.n]));
  }

  /* Compound-error line: y = p^k for k = 1..maxN, with marker at n */
  function compound(container, p, n, maxN = 40) {
    const W = 640, H = 300, padL = 48, padR = 20, top = 14, bot = 34;
    const s = svg(container, W, H, `Probability of completing a task of k steps when each step succeeds with ${p}`);
    const x = k => padL + (W - padL - padR) * (k - 1) / (maxN - 1);
    const y = v => top + (H - top - bot) * (1 - v);
    const g = el('g', { class: 'grid' }, s);
    [0, .25, .5, .75, 1].forEach(v => {
      el('line', { x1: padL, x2: W - padR, y1: y(v), y2: y(v) }, g);
      const t = el('text', { x: padL - 8, y: y(v) + 4, 'text-anchor': 'end' }, s); t.textContent = (v * 100) + '%'; t.setAttribute('fill', 'var(--muted)');
    });
    [1, 10, 20, 30, 40].forEach(k => { const t = el('text', { x: x(k), y: H - 12, 'text-anchor': 'middle' }, s); t.textContent = k; t.setAttribute('fill', 'var(--muted)'); });
    const xl = el('text', { x: W - padR, y: H - 12, 'text-anchor': 'end' }, s); xl.textContent = 'steps →'; xl.setAttribute('fill', 'var(--muted)');
    // reference: three-cube vs two-cube region
    let d = '';
    for (let k = 1; k <= maxN; k++) d += (k === 1 ? 'M' : 'L') + x(k) + ',' + y(Math.pow(p, k));
    el('path', { d: d + `L${x(maxN)},${y(0)}L${x(1)},${y(0)}Z`, fill: 'var(--accent)', opacity: .07 }, s);
    el('path', { d, fill: 'none', stroke: 'var(--accent)', 'stroke-width': 2.5, 'stroke-linejoin': 'round' }, s);
    const v = Math.pow(p, n);
    el('line', { x1: x(n), x2: x(n), y1: y(0), y2: y(v), stroke: 'var(--ink)', 'stroke-dasharray': '3 3' }, s);
    el('circle', { cx: x(n), cy: y(v), r: 6, fill: 'var(--accent)', stroke: '#fff', 'stroke-width': 2 }, s);
    // hover crosshair
    const cross = el('line', { y1: top, y2: y(0), stroke: 'var(--muted)', opacity: 0 }, s);
    const hit = el('rect', { x: padL, y: top, width: W - padL - padR, height: H - top - bot, class: 'hit' }, s);
    hit.addEventListener('mousemove', e => {
      const r = s.getBoundingClientRect(); const px = (e.clientX - r.left) * W / r.width;
      const k = Math.max(1, Math.min(maxN, Math.round(1 + (px - padL) / (W - padL - padR) * (maxN - 1))));
      cross.setAttribute('x1', x(k)); cross.setAttribute('x2', x(k)); cross.setAttribute('opacity', .6);
      showTip(`<b>${k}</b> step${k > 1 ? 's' : ''} → <b>${fmtPct(Math.pow(p, k) * 100)}</b> complete`, e);
    });
    hit.addEventListener('mouseleave', () => { cross.setAttribute('opacity', 0); hideTip(); });
  }

  /* Single stacked bar with two parts (HTML, so text stays legible at any width) */
  function split(container, parts, opts = {}) {
    container.innerHTML = '';
    legend(container, parts.map(p => ({ label: p.label, color: p.color })));
    const total = parts.reduce((a, p) => a + p.v, 0);
    const bar = document.createElement('div'); bar.setAttribute('role', 'img'); bar.setAttribute('aria-label', opts.label || '');
    bar.style.cssText = 'display:flex;gap:2px;height:30px;margin-top:4px';
    const labs = document.createElement('div'); labs.style.cssText = 'display:flex;gap:2px;margin-top:6px;font:600 13px var(--mono)';
    parts.forEach((p, i) => {
      const seg = document.createElement('div');
      seg.style.cssText = `flex:${p.v};background:${p.color};border-radius:${i === 0 ? '4px 0 0 4px' : i === parts.length - 1 ? '0 4px 4px 0' : '0'}`;
      bindTip(seg, `<strong>${p.label}</strong><br><b>${p.v}</b> of ${total} = ${fmtPct(100 * p.v / total)}`);
      bar.appendChild(seg);
      const l = document.createElement('div'); l.style.flex = p.v; l.textContent = `${p.v} ${p.short || ''}`; labs.appendChild(l);
    });
    container.appendChild(bar); container.appendChild(labs);
  }

  window.Charts = { hbars, dots, dumbbell, compound, split, el, bindTip, hideTip, fmtPct, pct };
})();
