import { chromium, firefox, webkit } from '/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/node_modules/playwright/index.mjs';
for (const [ad, m] of [['chromium', chromium], ['firefox', firefox], ['webkit', webkit]]) {
  for (const kok of ['https://localhost:18443', 'https://localhost:28443']) {
    const b = await m.launch(); const r = [];
    const ctx = await b.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(() => {
      window.__ilk = null;
      try { new PerformanceObserver((l) => { if (!window.__ilk && l.getEntriesByName('first-contentful-paint').length) window.__ilk = { karneVar: !!document.getElementById('karne'), y: Math.round(scrollY) }; }).observe({ type: 'paint', buffered: true }); } catch {}
    });
    const p = await ctx.newPage();
    await p.goto(kok + '/#karne', { waitUntil: 'load' }); await p.waitForTimeout(1500);
    for (let i = 0; i < 3; i++) {
      await p.reload({ waitUntil: 'load' }); await p.waitForTimeout(1200);
      const s = await p.evaluate(() => ({ ilk: window.__ilk, son: Math.round(scrollY) }));
      r.push(`ilkKare(karne=${s.ilk?.karneVar},y=${s.ilk?.y}) son.y=${s.son}`);
    }
    console.log(ad, kok.endsWith('18443') ? 'once ' : 'sonra', r.join(' ; '));
    await b.close();
  }
}
