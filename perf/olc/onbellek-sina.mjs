import { chromium, firefox, webkit } from "playwright";
const URL = "https://localhost:18443/";
for (const [ad, tip, ops] of [["chromium", chromium, { args: ["--ignore-certificate-errors-spki-list=fx6RoGSgC+dv1bxkoF5nglVTii+FblgVRaW22nfDZTE="] }], ["firefox", firefox, {}], ["webkit", webkit, {}]]) {
  const b = await tip.launch(ops); const c = await b.newContext({ ignoreHTTPSErrors: true }); const p = await c.newPage();
  const say = async () => p.evaluate(() => performance.getEntriesByType("resource").filter(r => r.name.includes("/assets/")).map(r => ({ n: r.name.split("/").pop().slice(0, 28), t: r.transferSize, e: r.encodedBodySize })));
  await p.goto(URL, { waitUntil: "load" }); await p.waitForTimeout(1500); const a = await say();
  await p.goto(URL, { waitUntil: "load" }); await p.waitForTimeout(1500); const s = await say();
  const ilk = a.reduce((x, r) => x + r.t, 0), ikinci = s.reduce((x, r) => x + r.t, 0);
  console.log(ad, b.version(), "| soğuk aktarım", ilk, "B (" + a.length + " varlık) | sıcak aktarım", ikinci, "B | sıcak 0 olan varlık", s.filter(r => r.t === 0).length + "/" + s.length);
  await b.close();
}
