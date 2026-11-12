// v2.608 (Faz 5 F5-E) — aşamalı açılım bekçisi: seyrek kullanılan ayarlar `details` (parcalar.Katla) altında, ama HİÇBİR alan kaldırılmadı
// (bağlı girdiler kaynakta duruyor, aynı Kaydet yazar); piyasa kimliği, tarife, işletme ve alarm satırları açık; Kalibrasyon'da
// «Gerçekleşen kayıp ayrışımı» ve «Hava verisi tutarlılığı» gövdeleri katlı, hüküm başlık çipinde kalır.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL("../../src/" + yol, import.meta.url), "utf8");
const santralim = oku("features/santralim/Santralim.tsx");
const digerleri = oku("features/sayfalar/Digerleri.tsx");
const parcalar = oku("features/sayfalar/parcalar.tsx");
const css = oku("index.css");

test("Katla: yerleşik details + summary; açık başlatma yalnız dışarıdan sinyalle", () => {
  assert.match(parcalar, /export function Katla\(\{ ozet, not, acik, className, children \}/);
  assert.match(parcalar, /<details ref=\{ref\} className=\{`katla\$\{className \? " " \+ className : ""\}`\}>/);
  assert.match(parcalar, /if \(acik && ref\.current\) ref\.current\.open = true;/);   // sinyal yalnız açar
  assert.match(parcalar, /<summary><span className="katla-ad">\{ozet\}<\/span>/);
  assert.match(css, /\.katla > summary::before \{ content: ""/);
  assert.match(css, /\.ayar-gelismis > summary \{ font-family: var\(--display\)/);
});

test("Santral ayarları: gelişmiş olanlar katlı, iş kritik satırlar açık; sıra korunur", () => {
  const konum = (metin: string) => { const i = santralim.indexOf(metin); assert.ok(i >= 0, `${metin} kaynakta yok`); return i; };
  const gelismis = konum('<Katla className="ayar-gelismis" ozet="Gelişmiş ayarlar"');
  // açık kalanlar «Gelişmiş ayarlar»dan ÖNCE
  for (const ad of ["Piyasa segmenti", "Dengeden Sorumlu Grup (DSG)", "UEVÇB kodu", "Satış tarifesi", "İşletme ayarları", "Alarm kuralları ve bildirimler"])
    assert.ok(konum(`<div className="ayar-ad">${ad}</div>`) < gelismis, `${ad} açık kalmalı`);
  // fiziksel model terimleri «Gelişmiş ayarlar» içinde
  assert.ok(konum('<div className="ayar-ad">Fiziksel model terimleri</div>') > gelismis);
  assert.ok(konum('ayrintiDugmesi(ayrinti, setAyrinti, "fizik")') > gelismis);
  // satır içi katlamalar: işletme gelişmiş alanları Kaydet'in üstünde, alarm eşikleri alıcılardan önce
  const isletme = konum('<Katla className="form-tam" ozet="Gelişmiş alanlar"');
  assert.ok(isletme < konum('<button className="dugme" onClick={eakKaydet}>Ayarları kaydet</button>'));
  assert.ok(konum('checked={dengelemeBirimi}') > isletme && konum('value={dosyaSiklik}') > isletme && konum('value={teminatKat}') > isletme && konum('value={arizaAy}') > isletme);
  assert.ok(konum('value={eakKw}') < isletme && konum('value={butceMwh}') < isletme && konum('value={sonTemizlik}') < isletme, "EAK, bütçe, temizlik açık kalır");
  const esik = konum('<Katla className="form-tam" ozet="Eşikleri düzenle"');
  assert.ok(esik < konum('<div className="etiket-ust form-tam">Bildirim alıcıları</div>') && konum("{ESIK_ALANLARI.map((a) => (") > esik);
  assert.ok(konum("value={akAlici}") > esik, "alıcılar açık kalır (katla sonrası)");
  // sensör kartı: gövde katlı, vadesi geçen sensör varsa açık
  assert.match(santralim, /<Katla ozet="Sensör envanteri ve ekleme" not=\{vadeGecti \? [^}]+\} acik=\{vadeGecti\}>/);
  assert.match(santralim, /const vadeGecti = !!sens\?\.sensorler\.some\(\(x\) => x\.durum === "gecti"\);/);
  assert.ok(santralim.includes("onClick={() => sensKaydet([...(sens?.sensorler ?? [])"), "sensör ekleme formu duruyor");
});

test("hiçbir alan kaldırılmadı: her bağlı girdi tam bir kez kaynakta", () => {
  for (const g of ["value={eakKw}", "value={gecKw}", "value={gecBitis}", "value={pozKaynak ?? \"program\"}", "value={pozSabit}", "checked={dengelemeBirimi}", "checked={!!luyIstisna}",
    "value={butceMwh}", "value={prRef}", "value={kullSoz}", "value={sonTemizlik}", "value={temizlikTl}", "value={dosyaSiklik}", "value={teminatKat}", "value={arizaAy}",
    "value={akEsik[a.k] ?? \"\"}", "value={akAlici}", "value={ftSon[k] ?? ft[k]}", "value={sf.marka_model}", "value={sf.kalibrasyon_tarihi}"])
    assert.equal(santralim.split(g).length - 1, 1, `${g} tam bir kez`);
  assert.equal(santralim.split('<Katla').length - 1, 4, "Santralim'de 4 katlama: işletme, eşik, gelişmiş ayarlar, sensör");
});

test("Kalibrasyon: kayıp ayrışımı ve hava verisi tutarlılığı gövdeleri katlı; hüküm çipte, kayma varsa açık", () => {
  const kayip = digerleri.indexOf('<Kart baslik="Gerçekleşen kayıp ayrışımı"'); const hava = digerleri.indexOf('<Kart baslik="Hava verisi tutarlılığı"');
  assert.ok(kayip > 0 && hava > kayip);
  const k1 = digerleri.indexOf('<Katla ozet="Nedene göre kayıp tablosu"'); assert.ok(k1 > kayip && k1 < hava);
  assert.ok(digerleri.indexOf("<th>KPI'dan dışlanır</th>") > k1, "ayrışım tablosu duruyor");
  const k2 = digerleri.indexOf('<Katla ozet="Girdi karşılaştırması"'); assert.ok(k2 > hava);
  assert.match(digerleri, /acik=\{ky\?\.hukum === "KAYMA"\}>/);
  assert.ok(digerleri.indexOf("<th>Dağılım farkı (PSI)</th>") > k2, "girdi tablosu duruyor");
  assert.ok(digerleri.slice(hava, k2).includes("ky.hukum]"), "hüküm başlık çipinde kalır");
  // boş/yükleniyor durumu katlanmaz: ternary Katla'dan ÖNCE, YerTutucu ve boş metin Katla'nın dışında
  assert.ok(digerleri.indexOf("{kyp === undefined ? <YerTutucu") < k1 && digerleri.indexOf("{ky === undefined ? <YerTutucu") < k2);
  assert.ok(digerleri.indexOf("Karşılaştırma henüz yapılamadı") > digerleri.indexOf("</Katla>", k2), "boş durum katlamanın dışında");
});
