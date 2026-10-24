/** 24.10 Faz 2 — platform yüzü bekçileri (kaynak pinleri):
 *  (1) App'te /yonetim yol kapısı ve tembel Yonetim parçası; (2) platform istemcisi AYRI jeton anahtarı kullanır (pvq_platform_token)
 *  ve müşteri jetonuna dokunmaz; (3) müşteri panelinden GelenTalepler ve başvuru uçları kalktı; (4) platform yüzü koyu + data-yuz;
 *  (5) sahip-only sayfa listede işaretli. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (p: string) => readFileSync(new URL(`../../src/${p}`, import.meta.url), "utf8");

test("App: /yonetim kapısı ayrı tembel parça", () => {
  const app = oku("App.tsx");
  assert.match(app, /const Yonetim = lazy\(\(\) => import\("\.\/features\/yonetim\/Yonetim"\)/);
  assert.match(app, /window\.location\.pathname === "\/yonetim" \|\| window\.location\.pathname\.startsWith\("\/yonetim\/"\)/);
  assert.match(app, /icerik = <Yonetim \/>;/);
});

test("platform istemcisi: ayrı jeton anahtarı, müşteri jetonuna dokunmaz", () => {
  const y = oku("api/yonetim.ts");
  assert.match(y, /const ANAHTAR = "pvq_platform_token";/);
  assert.doesNotMatch(y, /pvq_token"/);
  assert.match(y, /\/v1\/yonetim\$\{yol\}/);
  assert.match(y, /platformCikis\(\); dusunce\?\.\(\)/);   // 401 → yalnız platform oturumu düşer
});

test("müşteri paneli: GelenTalepler ve başvuru uçları yok", () => {
  const portfoy = oku("features/sayfalar/Portfoy.tsx");
  assert.doesNotMatch(portfoy, /<GelenTalepler/);
  assert.doesNotMatch(portfoy, /function GelenTalepler/);
  const client = oku("api/client.ts");
  assert.doesNotMatch(client, /\/v1\/vitrin\/basvurular/);
});

test("platform yüzü: koyu sabit, data-yuz=platform, nötr vurgu jetonu, sahip-only sayfa", () => {
  const kok = oku("features/yonetim/Yonetim.tsx");
  assert.match(kok, /kok\.dataset\.tema = "koyu"; kok\.dataset\.yuz = "platform";/);
  const css = oku("index.css");
  assert.match(css, /:root\[data-yuz="platform"\] \{ --marka: #5B8DEF;/);
  const liste = oku("features/yonetim/sayfaListesi.ts");
  assert.match(liste, /\{ id: "operatorler", ad: "Operatörler", sahip: true \}/);
  const kabuk = oku("features/yonetim/PlatformKabugu.tsx");
  assert.match(kabuk, /YSAYFALAR\.filter\(\(s\) => !s\.sahip \|\| ben\?\.rol === "sahip"\)/);
});

test("zorunlu 2FA: jeton var ama totp kapalıysa kurulum ekranı, kabuk açılmaz", () => {
  const kok = oku("features/yonetim/Yonetim.tsx");
  assert.match(kok, /if \(kurulmali\) return <IkiAdimKurulum/);
  assert.match(kok, /setKurulmali\(!b\.totp_aktif\)/);
});
