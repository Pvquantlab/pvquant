import { chromium, firefox, webkit } from '/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/node_modules/playwright/index.mjs';
const KOK = process.argv[2] || 'https://localhost:28443';
const durumlar = [['/', null], ['/yontem', null], ['/', 'j'], ['/?vitrin', 'j']];
for (const [ad, m] of [['chromium', chromium], ['firefox', firefox], ['webkit', webkit]]) {
  const b = await m.launch();
  for (const [yol, jeton] of durumlar) {
    const ctx = await b.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
    if (jeton) await ctx.addInitScript((j) => { try { localStorage.setItem('pvq_token', j); } catch {} }, jeton);
    const p = await ctx.newPage();
    const olay = [];
    p.on('pageerror', (e) => olay.push('pageerror: ' + e.message));
    p.on('console', (c) => { if (c.type() === 'error' || c.type() === 'warning') olay.push(c.type() + ': ' + c.text().slice(0, 160)); });
    p.on('requestfailed', (r) => { const u = r.url(); if (!/\.mp4/.test(u)) olay.push('failed: ' + u.slice(-60) + ' ' + (r.failure()?.errorText ?? '')); });
    p.on('response', (r) => { if (r.status() >= 400) olay.push('http ' + r.status() + ' ' + r.url().slice(-60)); });
    await p.goto(KOK + yol, { waitUntil: 'load' });
    await p.waitForTimeout(2500);
    const s = await p.evaluate(() => ({
      sinif: document.documentElement.className,
      kabukVar: !!document.querySelector('#root>[data-kabuk]'),
      kok: document.getElementById('root')?.firstElementChild?.className?.slice(0, 40) ?? null,
      yedek: [...document.fonts].filter(f => f.family.includes('Yedek')).map(f => f.status).join(','),
      fcp: Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? -1),
    }));
    console.log(ad, yol, jeton ?? '-', JSON.stringify(s), olay.length ? JSON.stringify(olay) : 'olay yok');
    await ctx.close();
  }
  await b.close();
}
