import { chromium, firefox, webkit } from '/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/node_modules/playwright/index.mjs';
import { readFileSync } from 'node:fs';
const dist = readFileSync('/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/web/dist/index.html', 'utf8');
const styleM = dist.match(/<style>(@font-face[\s\S]*?)<\/style>/);
const scriptM = dist.match(/<script>(try\{if\(document\.fonts\)[\s\S]*?)<\/script>/);
const css = styleM[1], js = scriptM[1];
// Android benzetimi: local() adlarından hiçbiri yok
const cssYok = css.replace(/local\('([^']+)'\)/g, "local('YokBoyleFont$1')");
const sayfa = (c) => `<!doctype html><html><head><meta charset="utf-8"><style>${c}</style><script>${js}</script></head><body><p style="font-family:'Inter Tight Yedek'">deneme</p></body></html>`;
for (const [ad, motor] of [['chromium', chromium], ['firefox', firefox], ['webkit', webkit]]) {
  const b = await motor.launch();
  for (const [durum, c] of [['gercek-local', css], ['local-yok(Android)', cssYok]]) {
    const p = await b.newPage();
    const olay = [];
    p.on('pageerror', (e) => olay.push('pageerror: ' + e.message));
    p.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') olay.push(m.type() + ': ' + m.text()); });
    await p.setContent(sayfa(c));
    await p.waitForTimeout(800);
    const durumlar = await p.evaluate(() => [...document.fonts].filter(f => f.family.includes('Yedek')).map(f => f.weight + ':' + f.status));
    console.log(ad, durum, JSON.stringify(durumlar), olay.length ? olay : 'olay yok');
    await p.close();
  }
  await b.close();
}
