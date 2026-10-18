import { chromium, firefox, webkit } from '/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/node_modules/playwright/index.mjs';
const KOK = process.argv[2];
for (const [ad, m] of [['chromium', chromium], ['firefox', firefox], ['webkit', webkit]]) {
  const b = await m.launch();
  const ctx = await b.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  const sonuc = [];
  for (const tur of ['soguk', 'yenile']) {
    const mp4 = []; const dinle = (r) => { if (/\.mp4/.test(r.url())) mp4.push(r.url().slice(-30)); };
    p.on('request', dinle);
    if (tur === 'soguk') await p.goto(KOK + '/', { waitUntil: 'load', timeout: 90000 }); else await p.reload({ waitUntil: 'load', timeout: 90000 });
    await p.waitForTimeout(7000);
    const s = await p.evaluate(() => {
      const g = performance.getEntriesByType('resource').filter(e => /santral-poster/.test(e.name)).map(e => `${Math.round(e.responseEnd - e.startTime)}ms/t${e.transferSize}/e${e.encodedBodySize}`);
      return { kayit: localStorage.getItem('pvq_yavas_hat'), poster: g };
    });
    p.off('request', dinle);
    sonuc.push(`${tur}: kayit=${s.kayit} poster=${JSON.stringify(s.poster)} mp4=${mp4.length}`);
  }
  console.log(ad, '\n  ' + sonuc.join('\n  '));
  await b.close();
}
