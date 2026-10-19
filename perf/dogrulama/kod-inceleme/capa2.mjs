import { chromium, webkit } from '/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/node_modules/playwright/index.mjs';
for (const [ad, m] of [['chromium', chromium], ['webkit', webkit]]) {
  for (const kok of ['https://localhost:18443', 'https://localhost:28443']) {
    const b = await m.launch(); const r = [];
    const ctx = await b.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(() => {
      window.__ilk = null; window.__devir = -1;
      new MutationObserver((ml, o) => { if (document.getElementById('karne')) { window.__devir = performance.now(); o.disconnect(); } }).observe(document, { childList: true, subtree: true });
      try { new PerformanceObserver((l) => { const e = l.getEntriesByName('first-contentful-paint')[0]; if (!window.__ilk && e) window.__ilk = { t: Math.round(e.startTime), karneVar: !!document.getElementById('karne'), y: Math.round(scrollY) }; }).observe({ type: 'paint', buffered: true }); } catch {}
    });
    const p = await ctx.newPage();
    await p.goto(kok + '/yontem', { waitUntil: 'load' }); await p.waitForTimeout(800);   // önbelleği ısıt (aynı demet)
    await p.goto(kok + '/', { waitUntil: 'load' }); await p.waitForTimeout(800);
    for (let i = 0; i < 3; i++) {
      await p.goto('about:blank'); await p.goto(kok + '/#karne', { waitUntil: 'load' }); await p.waitForTimeout(1200);   // yeni gezinme (yenileme değil)
      const s = await p.evaluate(() => ({ ilk: window.__ilk, devir: Math.round(window.__devir), son: Math.round(scrollY) }));
      r.push(`FCP=${s.ilk?.t} (karne=${s.ilk?.karneVar}, y=${s.ilk?.y}) karneDOM=${s.devir} son.y=${s.son}`);
    }
    console.log(ad, kok.endsWith('18443') ? 'once ' : 'sonra', '\n   ' + r.join('\n   '));
    await b.close();
  }
}
