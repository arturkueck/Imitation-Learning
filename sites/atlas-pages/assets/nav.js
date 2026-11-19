/* Shared header and previous/next navigation for all pages.
   Each page sets <body data-page="..." data-base="../"> (base is "" on the home page). */
(function () {
  const PAGES = [
    { id: 'home', href: '', label: 'Overview' },
    { id: 'watch', href: 'watch/', label: 'Watch' },
    { id: 'experiments', href: 'experiments/', label: 'Experiments' },
    { id: 'vision', href: 'vision/', label: 'Vision' },
    { id: 'plan', href: 'plan/', label: 'Plan' },
    { id: 'journal', href: 'journal/', label: 'Journal' },
    { id: 'literature', href: 'literature/', label: 'Literature' }
  ];
  const body = document.body, base = body.dataset.base || '', cur = body.dataset.page;
  const url = p => base + p.href || './';
  const logo = `<svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><g stroke="#fff" stroke-width=".6"><polygon points="16,20 23,24 16,28 9,24" fill="#9fc4f1"/><polygon points="9,24 16,28 16,31 9,27" fill="#2a78d6"/><polygon points="23,24 16,28 16,31 23,27" fill="#1c5cab"/><polygon points="16,11 23,15 16,19 9,15" fill="#f7b796"/><polygon points="9,15 16,19 16,24 9,20" fill="#eb6834"/><polygon points="23,15 16,19 16,24 23,20" fill="#b9471d"/></g><polygon points="16,2 23,6 16,10 9,6" fill="none" stroke="#be1e3c" stroke-dasharray="2 1.5"/></svg>`;
  const header = document.getElementById('topbar');
  if (header) header.innerHTML = `<div class="wrap">
      <a class="brand" href="${url(PAGES[0])}">${logo}<span>Beyond the Demonstrated Task<small>Imitation Learning · project site</small></span></a>
      <nav class="steps-nav" aria-label="Pages">${PAGES.map((p, i) => `<a href="${url(p)}"${p.id === cur ? ' class="active" aria-current="page"' : ''}><b>${i ? i : '⌂'}</b><span>${p.label}</span></a>`).join('')}</nav>
    </div><div class="progress" id="progress"></div>`;
  // previous / next
  const i = PAGES.findIndex(p => p.id === cur), pn = document.getElementById('pagenav');
  if (pn && i >= 0) {
    const prev = PAGES[i - 1], next = PAGES[i + 1];
    pn.innerHTML = `<div class="wrap">${prev ? `<a class="pn prev" href="${url(prev)}"><small>← Previous</small>${prev.label}</a>` : '<span></span>'}${next ? `<a class="pn next" href="${url(next)}"><small>Next →</small>${next.label}</a>` : `<a class="pn next" href="${url(PAGES[0])}"><small>Back to start ↺</small>Overview</a>`}</div>`;
  }
  window.SITE_PAGES = PAGES;
})();
