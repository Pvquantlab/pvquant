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

// ---------------- 25.10 Faz 3: sistem izleme ----------------
test("Faz 3: Sistem sayfası listede, kökte ve istemcide; hükümler uçtan", () => {
  const liste = oku("features/yonetim/sayfaListesi.ts");
  assert.match(liste, /\{ id: "sistem", ad: "Sistem" \}/);
  const kok = oku("features/yonetim/Yonetim.tsx");
  assert.match(kok, /\{sayfa === "sistem" && <Sistem \/>\}/);
  const y = oku("api/yonetim.ts");
  for (const uc of ['istek("/sistem")', "istek(`/isler${sorgu(p)}`)", "istek(`/santraller${sorgu({ sorunlu })}`)"]) assert.ok(y.includes(uc), uc);
  const sayfa = oku("features/yonetim/Sistem.tsx");
  // bayatlık hükmü arayüzde HESAPLANMAZ: tonlar uçtan gelen durum/taze/bayat alanlarını okur
  assert.match(sayfa, /ton=\{o\.nabiz\.durum === "calisiyor" \? undefined : "uyari"\}/);
  assert.match(sayfa, /ton=\{o\.gece_turu\.taze \? undefined : "uyari"\}/);
  assert.match(sayfa, /ton=\{o\.piyasa\.bayat \? "uyari" : undefined\}/);
  assert.doesNotMatch(sayfa, /yas_saat\s*>\s*\d|yas_dk\s*>\s*\d/);
  // hata ayrıntısı platformda görünür …
  assert.match(sayfa, /\{x\.ayrinti \?\? "—"\}/);
});

test("Faz 3: müşteri tarafı değişmedi — Isler tipi ve gece işleri kartı hata ayrıntısı taşımaz", () => {
  const tipler = oku("api/types.ts");
  const isler = tipler.slice(tipler.indexOf("export interface Isler"), tipler.indexOf("export interface Isler") + 400);
  assert.doesNotMatch(isler, /ayrinti|detail/);
  const d = oku("features/sayfalar/Digerleri.tsx");
  const kart = d.slice(d.indexOf("function GeceIsleriKarti"), d.indexOf("function GeceIsleriKarti") + 2600);
  assert.doesNotMatch(kart, /ayrinti/);
  assert.match(kart, /ayrıntı sunucu günlüğünde/);
});

// ---------------- 25.10 Faz 4: kullanım ----------------
test("Faz 4: Kullanım sayfası listede, kökte, istemcide; detayda kullanım kartı; müşteri tarafı değişmedi", () => {
  const liste = oku("features/yonetim/sayfaListesi.ts");
  assert.match(liste, /\{ id: "kullanim", ad: "Kullanım" \}/);
  assert.match(oku("features/yonetim/Yonetim.tsx"), /\{sayfa === "kullanim" && <Kullanim \/>\}/);
  const y = oku("api/yonetim.ts");
  assert.ok(y.includes("istek(`/kullanim${sorgu({ ay })}`)") && y.includes("istek(`/kullanim${sorgu({ tenant_id, ay })}`)"));
  const sayfa = oku("features/yonetim/Kullanim.tsx");
  // altı sütun: sayaç türleri + türetilmiş sayımlar; plan sınırı/limit rozeti YOK (Faz 5)
  for (const k of ['"dis_api"', '"webhook"', '"rapor"', '"kosu"', '"scada_saat"', '"yukleme"']) assert.ok(sayfa.includes(`k: ${k}`), k);
  assert.doesNotMatch(sayfa, /asildi|aşıldı|limit_|rozet-limit/);   // limit rozeti/zorlaması yok
  assert.match(oku("features/yonetim/sayfalar.tsx"), /<KullanimKarti tenantId=\{id\} \/>/);
  // müşteri istemcisi kullanım ucu bilmez
  assert.doesNotMatch(oku("api/client.ts"), /\/v1\/yonetim/);
});

// ---------------- 25.10 denetim tablo turu (O1/O2/O3) ----------------
test("tablo turu: ayrıntı çipleri, kiracı adı ve seçimi, tek zaman tipografisi, yalnız platform CSS", () => {
  const s = oku("features/yonetim/sayfalar.tsx");
  assert.match(s, /<AyrintiCipleri a=\{k\.ayrinti\} \/>/);
  assert.doesNotMatch(s, /JSON\.stringify\(k\.ayrinti\)/);
  assert.match(s, /k\.kiraci_ad \?\?/);
  assert.match(s, /<label className="girdi-etiket">Kiracı<select/);
  for (const f of ["features/yonetim/sayfalar.tsx", "features/yonetim/Sistem.tsx", "features/yonetim/Kullanim.tsx"]) {
    assert.doesNotMatch(oku(f), /[^$]\{zamanTr\(/, f);       // JSX hücrelerinde yalnız <Zaman/> (şablon dizeleri ${zamanTr} serbest)
  }
  const css = oku("index.css");
  assert.match(css, /:root\[data-yuz="platform"\] table\.veri\.santral th, :root\[data-yuz="platform"\] table\.veri\.santral td \{ text-align: left;/);
  assert.match(css, /:root\[data-yuz="platform"\] \.zaman \{ font-family: var\(--mono\)/);
  // müşteri paneli tablo kuralı değişmedi
  assert.match(css, /\ntable\.veri th \{ text-align: right;/);
  assert.match(css, /\ntable\.veri\.santral th, table\.veri\.santral td \{ width: 1%; \}/);
});

// ---------------- 25.10 denetim O4/O6/O8 ----------------
test("O4 KPI metni gerçekleşen fiyat der; O6 genel bakış görüntüleme izini dışlar; O8 boşta yenileme durur", () => {
  assert.match(oku("features/yonetim/Sistem.tsx"), /gerçekleşen PTF\/SMF/);
  assert.match(oku("features/yonetim/sayfalar.tsx"), /eylem_haric: "kiraci_goruntule"/);
  const kok = oku("features/yonetim/Yonetim.tsx");
  assert.match(kok, /const BOSTA_DK = 30;/);
  assert.match(kok, /if \(Date\.now\(\) - sonEtkilesim < BOSTA_DK \* 60 \* 1000\) void yonetim\.oturumYenile\(\)/);
  assert.match(kok, /addEventListener\("pointerdown", dokun/);
});

// ---------------- 26.10 D2/D3/D5 ----------------
test("D turu: envanter son hata → iş kayıtları süzgeci, Operatörler kendi satırı, Genel bakış sağlık şeridi", () => {
  const sis = oku("features/yonetim/Sistem.tsx");
  assert.match(sis, /plant_id: ek\.plant === undefined \? santral\?\.id/);
  assert.match(sis, /onClick=\{\(\) => santralSec\(p\.id, p\.ad\)\}/);
  assert.match(sis, /<option value=\{720\}>son 30 gün<\/option>/);
  const s = oku("features/yonetim/sayfalar.tsx");
  assert.match(s, /Kendi hesabınız: rol ve durum başka bir sahip tarafından değiştirilir/);
  assert.match(s, /<SaglikSeridi sis=\{sis\} git=\{\(\) => git\("sistem"\)\} \/>/);
  assert.match(s, /ok=\{sis\.nabiz\.durum === "calisiyor"\}/);   // hüküm uçtan
  assert.match(oku("api/yonetim.ts"), /plant_id\?: string \} = \{\}\)/);
});
