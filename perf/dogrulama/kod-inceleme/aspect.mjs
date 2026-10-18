import { chromium, firefox, webkit } from '/Users/sisamlipisagor/Desktop/masaüstü/pvquant/.claude/worktrees/perf-cross-browser/perf/node_modules/playwright/index.mjs';
const html = (w) => `<!doctype html><style>*{box-sizing:border-box}.k{display:flex;flex-direction:column;width:350px;overflow:hidden}.l{display:block;line-height:0;position:relative;aspect-ratio:10/8;overflow:hidden;margin:12px 12px 0;width:${w}}</style><div class="k"><div class="l" id="x"></div><p>govde</p></div>`;
for (const [ad, m] of [['chromium', chromium], ['firefox', firefox], ['webkit', webkit]]) {
  const b = await m.launch(); const p = await b.newPage();
  const r = [];
  for (const w of ['auto', 'calc(100% - 24px)']) { await p.setContent(html(w)); r.push(w + ' → ' + await p.evaluate(() => { const e = document.getElementById('x').getBoundingClientRect(); return `${e.width}x${e.height}`; })); }
  console.log(ad, r.join(' | ')); await b.close();
}
