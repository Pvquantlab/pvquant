import { chromium, firefox } from '/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/node_modules/playwright/index.mjs';
for (const [ad, m] of [['chromium', chromium], ['firefox', firefox]]) {
  for (const kok of ['https://localhost:18443', 'https://localhost:28443']) {
    const b = await m.launch();
    const ctx = await b.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
    // Arial/Liberation/Arimo olmayan sistem benzetimi: index.html'deki local() adları var olmayan adlara çevrilir
    await ctx.route(kok + '/', async (r) => { const y = await r.fetch(); const h = (await y.text()).replace(/local\('([^']+)'\)/g, "local('YokBoyle$1')"); await r.fulfill({ response: y, body: h }); });
    const p = await ctx.newPage(); const olay = [];
    p.on('pageerror', (e) => olay.push('pageerror: ' + e.message));
    p.on('console', (c) => { if (c.type() === 'error') olay.push('console.error: ' + c.text().slice(0, 120)); });
    await p.goto(kok + '/', { waitUntil: 'load' }); await p.waitForTimeout(1500);
    console.log(ad, kok.endsWith('18443') ? 'once' : 'sonra', olay.length ? JSON.stringify(olay) : 'olay yok');
    await b.close();
  }
}
