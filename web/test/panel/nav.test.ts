// v2.608 (Faz 5 F5-A) — yan menü grupları bekçisi: her sayfa kimliği TAM BİR grupta, App her kimliği çizer, hash derin bağlantısı
// bilinen kimlikleri korur, gruplar brief §6 düzenine uyar (beş grup, sıra sabit), KGÜP ve Paylaşım çift hedef değil.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL("../../src/" + yol, import.meta.url), "utf8");
const kabuk = oku("shell/Kabuk.tsx");
const idler = [...kabuk.matchAll(/\{ id: "([a-z]+)", ad: "[^"]+", yuz: "(acik|koyu)" \}/g)].map((m) => m[1]);
const gruplarKaynak = oku("shell/gruplar.ts");
const gruplar = [...gruplarKaynak.matchAll(/\{ id: "([a-z]+)", ad: "([^"]+)", sayfalar: \[([^\]]+)\] \}/g)].map((m) => ({ id: m[1], ad: m[2], sayfalar: m[3].split(",").map((s) => s.trim().replace(/"/g, "")) }));

test("her sayfa kimliği tam bir grupta; grup listesi brief düzeninde", () => {
  assert.ok(idler.length >= 19, `SAYFALAR ${idler.length}`);
  assert.deepEqual(gruplar.map((g) => g.ad), ["Genel bakış", "Üretim", "Piyasa ve finans", "Operasyon", "Yönetim"]);
  const sayim = new Map<string, number>();
  for (const g of gruplar) for (const s of g.sayfalar) sayim.set(s, (sayim.get(s) ?? 0) + 1);
  for (const id of idler) assert.equal(sayim.get(id), 1, `${id} tam bir grupta olmalı`);
  for (const [id] of sayim) assert.ok(idler.includes(id), `${id} SAYFALAR'da yok`);
  assert.deepEqual(gruplar[2].sayfalar, ["kgup", "portfoyler", "mutabakat", "finans"]);
  assert.deepEqual(gruplar[4].sayfalar, ["raporlar", "paylasim", "kurulus", "hakkinda"]);
});

test("App her kimliği çizer; santralsız sayfalar kapıdan muaf; KGÜP ve Paylaşım kendi sayfasında", () => {
  const app = oku("App.tsx");
  for (const id of idler) assert.match(app, new RegExp(`sayfa === "${id}"`), `App'te ${id} rotası`);
  assert.match(app, /hashBaglanti\(\)\.sayfa \?\? "genel"/);
  assert.match(app, /!plantId && !SANTRALSIZ\.includes\(sayfa\) && <SantralYok \/>/);
  const santralsiz = /SANTRALSIZ: SayfaId\[\] = \[([^\]]+)\]/.exec(gruplarKaynak)![1].split(",").map((s) => s.trim().replace(/"/g, ""));
  assert.deepEqual(santralsiz, ["portfoy", "portfoyler", "kurulus", "paylasim", "hakkinda"]);
  for (const id of santralsiz) assert.ok(idler.includes(id), `${id} SAYFALAR'da yok`);
  assert.match(app, /<Tahminler plantId=\{plantId\} kgupGit=/);
  assert.match(app, /sayfa === "kgup" && <Kgup plantId=/);
  assert.match(app, /sayfa === "paylasim" && <Paylasim \/>/);
});

test("yan menü: grup başlığı aria-expanded, aktif grup zorla açık, kapalı gruplar kalıcı; palet grup adıyla arar", () => {
  assert.match(kabuk, /const acik = aktif \|\| !kapaliGruplar\.includes\(g\.id\)/);
  assert.match(kabuk, /aria-expanded=\{acik\} aria-controls=/);
  assert.match(kabuk, /<div id=\{`yan-grup-\$\{g\.id\}`\} hidden=\{!acik\}>/);   // inceleme: kapsayıcı her zaman çizilir
  assert.match(kabuk, /localStorage\.setItem\(NAV_KAPALI_ANAHTAR/);
  assert.match(kabuk, /import \{ GRUPLAR, NAV_KAPALI_ANAHTAR, kapaliGruplariOku \} from "\.\/gruplar"/);
  assert.match(kabuk, /katla\(grupAdi\(s\.id\)\)\.includes\(q\)/);
  assert.match(kabuk, /aria-current=\{\(tiklanan \?\? sayfa\) === s\.id \? "page" : undefined\}/);
});
