import { chromium, firefox, webkit } from '/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/node_modules/playwright/index.mjs';
const KOK = process.argv[2];
for (const [ad, m] of [['chromium', chromium], ['firefox', firefox], ['webkit', webkit]]) {
  const b = await m.launch(); const r = [];
  for (let i = 0; i < 3; i++) {
    const ctx = await b.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
    await ctx.addInitScript(() => {
      window.__devir = -1; window.__lcp = [];
      new MutationObserver((ml, o) => { const k = document.getElementById('root'); if (k && k.firstElementChild && !k.querySelector(':scope>[data-kabuk]') && k.dataset.g !== '1') { window.__devir = performance.now(); o.disconnect(); } }).observe(document, { childList: true, subtree: true });
      try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp.push(Math.round(e.startTime) + ':' + (e.element?.tagName ?? '?')); }).observe({ type: 'largest-contentful-paint', buffered: true }); } catch {}
    });
    const p = await ctx.newPage(); const hata = [];
    p.on('pageerror', (e) => hata.push(e.message));
    await p.goto(KOK + '/', { waitUntil: 'load', timeout: 90000 }); await p.waitForTimeout(1500);
    const s = await p.evaluate(() => ({ fcp: Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? -1), devir: Math.round(window.__devir), lcp: window.__lcp.join(' ') }));
    r.push(`fcp=${s.fcp} devir=${s.devir} lcp=[${s.lcp}]${hata.length ? ' HATA ' + hata.join('|') : ''}`);
    await ctx.close();
  }
  console.log(ad, r.join(' ; ')); await b.close();
}
