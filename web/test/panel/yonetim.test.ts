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

test("platform yüzü: data-yuz=platform, yüz seçilebilir (açık varsayılan), nötr vurgu jetonu, sahip-only sayfa", () => {
  const kok = oku("features/yonetim/Yonetim.tsx");
  assert.match(kok, /kok\.dataset\.yuz = "platform";/);
  assert.match(kok, /localStorage\.getItem\("pvq_platform_tema"\) === "koyu" \? "koyu" : "acik"/);   // 27.10: açık varsayılan
  const css = oku("index.css");
  assert.match(css, /:root\[data-yuz="platform"\] \{ --plat-vurgu: #5B8DEF;/);
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
test("tablo turu: ayrıntı çipleri, müşteri adı ve seçimi, tek zaman tipografisi, yalnız platform CSS", () => {
  const s = oku("features/yonetim/sayfalar.tsx");
  assert.match(s, /<AyrintiCipleri a=\{k\.ayrinti\} \/>/);
  assert.doesNotMatch(s, /JSON\.stringify\(k\.ayrinti\)/);
  assert.match(s, /k\.kiraci_ad \?\?/);
  assert.match(s, /<label className="girdi-etiket">Müşteri<select/);   // 26.10: görünen ad «müşteri» (kimlikler kiraci)
  for (const f of ["features/yonetim/sayfalar.tsx", "features/yonetim/Sistem.tsx", "features/yonetim/Kullanim.tsx"]) {
    assert.doesNotMatch(oku(f), /[^$]\{zamanTr\(/, f);       // JSX hücrelerinde yalnız <Zaman/> (şablon dizeleri ${zamanTr} serbest)
  }
  const css = oku("index.css");
  assert.match(css, /:root\[data-yuz="platform"\] table\.veri\.santral th, :root\[data-yuz="platform"\] table\.veri\.santral td \{ text-align: left;/);
  assert.match(css, /:root\[data-yuz="platform"\] \.zaman \{ font-family: var\(--font\); font-variant-numeric: tabular-nums/);   // 26.10 görsel uyum: gövde ailesi, tabular
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

// ---------------- 26.10 Faz 5: planlar (uyarı kipi) + kimliğe bürünme ----------------
test("Faz 5: Planlar sahip-only, limit rozetleri, temsil düğmesi sahipte, müşteri şeridi işaretle, müşteri istemcisi değişmedi", () => {
  assert.match(oku("features/yonetim/sayfaListesi.ts"), /\{ id: "planlar", ad: "Planlar", sahip: true \}/);
  assert.match(oku("features/yonetim/Yonetim.tsx"), /\{sayfa === "planlar" && ben\?\.rol === "sahip" && <Planlar \/>\}/);
  const s = oku("features/yonetim/sayfalar.tsx");
  assert.match(s, /<LimitRozet kullanim=\{k\.santral\} limit=\{planlar\[k\.plan\]\?\.santral_limit\} \/>/);
  assert.match(s, /\{sahip && !askida && <button className="dugme" title="Bu hesabın panelini müşteri gözüyle, salt okunur, 15 dakika/);
  assert.match(oku("features/yonetim/Kullanim.tsx"), /<LimitRozet kullanim=\{t\.dis_api\} limit=\{plan\.aylik_dis_api_limit\} \/>/);
  const y = oku("api/yonetim.ts");
  assert.ok(y.includes('istek(`/kiracilar/${tenant_id}/temsil`, "POST")'));
  assert.doesNotMatch(y, /pvq_token"/);                                            // platform istemcisi müşteri jetonuna dokunmaz (Faz 2 bekçisi korunur)
  assert.match(oku("features/yonetim/temsil.ts"), /localStorage\.setItem\("pvq_temsil"/);   // temsil ayrı modülde
  const kabuk = oku("shell/Kabuk.tsx");
  assert.match(kabuk, /<TemsilSeridi \/>/);
  assert.match(kabuk, /localStorage\.getItem\("pvq_temsil"\)/);
  assert.match(kabuk, /if \(!t\) return null;/);                                   // olağan müşteri oturumunda çizilmez
  assert.doesNotMatch(oku("api/client.ts"), /temsilAc|\/v1\/yonetim/);             // müşteri istemcisi platform uçlarını bilmez (çıkışta pvq_temsil temizliği serbest)
});

// ---------------- 26.10 Faz 6: Kuruluş sayfası ----------------
test("Faz 6: Ayarlar (kimlik kurulus) menüde ve App'te; Portföy yönetim kartlarını çizmez; Kabuk 2FA kapısı; platform rozeti", () => {
  const kabuk = oku("shell/Kabuk.tsx");
  assert.match(kabuk, /\{ id: "kurulus", ad: "Ayarlar", yuz: "acik" \}/);
  assert.match(kabuk, /ikiAdimKurulmali \? <IkiAdimKapisi onTamam=/);
  const app = oku("App.tsx");
  assert.match(app, /\{sayfa === "kurulus" && <Kurulus santralYenile=\{santralYenile\} \/>\}/);
  const portfoy = oku("features/sayfalar/Portfoy.tsx");
  for (const b of ["<DisErisim", "<SantralArsivi", "<Paylasimlar", "<HesapVeEkip", "function DisErisim", "function HesapVeEkip"]) assert.doesNotMatch(portfoy, new RegExp(b), b);
  const kurulus = oku("features/sayfalar/Kurulus.tsx");
  for (const b of ["function DisErisim", "function Paylasimlar", "function HesapVeEkip", "function SantralArsivi", "export function IkiAdimBolumu", "function KurulusDenetim", "function Politika"]) assert.match(kurulus, new RegExp(b), b);
  assert.match(kurulus, /\{yonetici && <DisErisim/);                                   // yazma kartları rolle
  assert.match(oku("api/client.ts"), /kurulusAyarGuncelle: \(yonetici_2fa_zorunlu: boolean\)/);
  assert.match(oku("features/yonetim/sayfalar.tsx"), /"yönetici 2FA zorunlu"/);
});

// ---------------- 26.10 görsel uyum turu (platform = müşteri tasarım sistemi) ----------------
test("görsel uyum: platform tablolarında zaman/sayı gövde ailesi tabular, mono yalnız kimlik/IP/kod/hata; rozet tam boy; süzgeç formu kart içinde; vurgu jetonu", () => {
  const yon = ["features/yonetim/sayfalar.tsx", "features/yonetim/Sistem.tsx", "features/yonetim/Kullanim.tsx", "features/yonetim/ortak.tsx", "features/yonetim/Planlar.tsx"];
  for (const f of yon) {
    const s = oku(f);
    assert.doesNotMatch(s, /rozet-kucuk/, f);                                   // tablo rozeti müşteri paneliyle aynı kesim (12,5 px)
    assert.doesNotMatch(s, /className="(?:[\w-]+ )?mono(?: [\w-]+)?"[^>]*><Zaman /, f);   // zaman hücresi mono sarmalda değil
  }
  const sis = oku("features/yonetim/Sistem.tsx");
  assert.doesNotMatch(sis, /fontSize: 13\.5, minWidth/);                       // tablo puntosu ortak 14 px
  assert.match(sis, /<table className="veri sayisal" style=\{\{ minWidth: 0 \}\}>/);
  assert.doesNotMatch(sis, /className="mono"/);                                // 27.10: platform tablolarında mono yok
  assert.match(sis, /<span title=\{u\.kod\}>\{u\.is\}<\/span>/);   // 27.10: Türkçe ad, kod başlıkta
  const say = oku("features/yonetim/sayfalar.tsx");
  assert.doesNotMatch(say, /className="mono/);                                  // 27.10: kimlik/IP düz gövde metni
  assert.match(say, /<td><span className="rozet rozet-notr" title=\{k\.eylem\}>\{eylemAdi\(k\.eylem\)\}<\/span><\/td>/);   // eylem = Türkçe ad, nötr rozet
  assert.match(say, /<Kart baslik="Kayıtlar"[^>]*>\n\s*\{\/\* 26\.10 görsel uyum[^]*?<form className="form-izgara"/);   // Denetim süzgeci kartta
  assert.match(say, /<Kart baslik="Sonuçlar"[^>]*>\n\s*\{\/\* 26\.10 görsel uyum[^]*?<form className="form-izgara"/);   // Kullanıcılar süzgeci kartta
  const css = oku("index.css");
  assert.match(css, /:root\[data-yuz="platform"\] \{ --plat-vurgu: #5B8DEF; --plat-vurgu-acik: #9DBBFF;/);
  assert.match(css, /--marka: var\(--plat-vurgu\); --marka-koyu: var\(--plat-vurgu-acik\);/);
  assert.match(css, /:root\[data-yuz="platform"\] \.rozet-ok \{ color: var\(--marka-koyu\); \}/);   // 4,2 → 7,2:1
  assert.match(css, /\.plat-rozet \{[^}]*color: var\(--plat-vurgu-acik, #9DBBFF\)/);
  assert.doesNotMatch(css, /\.plat-rozet-sari \{ opacity/);
  assert.match(css, /:root\[data-yuz="platform"\] \.plat-ayrinti__cip \{ font-family: var\(--display\); font-size: 12\.5px; font-weight: 500;/);
  assert.match(css, /\n\.plat-ayrinti__cip \{ display: inline-flex;[^}]*font-family: var\(--mono\)/);   // müşteri Kuruluş çipi değişmedi
  // müşteri paneli jetonları ve kuralları değişmedi
  assert.match(css, /\[data-tema="koyu"\] \{\n[^]*?--zemin: #0B0E15; --kart: #181B23;/);
  assert.match(css, /\n\.rozet-kucuk \{ font-size: 11\.5px; padding: 2px 8px; \}/);
});

// ---------------- 27.10 eylem sözlüğü ----------------
test("eylem sözlüğü: arka uçtaki her denetim eylem kodu Türkçe karşılık taşır; süzgeç sözlükten seçer, değer koddur", () => {
  const kok = (p: string) => readFileSync(new URL(`../../../${p}`, import.meta.url), "utf8");
  const soz = oku("lib/sozluk.ts");
  const blok = soz.slice(soz.indexOf("eylem: {"), soz.indexOf("} as Record<string, string>,\n} as const;"));   // yalnız eylem bloğu
  const sozlukKodlari = new Set([...blok.matchAll(/([a-z0-9_]+): "[^"]+"/g)].map((m) => m[1]));
  const ds = kok("src/pvquant/services/denetim_service.py");
  const kodlar = new Set<string>();
  for (const m of ds.matchAll(/EYLEMLER_(?:PLATFORM|MUSTERI) = \(([^)]*)\)/g)) for (const k of m[1].matchAll(/"([a-z0-9_]+)"/g)) kodlar.add(k[1]);
  for (const f of ["apps/api/yonetim.py", "apps/api/main.py", "src/pvquant/services/platform_service.py", "src/pvquant/services/denetim_service.py"]) {
    for (const m of kok(f).matchAll(/kaydet\(\s*"(?:platform|musteri)",\s*"([a-z0-9_]+)"/g)) kodlar.add(m[1]);
  }
  assert.ok(kodlar.size >= 25, `arka uçta ${kodlar.size} kod bulundu`);
  const eksik = [...kodlar].filter((k) => !sozlukKodlari.has(k));
  assert.deepEqual(eksik, [], "sözlükte karşılığı olmayan eylem kodları");
  assert.match(soz, /export const eylemAdi = \(kod: string\) => SOZLUK\.eylem\[kod\] \?\? kod;/);   // bilinmeyen kod olduğu gibi
  const say = oku("features/yonetim/sayfalar.tsx");
  assert.match(say, /Object\.entries\(SOZLUK\.eylem\)\.map\(\(\[kod, ad\]\) => <option key=\{kod\} value=\{kod\}>\{ad\}<\/option>\)/);
  assert.doesNotMatch(say, /placeholder="ör\. giris/);
});

// ---------------- 27.10 platform açık yüzü (Claude Ivory) ----------------
test("platform açık yüzü: «ara yol» jetonları, Açık/Koyu seçici, ilk boyama betiği, önizleme kalıntısı yok, müşteri/koyu dokunulmadı", () => {
  const css = oku("index.css");
  assert.match(css, /:root\[data-yuz="platform"\]\[data-tema="acik"\] \{\n  --zemin: #F7F7F8; --yan: #FBFBFC; --kart: #FFFFFF;/);
  assert.match(css, /--metin: #0A0A0A; --ikincil: #3F3F42; --soluk: #66666B;/);
  assert.match(css, /--plat-vurgu: #3D6BCB; --plat-vurgu-acik: #2A52A8;/);
  assert.doesNotMatch(css, /data-palet|ÖNİZLEME/);
  assert.match(css, /^:root \{[^]*?--zemin: #E8EAEE; --kart: #FFFFFF;/);                   // müşteri açık yüzü aynen (dosya başı)
  assert.match(css, /\[data-tema="koyu"\] \{\n[^]*?--zemin: #0B0E15; --kart: #181B23;/);   // koyu yüz aynen
  const kab = oku("features/yonetim/PlatformKabugu.tsx");
  assert.match(kab, /<div className="seg" role="group" aria-label="Tema">/);
  assert.match(kab, /aria-pressed=\{tema\.kip === "acik"\}[^]*?aria-pressed=\{tema\.kip === "koyu"\}/);
  assert.doesNotMatch(kab, /onizleme|PALET/);
  const kok = oku("features/yonetim/Yonetim.tsx");
  assert.match(kok, /localStorage\.setItem\("pvq_platform_tema", k\)/);
  assert.match(kok, /kok\.classList\.add\("tema-gecisi"\)/);
  assert.doesNotMatch(kok, /onizleme|paletler/);
  const html = readFileSync(new URL("../../index.html", import.meta.url), "utf8");
  assert.match(html, /localStorage\.getItem\("pvq_platform_token"\)\)\{d\.dataset\.yuz="platform";d\.dataset\.tema=localStorage\.getItem\("pvq_platform_tema"\)==="koyu"\?"koyu":"acik";return;\}/);
});
