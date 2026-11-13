/** Sahte API — canlıda ölçülen sunucu süreleriyle (24.10, Deneme Lab kiracısı, konteyner içi sıcak):
 *  /v1/portfoy ≈ 270 ms · /v1/portfoy/tahmin ≈ 400 ms sonra 500 · /v1/portfoy/dsg ≈ 1000 ms · diğer GET'ler ≈ 60 ms.
 *  node sahte-api.mjs [port=4807] ; GET /_log istek günlüğü (zaman, yol), POST /_sifirla günlüğü temizler. */
import http from "node:http";
const PORT = Number(process.argv[2] ?? 4807);
let DAMGA_SURUM = 1;   // 26.10 eşzamanlama sınaması
const LAT = { "/v1/portfoy": 270, "/v1/portfoy/tahmin": 400, "/v1/portfoy/dsg": 1000, "/v1/plants": 60, "/v1/oturum/yenile": 60 };
const gunluk = [];
const santral = (id, ad, kwp, wm, b, y, al, son, kes) => ({ id, ad, kapasite_kwp: kwp, tz: "Europe/Istanbul", segment: null, son_olcum: son, kesinti_gun: kes, wmape_30g: wm, bugun_kwh: b, yarin_kwh: y, acik_alarm: al, son_kosu: "2026-10-23T15:42:00Z" });
const PORTFOY = { gun: "2026-10-24", santraller: [
  santral("a1", "Edikli GES", 15230, 37.5, 65400, 64200, 0, "2026-10-22T20:00:00Z", 1), santral("a2", "Format Lab", 1000, null, 4383, 4330, 3, "2020-06-17T20:00:00Z", 2319),
  santral("a3", "Karapınar RT-2579", 260000, 29.2, 1446500, 1486300, 0, "2026-10-22T20:00:00Z", 1), santral("a4", "Kıvanç 2 GES", 52500, 33.7, 282200, 275400, 0, "2026-10-22T20:00:00Z", 1),
  santral("a5", "PVDAQ Golden 33", 2, null, 3, 8, 3, "2019-01-01T06:00:00Z", 2852) ],
  toplam: { santral: 5, kapasite_kwp: 328732, bugun_kwh: 1798700, yarin_kwh: 1830200, wmape_agirlikli: 30.3, wmape_kapsanan_kwp: 327730, acik_alarm: 6, veri_gecikmis: 2 } };
const DSG = { santral: 5, n_saat: 480, ayri_tl: 412300, net_tl: 301900, kazanc_tl: 110400, kazanc_pct: 26.8, sapma_net_mwh: 118.2, sapma_ayri_mwh: 161.5, pencere_gun: 30, fiyat: { epias_saat: 0, senaryo_saat: 480 }, not: "Senaryo fiyatıyla; EPİAŞ fiyatı bağlanınca gerçek fiyat kullanılır." };
const PLANTS = PORTFOY.santraller.map((s) => ({ id: s.id, name: s.ad, capacity_kwp: s.kapasite_kwp, tz: s.tz }));
// ---- v2.520 (P5a): YEKDEM ilanları modül kapsamında — PUT ile eklenen satır sonraki GET'te görünür (01.11 incelemesi)
// ---- v2.520 (P5a): YEKDEM aylık ilanı + TCMB kur arşivi (gerçek servis çıktısından; band konumu Eylül ortalama kuruyla)
const YF = (ay, tip, f, y, bant) => ({ ay, tesis_tipi: tip, fiyat_kr_kwh: f, yerli_katki_kr_kwh: y, kaynak: "EPİAŞ duyurusu 01.10.2026 (7189 sayılı CK Ek-2 aylık güncelleme)", guncelleme: "2026-11-01T00:09:50Z", kayit: { durum: "resmi", neden: "EPİAŞ duyurusu 01.10.2026" },
  bant: bant ?? { durum: "kur_yok", usd_cent: null, kur_ortalama: null, kur_ayi: ay.slice(0, 5) + String(Number(ay.slice(5)) - 1).padStart(2, "0"), taban_cent: tip === "gunes" ? 4.95 : 5.85, tavan_cent: tip === "gunes" ? 6.05 : 7.15, taban_kr: null, tavan_kr: null } });
const BANT_EKIM = { durum: "icinde", usd_cent: 5.967, kur_ortalama: 48.553, kur_ayi: "2026-09", taban_cent: 4.95, tavan_cent: 6.05, taban_kr: 240.34, tavan_kr: 293.75 };
const BANT_EYLUL = { durum: "icinde", usd_cent: 5.961, kur_ortalama: 47.7783, kur_ayi: "2026-08", taban_cent: 4.95, tavan_cent: 6.05, taban_kr: 236.5, tavan_kr: 289.06 };
const BANT_AGUSTOS = { durum: "icinde", usd_cent: 5.936, kur_ortalama: 46.9845, kur_ayi: "2026-07", taban_cent: 4.95, tavan_cent: 6.05, taban_kr: 232.57, tavan_kr: 284.26 };
const YEKDEM_Y = { bugun: "2026-11-01", bekleyen: [{ ay: "2026-11", tesis_tipi: "gunes" }, { ay: "2026-11", tesis_tipi: "gunes_depolamali" }], fiyatlar: [YF("2026-10", "gunes", 289.74, 78.74, BANT_EKIM), YF("2026-10", "gunes_depolamali", 341.74, null, { ...BANT_EKIM, usd_cent: 7.038, taban_cent: 5.85, tavan_cent: 7.15, taban_kr: 284.04, tavan_kr: 347.15 }),
    YF("2026-09", "gunes", 284.81, 77.40, BANT_EYLUL), YF("2026-09", "gunes_depolamali", 335.93, null, { ...BANT_EYLUL, usd_cent: 7.031, taban_cent: 5.85, tavan_cent: 7.15, taban_kr: 279.5, tavan_kr: 341.61 }),
    YF("2026-08", "gunes", 278.92, 75.80, BANT_AGUSTOS), YF("2026-08", "gunes_depolamali", 328.98, null, { ...BANT_AGUSTOS, usd_cent: 7.002, taban_cent: 5.85, tavan_cent: 7.15, taban_kr: 274.86, tavan_kr: 335.94 })],
  tesis_tipleri: ["gunes", "gunes_depolamali"], tesis_etiket: { gunes: "güneş", gunes_depolamali: "bütünleşik depolamalı güneş" }, bant_cent: { gunes: [4.95, 6.05], gunes_depolamali: [5.85, 7.15] },
  baslangic_kr: { gunes: [106, 28.8], gunes_depolamali: [125, 38.45] }, kaynak_notu: "EPİAŞ aylık YEKDEM fiyat duyurusu (7189 sayılı CK Ek-2); kur TCMB",
  kur: { son_gun: "2026-10-30", son_usd_alis: 49.7747, son_eur_alis: 55.7149, gun_sayisi: 85, ilk_gun: "2026-07-01", eksik_is_gunu_30: [], kaynak: "TCMB gösterge döviz alış kuru (today.xml ve günlük arşiv); iş günü 15:30 bülteni, yarım günlerde bülten yok", kaynak_url: "https://www.tcmb.gov.tr/kurlar/kurlar_tr.html" },
  kaynaklar: { epias_url: "https://www.epias.com.tr/tum-duyurular/piyasa-duyurulari/elektrik/kayit-ve-uzlastirma/01-07-2021-tarihinden-31-12-2030-tarihine-kadar-isletmeye-girecek-yek-belgeli-yenilenebilir-enerji-kaynaklarina-dayali-elektrik-uretim-tesisleri-icin-uygulanacak-fiyatlar-hk-38/", epias_baslik: "EPİAŞ duyurusu (01.10.2026)", tcmb_url: "https://www.tcmb.gov.tr/kurlar/kurlar_tr.html", mevzuat: "7189 sayılı Cumhurbaşkanı Kararı (RG 1.5.2023-32177) Ek-1 fiyat ve sınırlar, Ek-2 aylık güncelleme" } };

http.createServer((req, res) => {
  const url = new URL(req.url, "http://x"); const yol = url.pathname; const t = performance.now();
  res.setHeader("Access-Control-Allow-Origin", "*"); res.setHeader("Access-Control-Allow-Headers", "authorization,content-type,if-none-match"); res.setHeader("Access-Control-Expose-Headers", "ETag"); res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
  if (req.method === "OPTIONS") { res.writeHead(204); return res.end(); }
  if (yol === "/_log") { res.setHeader("content-type", "application/json"); return res.end(JSON.stringify(gunluk)); }
  if (yol === "/_sifirla") { gunluk.length = 0; return res.end("ok"); }
  gunluk.push({ t: Math.round(performance.now()), m: req.method, yol: yol + url.search });
  const gec = LAT[yol] ?? 60;
  const yanit = (kod, govde, ek = {}) => setTimeout(() => { res.writeHead(kod, { "content-type": "application/json", "cache-control": "no-cache", ...ek }); res.end(JSON.stringify(govde)); }, gec);
  // ---- 24.10 Faz 2: platform yönetimi (/v1/yonetim/*) — kareler için; PLATFORM_2FA=1 → sahip 2FA açık
  const PJ = "x." + Buffer.from('{"sub":"p1","kapsam":"platform","rol":"sahip","sv":0}').toString("base64url") + ".y";
  const totpAcik = !!process.env.PLATFORM_2FA;
  if (yol === "/v1/yonetim/giris") return yanit(200, { token: PJ, rol: "sahip", email: "sahip@pvquant.com", iki_adim_kurulmali: !totpAcik });
  if (yol === "/v1/yonetim/oturum/yenile") return yanit(200, { token: PJ, rol: "sahip", email: "sahip@pvquant.com", iki_adim_kurulmali: !totpAcik });
  if (yol === "/v1/yonetim/ben") return yanit(200, { id: "p1", email: "sahip@pvquant.com", rol: "sahip", totp_aktif: totpAcik, son_giris: "2026-10-24T21:48:28Z", olusturma: "2026-10-24T20:40:00Z" });
  if (yol === "/v1/yonetim/iki-adim/baslat") return yanit(200, { secret: "JBSWY3DPEHPK3PXP7F2A6RT4Q5XZ", otpauth_uri: "otpauth://totp/PVQuant%20Platform:sahip%40pvquant.com?secret=JBSWY3DPEHPK3PXP3PXP&issuer=PVQuant%20Platform" });
  if (yol === "/v1/yonetim/iki-adim/dogrula") return yanit(200, { tamam: true });
  const KIRACILAR = [
    { id: "19bf0a66-39dc-42e5-a9bb-269466de3f7a", ad: "Meridyen Enerji", plan: "pilot", durum: "active", olusturma: "2026-07-12T09:00:00Z", guncelleme: null, notlar: "Referans kiracı.", santral: 1, kurulu_guc_kwp: 4514, kullanici: 2, son_giris: "2026-10-24T18:10:00Z" },
    { id: "e190f269-637e-4459-af54-27a7e08095c7", ad: "Deneme Lab", plan: "pilot", durum: "active", olusturma: "2026-09-02T14:20:00Z", guncelleme: "2026-10-24T20:00:00Z", notlar: null, santral: 5, kurulu_guc_kwp: 328732, kullanici: 1, son_giris: "2026-10-24T20:15:00Z" },
    { id: "7c1d2e3f-0000-4000-8000-000000000003", ad: "Askıdaki Enerji", plan: "standart", durum: "suspended", olusturma: "2026-08-15T10:00:00Z", guncelleme: "2026-10-20T09:00:00Z", notlar: "Ödeme bekleniyor.", santral: 2, kurulu_guc_kwp: 12000, kullanici: 0, son_giris: "2026-10-01T07:30:00Z" }];
  if (yol === "/v1/yonetim/kiracilar" && req.method === "GET") return yanit(200, { kiracilar: KIRACILAR });
  if (yol === "/v1/yonetim/kiracilar" && req.method === "POST") return yanit(201, { tenant_id: "yeni-1", user_id: "u-yeni", davet_gonderildi: false, davet_baglantisi: "https://pvquant.com/parola-yenile?jeton=ORNEK-JETON-DEGERI-UZUN-UZUN" });
  if (/^\/v1\/yonetim\/kiracilar\/[^/]+$/.test(yol) && req.method === "GET") { const k = KIRACILAR[1]; return yanit(200, { ...k, kullanicilar: [
      { id: "u1", email: "deneme@example.com", rol: "admin", aktif: true, totp_aktif: true, son_giris: "2026-10-24T20:15:00Z", olusturma: "2026-09-02T14:20:00Z" },
      { id: "u2", email: "izleyici@example.com", rol: "viewer", aktif: false, totp_aktif: false, son_giris: null, olusturma: "2026-09-10T10:00:00Z" }],
    santraller: PORTFOY.santraller.map((s, i) => ({ id: s.id, ad: s.ad, kapasite_kwp: s.kapasite_kwp, tz: s.tz, arsivli: false, olusturma: "2026-09-02T14:30:00Z", son_scada: s.son_olcum, son_kosu: s.son_kosu, segment: i === 0 ? "lisansli_serbest" : null, uevcb: i === 0 ? "40X000000000123A" : null, kgup_yukumlu: i === 0 ? true : null })) }); }
  if (/^\/v1\/yonetim\/kiracilar\/[^/]+$/.test(yol) && req.method === "PUT") return yanit(200, { tamam: true, eski: {}, yeni: {} });
  if (yol === "/v1/yonetim/kullanicilar" && req.method === "GET") return yanit(200, { kullanicilar: [
      { id: "u1", email: "deneme@example.com", rol: "admin", aktif: true, totp_aktif: true, son_giris: "2026-10-24T20:15:00Z", olusturma: "2026-09-02T14:20:00Z", tenant_id: KIRACILAR[1].id, firma: "Deneme Lab" },
      { id: "u3", email: "ops@meridyen.example", rol: "admin", aktif: true, totp_aktif: false, son_giris: "2026-10-24T18:10:00Z", olusturma: "2026-07-12T09:00:00Z", tenant_id: KIRACILAR[0].id, firma: "Meridyen Enerji" },
      { id: "u2", email: "izleyici@example.com", rol: "viewer", aktif: false, totp_aktif: false, son_giris: null, olusturma: "2026-09-10T10:00:00Z", tenant_id: KIRACILAR[1].id, firma: "Deneme Lab" }] });
  // 26.10 denetim-3: posta gitmezse bağlantı yalnız sahibe; OPERATOR=1 ile operatör yanıtı (bağlantısız, yalnız not) taklit edilir
  if (/^\/v1\/yonetim\/kullanicilar\//.test(yol)) return yanit(200, yol.endsWith("parola-sifirlama")
    ? (process.env.OPERATOR ? { gonderildi: false, not: "posta gönderilemedi; bağlantıyı yalnız sahip görebilir, sahipten isteyin" } : { gonderildi: false, baglanti: "https://pvquant.com/parola-yenile?jeton=ORNEK" })
    : { tamam: true });
  if (yol === "/v1/yonetim/basvurular") return yanit(200, { basvurular: [
      { id: "b1", eposta: "ali@gunesenerji.example", santral_adi: "Konya 2 GES", kurulu_guc_kwp: 9800, okundu: false, created_at: "2026-10-24T11:05:00Z" },
      { id: "b2", eposta: "info@tarimsal.example", santral_adi: null, kurulu_guc_kwp: null, okundu: true, created_at: "2026-10-19T08:40:00Z" }] });
  if (/^\/v1\/yonetim\/basvurular\//.test(yol)) return yanit(200, { tamam: true });
  if (yol === "/v1/yonetim/operatorler" && req.method === "GET") return yanit(200, { operatorler: [
      { id: "p1", email: "sahip@pvquant.com", rol: "sahip", aktif: true, totp_aktif: true, son_giris: "2026-10-24T21:48:28Z", olusturma: "2026-10-24T20:40:00Z" },
      { id: "p2", email: "destek@pvquant.com", rol: "operator", aktif: true, totp_aktif: false, son_giris: null, olusturma: "2026-10-25T08:00:00Z" },
      { id: "p4", email: "nobet@pvquant.com", rol: "operator", aktif: true, totp_aktif: true, son_giris: "2026-10-26T06:10:00Z", olusturma: "2026-10-25T12:00:00Z" }], roller: ["operator", "sahip"] });   // 26.10: 2FA'lı operatör («2FA sıfırla» + yeniden doğrulama kartı)
  if (yol === "/v1/yonetim/operatorler" && req.method === "POST") return yanit(201, { id: "p3", email: "yeni@pvquant.com", rol: "operator", aktif: true, totp_aktif: false, son_giris: null, olusturma: "2026-10-25T09:00:00Z", gecici_parola: "Xy9-ornek-gecici" });
  if (/^\/v1\/yonetim\/operatorler\//.test(yol)) return yanit(200, { tamam: true });
  if (yol === "/v1/yonetim/parola") return yanit(200, { tamam: true });
  // ---- 25.10 Faz 3: sistem izleme (/v1/yonetim/{sistem,isler,santraller}) — zamanlar «şimdi»ye göre, hükümler uçtan
  const dkOnce = (dk) => new Date(Date.now() - dk * 60000).toISOString();
  const NABIZ_SESSIZ = !!process.env.NABIZ_SESSIZ;   // NABIZ_SESSIZ=1 → zamanlayıcı sessiz, gece turu bayat (uyarı tonları)
  if (yol === "/v1/yonetim/yekdem") return yanit(200, YEKDEM_Y);
  if (yol === "/v1/yonetim/yekdem-fiyat" && req.method === "PUT") { let g = ""; req.on("data", (c) => { g += c; }); req.on("end", () => { let b = {}; try { b = JSON.parse(g || "{}"); } catch { /* yok */ }
      const m = /(\d{1,2})\.(\d{1,2})\.(\d{4})/.exec(b.kaynak ?? ""); const kt = m ? new Date(+m[3], +m[2] - 1, +m[1]) : null;
      const ret = (d) => { res.writeHead(422, { "Content-Type": "application/json; charset=utf-8" }); res.end(JSON.stringify({ detail: d })); };
      if (!b.kaynak) return ret("kaynak gerekli: duyurunun adı ve tarihi (ör. «EPİAŞ duyurusu 01.10.2026»)");
      if (!kt) return ret("kaynakta duyuru tarihi olmalı (gg.aa.yyyy)");
      if (kt > new Date()) return ret(`kaynak tarihi (${m[0]}) bugünden sonra olamaz`);
      const donem = new Date(+String(b.ay).slice(0, 4), +String(b.ay).slice(5, 7) - 1, 1);
      if (new Date(kt.getFullYear(), kt.getMonth(), 1) < donem) return ret(`kaynak tarihi (${m[0]}) geçerli dönemden (${String(b.ay).slice(5, 7)}.${String(b.ay).slice(0, 4)}) önce: EPİAŞ bir ayın fiyatını o ayın başında ya da sonra ilan eder, bu duyuru o dönemi içeremez`);
      const KUR = { "2026-10": 49.334, "2026-09": 48.553, "2026-08": 47.7783, "2026-07": 46.9845 };   // gerçek arşivden aylık ortalama USD alış
      const onceki = `${donem.getMonth() === 0 ? donem.getFullYear() - 1 : donem.getFullYear()}-${String(donem.getMonth() === 0 ? 12 : donem.getMonth()).padStart(2, "0")}`;
      const tip = b.tesis_tipi ?? "gunes"; const [taban, tavan] = tip === "gunes" ? [4.95, 6.05] : [5.85, 7.15]; const ko = KUR[onceki];
      const bant = ko ? (() => { const c = Number(b.fiyat_kr_kwh) / ko; return { durum: c <= taban + 0.02 ? "tabanda" : c >= tavan - 0.02 ? "tavanda" : "icinde", usd_cent: +c.toFixed(3), kur_ortalama: ko, kur_ayi: onceki, taban_cent: taban, tavan_cent: tavan, taban_kr: +(taban * ko).toFixed(2), tavan_kr: +(tavan * ko).toFixed(2), kur_gun: 20, kur_beklenen: 20, kur_eksik_gun: [] }; })() : undefined;
      const f = YF(b.ay, tip, Number(b.fiyat_kr_kwh), b.yerli_katki_kr_kwh ?? null, bant); f.kaynak = b.kaynak; f.guncelleme = new Date().toISOString();
      f.kayit = /epia/i.test(b.kaynak.normalize("NFD").replace(/[\u0300-\u036f]/g, "")) ? { durum: "resmi", neden: `EPİAŞ duyurusu ${m[0]}` } : { durum: "elle", neden: "kaynak EPİAŞ duyurusu olarak yazılmadı" };
      const i = YEKDEM_Y.fiyatlar.findIndex((x) => x.ay === f.ay && x.tesis_tipi === f.tesis_tipi); if (i >= 0) YEKDEM_Y.fiyatlar[i] = f; else YEKDEM_Y.fiyatlar.unshift(f);
      YEKDEM_Y.bekleyen = YEKDEM_Y.bekleyen.filter((x) => !(x.ay === f.ay && x.tesis_tipi === f.tesis_tipi));
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" }); res.end(JSON.stringify(f)); }); return; }
  if (yol === "/v1/yonetim/kur-doldur" && req.method === "POST") return yanit(200, { yazilan: 1, bulunamayan: ["2026-10-28"], bas: "2026-10-01", bit: "2026-10-31" });
  // v2.608 (Faz 5 F5-D): iki sağlık görünümü — /sistem ham özeti (SISTEM) + sınıflanmış teknik sağlık + müşteri hizmet sağlığı
  const SISTEM = ({
    zaman: dkOnce(0),
    nabiz: NABIZ_SESSIZ ? { durum: "sessiz", son: dkOnce(47), yas_dk: 47, ayrinti: { baslatma: dkOnce(900), is_sayisi: 21, aralik_dk: 5 }, aralik_dk: 5, sessiz_dk: 15 }
                        : { durum: "calisiyor", son: dkOnce(3), yas_dk: 3, ayrinti: { baslatma: dkOnce(900), is_sayisi: 21, aralik_dk: 5 }, aralik_dk: 5, sessiz_dk: 15 },
    gece_turu: NABIZ_SESSIZ ? { taze: false, bayat_isler: ["Sabah tahmini"], son: dkOnce(60 * 31), esik_saat: 30, uretici_isler: [
        { kod: "sabah_tahmin", is: "Sabah tahmini", son_ok: dkOnce(60 * 55) }, { kod: "gece_skill", is: "Gece karnesi", son_ok: dkOnce(60 * 7) }, { kod: "gunluk_beklenti", is: "Günlük beklenti", son_ok: dkOnce(60 * 7) }] }
      : { taze: true, bayat_isler: [], son: dkOnce(60 * 7), esik_saat: 30, uretici_isler: [
        { kod: "sabah_tahmin", is: "Sabah tahmini", son_ok: dkOnce(60 * 7) }, { kod: "gece_skill", is: "Gece karnesi", son_ok: dkOnce(60 * 8) }, { kod: "gunluk_beklenti", is: "Günlük beklenti", son_ok: dkOnce(60 * 8) }] },
    isler_24: { toplam: 86, hata: NABIZ_SESSIZ ? 4 : 1 },
    meteo: { esik_saat: 36, kaynaklar: [
      { kaynak: "ICON-EU", son_indirme: dkOnce(60 * 8), nokta: 6, satir: 184320, ilk: "2026-07-12T00:00:00+00:00", son_ts: dkOnce(-60 * 96), yas_saat: 8.1, bayat: false },
      { kaynak: "GFS", son_indirme: dkOnce(60 * 8), nokta: 6, satir: 391680, ilk: "2026-07-12T00:00:00+00:00", son_ts: dkOnce(-60 * 384), yas_saat: 8.2, bayat: false },
      { kaynak: "GEFS üyeleri", son_indirme: dkOnce(60 * 50), nokta: 6, satir: 1105920, ilk: "2026-08-01T00:00:00+00:00", son_ts: dkOnce(-60 * 200), yas_saat: 50.3, bayat: true }] },
    // v2.516 inceleme: gerçekleşen fiyat DÜNÜN son saatine kadar (gece dünü çeker); ileri tarih yalnız gün öncesi PTF (gop_son = yarın)
    piyasa: { son_ts: dkOnce(60 * 26), son_guncelleme: dkOnce(60 * 8), satir: 2520, yas_saat: 8.0, esik_saat: 36, bayat: false,
      // v2.516 (#4): kimlik + yön kapsamı + gün öncesi PTF ufku; NABIZ_SESSIZ=1 → yön 2 gündür eksik (uyarı tonu)
      kimlik: true, yon_son: NABIZ_SESSIZ ? dkOnce(60 * 74) : dkOnce(60 * 26), yon_saat_7g: NABIZ_SESSIZ ? 96 : 168, saat_7g: 168, yon_bayat: !!NABIZ_SESSIZ, gop_son: dkOnce(-60 * 20) },
    // v2.516 (#3): izlenen işler — durum uçtan; NABIZ_SESSIZ=1 → «Rapor alanları» 50 saattir koşmamış (bayat)
    izlenen: (() => { const L = [["gun_ici_tahmin", "Gün içi güncelleme", "gün içi", 30, 60 * 2], ["kgup_revizyon_kontrol", "Program revizyonu kontrolü (gün içi)", "gün içi", 30, 60 * 3],
        ["kgup_teslim_kontrol", "Program bildirimi kontrolü (15:35)", "günlük", 36, 60 * 20], ["gun_oncesi_ptf", "Gün öncesi fiyatı (yarının PTF'si)", "günlük", 36, 60 * 21],
        ["gece_piyasa", "Piyasa fiyatları", "günlük", 36, 60 * 8], ["gece_epias_uretim", "Gerçekleşen üretim çekimi", "günlük", 36, 60 * 8], ["alarm", "Alarm taraması", "günlük", 36, 60 * 4],
        ["gece_hijyen", "Veri hijyeni", "günlük", 36, 60 * 8], ["gece_ufuk_sigma", "Ufuk belirsizliği", "günlük", 36, 60 * 8], ["gece_konformal", "Bant kalibrasyonu", "günlük", 36, 60 * 8],
        ["rapor_alanlari", "Rapor alanları", "günlük", 36, NABIZ_SESSIZ ? 60 * 50 : 60 * 8], ["kgup_arsiv_temizlik", "KGÜP arşivi saklama temizliği", "aylık", 840, null], ["denetim_temizlik", "Denetim izi temizliği", "aylık", 840, 60 * 24 * 20]];
      const isler = L.map(([kod, is, siklik, esik, dk]) => { const yas = dk == null ? null : dk / 60; const durum = dk == null ? "henuz_yok" : yas > esik ? "esik_asimi" : "ok";
        return { kod, is, siklik, esik_saat: esik, son_ok: dk == null ? null : dkOnce(dk), yas_saat: yas, durum, not: null }; });
      return { isler, bayat: isler.filter((x) => x.durum === "bayat").map((x) => x.is) }; })(),
    yedek: { son_basarili: dkOnce(60 * 9), yas_saat: 9.2, esik_saat: 30, bayat: false, son_deneme: { zaman: dkOnce(60 * 9), tamam: true, ayrinti: null } },
    db: { boyut_bayt: 2_914_000_000 }, santral: { etkin: 6, arsivli: 1 } });
  if (yol === "/v1/yonetim/sistem") return yanit(200, SISTEM);
  if (yol === "/v1/yonetim/sistem-sagligi") {
    const D = (durum, neden, ek = {}) => ({ durum, etiket: { saglikli: "Sağlıklı", dikkat: "Dikkat gerekiyor", kritik: "Kritik", veri_bekleniyor: "Veri bekleniyor", dogrulanamadi: "Doğrulanamadı", uygulanmiyor: "Uygulanmıyor" }[durum], neden, ...ek });
    const S = NABIZ_SESSIZ;
    const bil = {
      zamanlayici: S ? D("dikkat", "son nabız 47 dk önce (beklenen her 5 dk)", { son: dkOnce(47), yas_dk: 47 }) : D("saglikli", "nabız 3 dk önce", { son: dkOnce(3), yas_dk: 3 }),
      gece_isleri: S ? D("kritik", "30 saattir koşmayan üretici iş: Sabah tahmini", { bayat: ["Sabah tahmini"], son: dkOnce(60 * 31), uretici_isler: SISTEM.gece_turu.uretici_isler, is_hatasi_24: 4 })
                     : D("saglikli", "üretici ve izlenen işler eşik içinde", { bayat: [], son: dkOnce(60 * 7), uretici_isler: SISTEM.gece_turu.uretici_isler, is_hatasi_24: 1 }),
      hava: D("dikkat", "eski kaynak: GEFS üyeleri (50 saat)", { son_indirme: dkOnce(60 * 8), en_yeni_kosu: dkOnce(-60 * 384), kaynak_sayisi: 3, esik_saat: 36, son_is: { zaman: dkOnce(60 * 8), tamam: true, ayrinti: null } }),
      epias: S ? D("dikkat", "sistem yönü eksik ya da fiyatın bir günden fazla gerisinde", { kimlik: true, son_baglanti: { zaman: dkOnce(60 * 8), tamam: true, ayrinti: null }, son_veri_alimi: dkOnce(60 * 8), en_yeni_kayit: dkOnce(60 * 26), yon_son: dkOnce(60 * 74), yon_saat_7g: 96, gop_son: dkOnce(-60 * 20), epias_uretim: { zaman: dkOnce(60 * 8), tamam: true, ayrinti: null } })
               : D("saglikli", "kimlik var, son istek başarılı, fiyat ve yön güncel", { kimlik: true, son_baglanti: { zaman: dkOnce(60 * 8), tamam: true, ayrinti: null }, son_veri_alimi: dkOnce(60 * 8), en_yeni_kayit: dkOnce(60 * 26), yon_son: dkOnce(60 * 26), yon_saat_7g: 168, gop_son: dkOnce(-60 * 20), epias_uretim: { zaman: dkOnce(60 * 8), tamam: true, ayrinti: null } }),
      veritabani: D("dogrulanamadi", "geri yükleme sınaması yapılmıyor; yedek dosyasının açılabilirliği sınanmadı", {
        baglanti: D("saglikli", "özet sorguları yanıt verdi", { boyut_bayt: 2_914_000_000 }), yedek: D("saglikli", "son başarılı yedek 9 saat önce", { son_basarili: dkOnce(60 * 9), son_deneme: { zaman: dkOnce(60 * 9), tamam: true, ayrinti: null }, esik_saat: 30 }),
        yedek_dogrulama: D("dogrulanamadi", "geri yükleme sınaması yapılmıyor; yedek dosyasının açılabilirliği sınanmadı") }),
      sunucu: D("dogrulanamadi", "uygulama ve API hata günlüğü panele bağlı değil; sunucu günlüğüne bakılır", {
        api: D("saglikli", "bu yanıt API tarafından üretildi; ayrı dış yoklama yok"), hata_gunlugu: D("dogrulanamadi", "uygulama ve API hata günlüğü panele bağlı değil; sunucu günlüğüne bakılır"),
        is_hatalari: S ? D("dikkat", "son 24 saatte 4 başarısız iş (86 kayıt)") : D("dikkat", "son 24 saatte 1 başarısız iş (86 kayıt)") }) };
    const durumlar = Object.values(bil).map((b) => b.durum); const sira = ["kritik", "dikkat", "dogrulanamadi", "veri_bekleniyor", "saglikli", "uygulanmiyor"];
    const genel = sira.find((d) => durumlar.includes(d));
    return yanit(200, { zaman: dkOnce(0), durum: genel, etiket: bil.zamanlayici.etiket && { saglikli: "Sağlıklı", dikkat: "Dikkat gerekiyor", kritik: "Kritik", dogrulanamadi: "Doğrulanamadı" }[genel],
      sayim: Object.fromEntries(sira.map((d) => [d, durumlar.filter((x) => x === d).length])), bilesenler: bil, sozluk_surumu: "2026-11-12",
      esik: { nabiz_sessiz_dk: 15, nabiz_kritik_dk: 60, gece_saat: 30, meteo_saat: 36, piyasa_saat: 36, yedek_saat: 30 },
      sureler: [["sabah_tahmin", "Sabah tahmini", 7, 0, 412.5, 498.2], ["gece_skill", "Gece karnesi", 7, 0, 88.1, 102.0], ["gece_finansal_etki", "Finansal etki", 7, 1, 61.4, 190.3], ["gece_bagimsiz_dogrulama", "Bağımsız doğrulama", 7, 0, 40.2, 55.0], ["alarm", "Alarm taraması", 7, 0, 12.0, 14.1]]
        .map(([kod, is, n, hata, ort, uzun]) => ({ kod, is, n, hata, ort_sn: ort, en_uzun_sn: uzun, son: dkOnce(60 * 8) })),
      ham: SISTEM, not: "Teknik sağlık: altyapı sinyalleri. Müşteriye kullanılabilir sonuç üretilip üretilmediği ayrı hesaptır (Müşteri hizmet sağlığı)." });
  }
  if (yol === "/v1/yonetim/hizmet-sagligi") {
    const E = { saglikli: "Sağlıklı", dikkat: "Dikkat gerekiyor", kritik: "Kritik", veri_bekleniyor: "Veri bekleniyor", dogrulanamadi: "Doğrulanamadı", uygulanmiyor: "Uygulanmıyor" };
    const B = (durum, neden, ek = {}) => ({ durum, etiket: E[durum], neden, ...ek });
    const sira = ["kritik", "dikkat", "dogrulanamadi", "veri_bekleniyor", "saglikli", "uygulanmiyor"];
    const enKotu = (ds) => { const h = ds.filter((d) => d !== "uygulanmiyor"); return h.length ? sira.find((d) => h.includes(d)) : "uygulanmiyor"; };
    const sayim = (ds) => Object.fromEntries(sira.map((d) => [d, ds.filter((x) => x === d).length]));
    const S = (id, ad, kwp, tenant_id, kiraci, segment, boyutlar) => { const durum = enKotu(Object.values(boyutlar).map((b) => b.durum));
      return { id, ad, kapasite_kwp: kwp, tenant_id, kiraci, kiraci_durum: "active", segment, durum, etiket: E[durum], eylem_gereken: Object.keys(boyutlar).filter((k) => ["kritik", "dikkat"].includes(boyutlar[k].durum)), boyutlar }; };
    const santraller = [
      S("a1", "Edikli GES", 15230, "t1", "Deneme Lab", "lisansli_serbest", { veri: B("saglikli", "ölçüm güncel"), tahmin: B("saglikli", "tahmin güncel ve yarını kapsıyor"), kgup: B("saglikli", "bildirildiği beyan edildi; TPYS kabulü PVQuant'tan doğrulanamaz"), mutabakat: B("saglikli", "2026-09 bildirimi yüklü; EPİAŞ'ın uzlaştırma durumu dosyadan doğrulanmaz"), alarm: B("saglikli", "açık alarm ve süren olay yok") }),
      S("a2", "Format Lab", 1000, "t1", "Deneme Lab", null, { veri: B("kritik", "son geçerli ölçüm 2319 gün önce; karne ve uzlaştırma hesaplanamaz", { en_yeni_kayit: "2020-06-17T20:00:00Z" }), tahmin: B("dikkat", "tahmin, son ölçümden 2319 gün sonra üretildi (düzeltme katmanları eski ölçümle)"), kgup: B("dikkat", "piyasa segmenti seçilmedi; program yükümlülüğü bilinmiyor"), mutabakat: B("dikkat", "piyasa segmenti seçilmedi; uzlaştırma kalemleri hesaplanamaz"), alarm: B("dikkat", "3 okunmamış alarm", { son_is_hatasi: dkOnce(60 * 5) }) }),
      S("a3", "Karapınar RT-2579", 260000, "t2", "Güneş Enerji A.Ş.", "lisansli_yekdem", { veri: B("saglikli", "ölçüm güncel"), tahmin: B("dogrulanamadi", "bağımsız doğrulama kaydı yok"), kgup: B("kritik", "teslim kesimi öncesinde verilmiş tahmin yok"), mutabakat: B("veri_bekleniyor", "2026-10 ön bildirimi 11.11.2026 tarihinde yayımlanır"), alarm: B("saglikli", "açık alarm ve süren olay yok") }),
      S("a4", "Kıvanç 2 GES", 52500, "t2", "Güneş Enerji A.Ş.", "lisanssiz_dagitim", { veri: B("dikkat", "son geçerli ölçüm 3 gün önce"), tahmin: B("saglikli", "tahmin güncel ve yarını kapsıyor"), kgup: B("uygulanmiyor", "bu santral için program bildirimi yükümlülüğü yok"), mutabakat: B("saglikli", "2026-09 bildirimi yüklü; EPİAŞ'ın uzlaştırma durumu dosyadan doğrulanmaz"), alarm: B("saglikli", "açık alarm ve süren olay yok") }),
    ];
    const grup = (liste, id, ad) => { const ds = liste.map((p) => p.durum); const durum = enKotu(ds); const boyut = {};
      for (const b of ["veri", "tahmin", "kgup", "mutabakat", "alarm"]) { const bd = liste.map((p) => p.boyutlar[b].durum); boyut[b] = { durum: enKotu(bd), sayim: sayim(bd) }; }
      return { id, ad, santral: liste.length, durum, etiket: E[durum], sayim: sayim(ds), boyut, dikkat_santral: liste.filter((p) => ["kritik", "dikkat"].includes(p.durum)).map((p) => ({ id: p.id, ad: p.ad, durum: p.durum, eylem_gereken: p.eylem_gereken })) }; };
    const tenant = url.searchParams.get("tenant_id"); const sorunlu = url.searchParams.get("yalniz_sorunlu") === "true";
    const kume = santraller.filter((p) => !tenant || p.tenant_id === tenant);
    const kuruluslar = [["t1", "Deneme Lab"], ["t2", "Güneş Enerji A.Ş."]].filter(([id]) => !tenant || id === tenant).map(([id, ad]) => grup(kume.filter((p) => p.tenant_id === id), id, ad));
    const ds = kume.map((p) => p.durum); const genel = enKotu(ds); const boyut = {};
    for (const b of ["veri", "tahmin", "kgup", "mutabakat", "alarm"]) { const bd = kume.map((p) => p.boyutlar[b].durum); boyut[b] = { durum: enKotu(bd), sayim: sayim(bd) }; }
    return yanit(200, { zaman: dkOnce(0), yarin: "2026-10-25", donem: "2026-09", pencere: { durum: "erken" }, santraller: sorunlu ? kume.filter((p) => ["kritik", "dikkat"].includes(p.durum)) : kume, kuruluslar,
      portfoyler: [{ ...grup(kume.filter((p) => p.tenant_id === "t2"), "pf1", "Konya DSG"), tur: "dsg", tenant_id: "t2" }].filter((g) => g.santral > 0),
      ozet: { santral: kume.length, kurulus: kuruluslar.length, durum: genel, etiket: E[genel], sayim: sayim(ds), boyut, dikkat_kurulus: kuruluslar.filter((k) => ["kritik", "dikkat"].includes(k.durum)).length },
      boyutlar: ["veri", "tahmin", "kgup", "mutabakat", "alarm"], esik: { olcum_dikkat_saat: 48, olcum_kritik_saat: 168, tahmin_dikkat_saat: 30, tahmin_kritik_saat: 72 }, sozluk_surumu: "2026-11-12",
      not: "Hizmet sağlığı teknik iş başarısından bağımsız hesaplanır; TPYS kabulü ve EPİAŞ uzlaştırma durumu doğrulanamaz." });
  }
  // v2.516 (#5): müşteriler arası açık alarm özeti
  if (yol === "/v1/yonetim/alarmlar") return yanit(200, { acik: 6, musteri: 2, santral: 3, en_eski: dkOnce(60 * 60), pencere_gun: 7, kurallar: [
      { kural: "kgup_teslim_gecikti", etiket: "Program bildirimi hazırlanamadı", adet: 3, musteri: 2 }, { kural: "veri_gelmedi", etiket: "Veri gelmedi", adet: 2, musteri: 1 },
      { kural: "skill_dustu", etiket: "Tahmin doğruluğu düştü", adet: 1, musteri: 1 }] });
  if (yol === "/v1/yonetim/isler") { const hepsi = [
      { id: "j1", kod: "sabah_tahmin", is: "Sabah tahmini", tenant_id: "e190f269-637e-4459-af54-27a7e08095c7", kiraci: "Deneme Lab", plant_id: "pl-1", santral: "Format Lab", zaman: dkOnce(60 * 7), sure_sn: 41.2, tamam: false, durum: "error", ayrinti: "KeyError: 'artik' — uzlastirma_service.py:76 (artiklar.reindex)" },
      { id: "j2", kod: "sabah_tahmin", is: "Sabah tahmini", tenant_id: "19bf0a66-39dc-42e5-a9bb-269466de3f7a", kiraci: "Meridyen Enerji", plant_id: "pl-2", santral: "Karapınar 1", zaman: dkOnce(60 * 7 + 1), sure_sn: 38.9, tamam: true, durum: "ok", ayrinti: null },
      { id: "j3", kod: "gece_meteo", is: "Hava verisi indirme", tenant_id: null, kiraci: null, plant_id: null, santral: null, zaman: dkOnce(60 * 8), sure_sn: 1312.4, tamam: true, durum: "ok", ayrinti: null },
      { id: "j4", kod: "gece_skill", is: "Gece karnesi", tenant_id: "e190f269-637e-4459-af54-27a7e08095c7", kiraci: "Deneme Lab", plant_id: "pl-3", santral: "PVDAQ Golden 33", zaman: dkOnce(60 * 8 + 30), sure_sn: 6.1, tamam: true, durum: "ok", ayrinti: "yetersiz veri: 10 günde 3 geçerli gün, atlandı" },
      { id: "j5", kod: "gece_yedek", is: "Veritabanı yedeği", tenant_id: null, kiraci: null, plant_id: null, santral: null, zaman: dkOnce(60 * 9), sure_sn: 12.7, tamam: true, durum: "ok", ayrinti: null }];
    const yalnizHata = /yalniz_hata=true/.test(url.search); const isAdi = (url.searchParams.get("job") || ""); const kiraci = url.searchParams.get("tenant_id") || "";
    return yanit(200, { isler: hepsi.filter((x) => (!yalnizHata || !x.tamam) && (!isAdi || x.kod === isAdi) && (!kiraci || x.tenant_id === kiraci)), pencere_saat: Number(url.searchParams.get("saat") || 48),
      is_turleri: [{ kod: "gece_meteo", is: "Hava verisi indirme" }, { kod: "sabah_tahmin", is: "Sabah tahmini" }, { kod: "gece_skill", is: "Gece karnesi" }, { kod: "gece_yedek", is: "Veritabanı yedeği" }] }); }
  if (yol === "/v1/yonetim/santraller") { const hepsi = [
      { id: "pl-2", ad: "Karapınar 1", kapasite_kwp: 4514, tz: "Europe/Istanbul", olusturma: "2026-07-12T09:10:00Z", tenant_id: "19bf0a66-39dc-42e5-a9bb-269466de3f7a", kiraci: "Meridyen Enerji", kiraci_durum: "active", son_scada: dkOnce(60 * 3), son_kosu: dkOnce(60 * 7), son_hata: null, sorunlar: [], segment: "lisansli_serbest", uevcb: "40X000000000123A", kgup_yukumlu: true, kgup_yarin: { gun: "2026-10-25", oneri_surum: 2, bildirilen: true, eak: true } },
      { id: "pl-1", ad: "Format Lab", kapasite_kwp: 1200, tz: "Europe/Istanbul", olusturma: "2026-09-02T14:30:00Z", tenant_id: "e190f269-637e-4459-af54-27a7e08095c7", kiraci: "Deneme Lab", kiraci_durum: "active", son_scada: dkOnce(60 * 70), son_kosu: dkOnce(60 * 31), son_hata: dkOnce(60 * 7), sorunlar: ["scada_bayat", "kosu_bayat", "segment_yok"], segment: null, uevcb: null, kgup_yukumlu: null, kgup_yarin: { gun: "2026-10-25", oneri_surum: null, bildirilen: false, eak: false } },
      { id: "pl-3", ad: "PVDAQ Golden 33", kapasite_kwp: 1.1, tz: "Etc/GMT+7", olusturma: "2026-09-05T10:00:00Z", tenant_id: "e190f269-637e-4459-af54-27a7e08095c7", kiraci: "Deneme Lab", kiraci_durum: "active", son_scada: null, son_kosu: dkOnce(60 * 7), son_hata: null, sorunlar: ["scada_yok"], segment: "lisanssiz_dagitim", uevcb: null, kgup_yukumlu: false, kgup_yarin: { gun: "2026-10-25", oneri_surum: null, bildirilen: false, eak: false } },
      { id: "pl-4", ad: "Askıdaki GES", kapasite_kwp: 980, tz: "Europe/Istanbul", olusturma: "2026-08-15T10:00:00Z", tenant_id: "7c1d2e3f-0000-4000-8000-000000000003", kiraci: "Askıdaki Enerji", kiraci_durum: "suspended", son_scada: dkOnce(60 * 24 * 12), son_kosu: dkOnce(60 * 24 * 12), son_hata: null, sorunlar: ["scada_bayat", "kosu_bayat", "kiraci_askida", "segment_yok"], segment: null, uevcb: null, kgup_yukumlu: null, kgup_yarin: { gun: "2026-10-25", oneri_surum: 1, bildirilen: false, eak: false } }];
    const sorunlu = /sorunlu=true/.test(url.search);
    return yanit(200, { santraller: hepsi.filter((p) => !sorunlu || p.sorunlar.length > 0), esik: { scada_saat: 48, kosu_saat: 30 }, toplam: hepsi.length, yarin: "2026-10-25" }); }
  // ---- 25.10 Faz 4: kullanım (/v1/yonetim/kullanim[?ay][&tenant_id]) — sayaç + türetilmiş sayımlar
  if (yol === "/v1/yonetim/kullanim") {
    const ay = url.searchParams.get("ay") || new Date().toISOString().slice(0, 7); const tid = url.searchParams.get("tenant_id");
    const T = (dis_api, webhook, webhook_hata, rapor, kosu, scada_saat, yukleme, kgup = 0, kgup_bildirilen = 0) => ({ dis_api, webhook, webhook_hata, rapor, kosu, scada_saat, yukleme, kgup, kgup_bildirilen });   // v2.516 (#6)
    if (tid) { const gunler = []; for (let d = 25; d >= 1; d--) gunler.push({ gun: `${ay}-${String(d).padStart(2, "0")}`, ...T(d % 3 === 0 ? 0 : 40 + d, d % 5 === 0 ? 1 : 0, d === 10 ? 1 : 0, d % 7 === 0 ? 1 : 0, 5, 120, d === 3 ? 1 : 0, d % 2 === 0 ? 1 : 0, d % 6 === 0 ? 1 : 0) });
      return yanit(200, { ay, tenant_id: tid, ad: KIRACILAR.find((k) => k.id === tid)?.ad ?? "Kiracı", gunler }); }
    const [oy, om] = ay.split("-").map(Number); const onceki = `${om === 1 ? oy - 1 : oy}-${String(om === 1 ? 12 : om - 1).padStart(2, "0")}`;
    // v2.609 (F6-B): anlık sayımlar + kota hükümleri uçtan (yetki_service.kota_durumu şekli); kaynak plan | ezme
    const K = (ad, birim, limit, kullanim, kaynak = "plan", not_) => { const oran = limit == null || kullanim == null ? null : limit <= 0 ? null : Math.round(kullanim / limit * 1000) / 1000;
      const durum = kullanim == null ? "olculmuyor" : limit == null ? "sinirsiz" : limit <= 0 ? (kullanim > 0 ? "asildi" : "saglikli") : oran > 1 ? "asildi" : oran >= 1 ? "dolu" : oran >= 0.8 ? "dikkat" : "saglikli";
      const et = { saglikli: "sınırın altında", dikkat: "sınıra yaklaşıyor", dolu: "sınıra ulaşıldı", asildi: "sınır aşıldı", sinirsiz: "sınırsız", olculmuyor: "ölçülmüyor" }[durum];
      return { ad, birim, limit, kullanim, oran, durum, etiket: et, kaynak, ...(not_ ? { not_ } : {}) }; };
    const KOTA = (p, anlik, bu) => ({ santral: K("Etkin santral", "adet", p.santral_limit, anlik.santral), kullanici: K("Etkin kullanıcı", "adet", p.kullanici_limit, anlik.kullanici),
      portfoy: K("Etkin portföy", "adet", p.portfoy_limit, anlik.portfoy), ac_mw: K("Yönetilen güç", "MW", p.ac_mw_limit, anlik.ac_mw, "plan", anlik.ac_eksik_santral ? `${anlik.ac_eksik_santral} santralde AC sınırı girilmemiş; DC gücü sayıldı (yaklaşık)` : undefined),
      aylik_dis_api: K("Dış API isteği", "istek/ay", p.aylik_dis_api_limit, bu.dis_api), aylik_rapor: K("Üretilen rapor", "adet/ay", p.aylik_rapor_limit, bu.rapor), aylik_isleme_saat: K("İşlenen üretim verisi", "saat/ay", p.aylik_isleme_saat_limit, bu.scada_saat) });
    const PP = { pilot: { santral_limit: 3, kullanici_limit: 3, portfoy_limit: 0, ac_mw_limit: null, aylik_dis_api_limit: 5000, aylik_rapor_limit: 50, aylik_isleme_saat_limit: null },
      standart: { santral_limit: 25, kullanici_limit: 10, portfoy_limit: 1, ac_mw_limit: null, aylik_dis_api_limit: 50000, aylik_rapor_limit: 500, aylik_isleme_saat_limit: null } };
    const A1 = { santral: 2, ac_mw: 5.714, ac_eksik_santral: 1, kullanici: 3, portfoy: 0 }, A2 = { santral: 1, ac_mw: 4.514, ac_eksik_santral: 0, kullanici: 1, portfoy: 0 }, A3 = { santral: 1, ac_mw: 0.98, ac_eksik_santral: 1, kullanici: 2, portfoy: 1 };
    const B1 = T(1184, 25, 1, 3, 125, 3000, 2, 18, 4), B2 = T(312, 0, 0, 1, 25, 600, 0, 22, 20), B3 = T(0, 0, 0, 0, 0, 0, 0);
    const k1 = KOTA(PP.pilot, A1, B1); k1.santral = K("Etkin santral", "adet", 5, 2, "ezme");   // sözleşme ezmesi örneği
    return yanit(200, { ay, onceki_ay: onceki, turler: ["dis_api", "webhook", "webhook_hata"], kota_alanlari: ["santral", "kullanici", "portfoy", "ac_mw", "aylik_dis_api", "aylik_rapor", "aylik_isleme_saat"],
      kota_sozlugu: { saglikli: "sınırın altında", dikkat: "sınıra yaklaşıyor", dolu: "sınıra ulaşıldı", asildi: "sınır aşıldı", sinirsiz: "sınırsız", olculmuyor: "ölçülmüyor" }, kiracilar: [
      { id: KIRACILAR[1].id, ad: "Deneme Lab", plan: "pilot", durum: "active", abonelik_durum: "pilot", abonelik_etiketi: "Pilot", etkin_anahtar: 2, etkin_webhook: 1, son_api_kullanim: dkOnce(42), bu_ay: B1, onceki_ay: T(960, 30, 0, 4, 150, 3720, 3, 12, 0), anlik: A1, kotalar: k1 },
      { id: KIRACILAR[0].id, ad: "Meridyen Enerji", plan: "pilot", durum: "active", abonelik_durum: "sona_erdi", abonelik_etiketi: "Sona erdi", etkin_anahtar: 1, etkin_webhook: 0, son_api_kullanim: dkOnce(60 * 30), bu_ay: B2, onceki_ay: T(280, 0, 0, 2, 31, 744, 1, 25, 23), anlik: A2, kotalar: KOTA(PP.pilot, A2, B2) },
      { id: KIRACILAR[2].id, ad: "Askıdaki Enerji", plan: "standart", durum: "suspended", abonelik_durum: "askida", abonelik_etiketi: "Askıda", etkin_anahtar: 0, etkin_webhook: 0, son_api_kullanim: null, bu_ay: B3, onceki_ay: T(12, 0, 0, 0, 10, 240, 0), anlik: A3, kotalar: KOTA(PP.standart, A3, B3) }] });
  }
  // ---- 26.10 Faz 5: planlar + temsil
  const PLANLAR = [
    // v2.609 (F6-B): üç yeni kota + plan → modül varsayılanları (plan_modulleri tohumu)
    { ad: "pilot", baslik: "Pilot", santral_limit: 3, kullanici_limit: 3, api_rpm_limit: 60, aylik_rapor_limit: 50, aylik_dis_api_limit: 5000, ac_mw_limit: null, portfoy_limit: 0, aylik_isleme_saat_limit: null, notlar: null, sira: 1, guncelleme: "2026-10-26T00:00:00Z", kiraci: 2,
      moduller: { tahmin: { dahil: true, sinir: null }, dogruluk: { dahil: true, sinir: null }, veri: { dahil: true, sinir: { baglanti: 1 } }, alarm: { dahil: true, sinir: { kurallar: "temel" } }, kgup: { dahil: true, sinir: { revizyon: false } } } },
    { ad: "standart", baslik: "Standart", santral_limit: 25, kullanici_limit: 10, api_rpm_limit: 120, aylik_rapor_limit: 500, aylik_dis_api_limit: 50000, ac_mw_limit: null, portfoy_limit: 1, aylik_isleme_saat_limit: null, notlar: null, sira: 2, guncelleme: "2026-10-26T00:00:00Z", kiraci: 1,
      moduller: Object.fromEntries(["tahmin", "dogruluk", "veri", "alarm", "kgup", "finansal_etki", "mutabakat", "rapor_gelismis", "paylasim"].map((m) => [m, { dahil: true, sinir: null }]).concat([["portfoy_dsg", { dahil: true, sinir: { portfoy: 1 } }], ["dis_api", { dahil: true, sinir: { kapsamlar: "oku" } }]])) },
    { ad: "kurumsal", baslik: "Kurumsal", santral_limit: null, kullanici_limit: null, api_rpm_limit: null, aylik_rapor_limit: null, aylik_dis_api_limit: null, ac_mw_limit: null, portfoy_limit: null, aylik_isleme_saat_limit: null, notlar: null, sira: 3, guncelleme: "2026-10-26T00:00:00Z", kiraci: 0,
      moduller: Object.fromEntries(["tahmin", "dogruluk", "veri", "alarm", "kgup", "finansal_etki", "mutabakat", "rapor_gelismis", "paylasim", "portfoy_dsg", "dis_api", "destek_oncelik"].map((m) => [m, { dahil: true, sinir: null }]).concat([["santral_yetki", { dahil: true, sinir: { durum: "gelistirmede" } }], ["sozlesme", { dahil: true, sinir: { durum: "sinirli" } }], ["entegrasyon", { dahil: true, sinir: { durum: "is_bazli" } }]])) }];
  const MODUL_AD = { tahmin: "Tahmin ve Genel bakış", dogruluk: "Doğruluk karnesi ve bağımsız doğrulama", veri: "Veri yükleme ve bağlantılar", alarm: "Alarm ve olay kaydı", kgup: "Üretim programı (KGÜP)", finansal_etki: "Finansal etki merkezi", mutabakat: "Mutabakat ve EPİAŞ bildirimi", rapor_gelismis: "Dönem raporu ve zamanlanmış gönderim", paylasim: "Kuruluşlar arası paylaşım", portfoy_dsg: "Portföy, DSG ve KÜPST", dis_api: "Kurumsal API ve webhook", santral_yetki: "Santral bazlı kullanıcı yetkisi", sozlesme: "Sözleşme kuralları", entegrasyon: "Özel entegrasyon ve saha toplayıcısı", destek_oncelik: "Öncelikli destek" };
  for (const p of PLANLAR) { for (const k of Object.keys(MODUL_AD)) if (!p.moduller[k]) p.moduller[k] = { dahil: false, sinir: null }; for (const [k, m] of Object.entries(p.moduller)) m.ad = MODUL_AD[k] ?? k; }   // her modül adıyla (plan_listesi gibi)
  if (yol === "/v1/yonetim/planlar") return yanit(200, { planlar: PLANLAR, limit_alanlari: ["santral_limit", "kullanici_limit", "api_rpm_limit", "aylik_rapor_limit", "aylik_dis_api_limit", "ac_mw_limit", "portfoy_limit", "aylik_isleme_saat_limit"] });
  if (/^\/v1\/yonetim\/planlar\//.test(yol)) return yanit(200, PLANLAR[0]);
  // ---- v2.609 (Faz 6 F6-A/C): abonelik hakları + yaşam döngüsü eylemi (sahte: her PUT aynı nesneyi döner)
  if (/^\/v1\/yonetim\/kiracilar\/[^/]+\/abonelik$/.test(yol)) {
    const MOD = (ad, dahil, kaynak = "plan", sinir = null, durum = "mevcut", de = "mevcut") => ({ ad, dahil, kaynak, sinir, durum, durum_etiketi: de });
    const K = (ad, birim, limit, kullanim, kaynak = "plan", not_) => { const oran = limit == null || kullanim == null || limit <= 0 ? null : Math.round(kullanim / limit * 1000) / 1000;
      const durum = kullanim == null ? "olculmuyor" : limit == null ? "sinirsiz" : limit <= 0 ? (kullanim > 0 ? "asildi" : "saglikli") : oran > 1 ? "asildi" : oran >= 1 ? "dolu" : oran >= 0.8 ? "dikkat" : "saglikli";
      return { ad, birim, limit, kullanim, oran, durum, etiket: { saglikli: "sınırın altında", dikkat: "sınıra yaklaşıyor", dolu: "sınıra ulaşıldı", asildi: "sınır aşıldı", sinirsiz: "sınırsız", olculmuyor: "ölçülmüyor" }[durum], kaynak, ...(not_ ? { not_ } : {}) }; };
    const ab = { tenant_id: KIRACILAR[1].id, kiraci: "Deneme Lab", plan: { ad: "pilot", baslik: "Pilot" }, durum: "pilot", durum_etiketi: "Pilot", kayit_durumu: "pilot", kayit_var: true,
      tarihler: { baslangic: "2026-10-26", bitis: null, pilot_bitis: "2026-12-25", kalan_gun: 42 },
      moduller: { tahmin: MOD("Tahmin ve Genel bakış", true), dogruluk: MOD("Doğruluk karnesi ve bağımsız doğrulama", true), veri: MOD("Veri yükleme ve bağlantılar", true, "plan", { baglanti: 1 }), alarm: MOD("Alarm ve olay kaydı", true, "plan", { kurallar: "temel" }),
        kgup: MOD("Üretim programı (KGÜP)", true, "plan", { revizyon: false }), finansal_etki: MOD("Finansal etki merkezi", true, "ek"), mutabakat: MOD("Mutabakat ve EPİAŞ bildirimi", false, "yok"), rapor_gelismis: MOD("Dönem raporu ve zamanlanmış gönderim", false, "yok"),
        paylasim: MOD("Kuruluşlar arası paylaşım", false, "yok"), portfoy_dsg: MOD("Portföy, DSG ve KÜPST", false, "yok"), dis_api: MOD("Kurumsal API ve webhook", false, "yok"), santral_yetki: MOD("Santral bazlı kullanıcı yetkisi", false, "yok", null, "gelistirmede", "geliştirmede"),
        sozlesme: MOD("Sözleşme kuralları", false, "yok", null, "sinirli", "sınırlı"), entegrasyon: MOD("Özel entegrasyon ve saha toplayıcısı", false, "yok", null, "is_bazli", "iş bazlı"), destek_oncelik: MOD("Öncelikli destek", false, "yok", null, "surec", "süreç") },
      kotalar: { santral: K("Etkin santral", "adet", 5, 2, "ezme"), kullanici: K("Etkin kullanıcı", "adet", 3, 3), portfoy: K("Etkin portföy", "adet", 0, 0), ac_mw: K("Yönetilen güç", "MW", null, 5.714, "plan", "1 santralde AC sınırı girilmemiş; DC gücü sayıldı (yaklaşık)"),
        aylik_dis_api: K("Dış API isteği", "istek/ay", 5000, 1184), aylik_rapor: K("Üretilen rapor", "adet/ay", 50, 3), aylik_isleme_saat: K("İşlenen üretim verisi", "saat/ay", null, 3000), api_rpm: K("Dış API hızı", "istek/dk", 60, null, "plan", "anahtar başına uygulanır (altyapı sınırı); plan değeri yeni anahtarların üst sınırıdır") },
      kullanim: { santral: 2, kullanici: 3, portfoy: 0, ac_mw: 5.714, ac_eksik_santral: 1, aylik_dis_api: 1184, aylik_rapor: 3, aylik_isleme_saat: 3000, api_rpm: null, ay: "2026-11" },
      uyarilar: ["Etkin kullanıcı: sınıra ulaşıldı"], zorlama: "uyari",
      sozlesme: { notu: "Pilot; finansal etki modülü deneme amaçlı açık", teklif_ref: "T-2026-11-03", kota_ezme: { santral: 5 }, modul_ek: ["finansal_etki"], modul_cikar: [], guncelleme: dkOnce(60 * 50), guncelleyen: "p1" },
      sozluk: { durumlar: { pilot: "Pilot", aktif: "Etkin", sona_eriyor: "Sona eriyor", yenileme_bekliyor: "Yenileme bekliyor", askida: "Askıda", sona_erdi: "Sona erdi", feshedildi: "Feshedildi" }, kota_durumlari: { saglikli: "sınırın altında", dikkat: "sınıra yaklaşıyor", dolu: "sınıra ulaşıldı", asildi: "sınır aşıldı", sinirsiz: "sınırsız", olculmuyor: "ölçülmüyor" } },
      zaman: new Date().toISOString(),
      gecmis: [{ id: 3, zaman: dkOnce(60 * 50), aktor: "p1", eylem: "guncelle", eski: { kota_ezme: {}, modul_ek: [] }, yeni: { kota_ezme: { santral: 5 }, modul_ek: ["finansal_etki"] }, gerekce: "pilot genişletme; teklif T-2026-11-03" },
        { id: 2, zaman: dkOnce(60 * 24 * 3), aktor: "goc v2609", eylem: "geri_doldurma", eski: null, yeni: { plan: "pilot", durum: "pilot", pilot_bitis: "2026-12-25" }, gerekce: "v2.609 göçü" }] };
    if (req.method === "PUT") return yanit(200, { tamam: true, degisen: { plan: { eski: "pilot", yeni: "standart" } }, abonelik: ab });
    return yanit(200, ab); }
  if (/^\/v1\/yonetim\/planlar\/[^/]+\/moduller$/.test(yol) && req.method === "PUT") return yanit(200, PLANLAR[1]);
  if (/^\/v1\/yonetim\/kiracilar\/[^/]+\/temsil$/.test(yol)) return yanit(200, { token: "x." + Buffer.from('{"role":"viewer","temsil":"p1"}').toString("base64url") + ".y", tenant_id: KIRACILAR[1].id, kiraci: "Deneme Lab", sure_dk: 15, bitis: new Date(Date.now() + 15 * 60000).toISOString() });
  if (yol === "/v1/yonetim/denetim") return yanit(200, { kayitlar: [
      // v2.516 (#7): uzlaştırma katmanının müşteri eylemleri izde
      { id: 16, zaman: "2026-10-24T23:40:00Z", kapsam: "musteri", aktor_id: "u1", aktor_eposta: "operasyon@meridyen.example", tenant_id: "19bf0a66-39dc-42e5-a9bb-269466de3f7a", kiraci_ad: "Meridyen Enerji", eylem: "kgup_indir", nesne_tur: "plant", nesne_id: "pl-2", ayrinti: { gun: "2026-10-25", kantil: "p50", surum: 2, yeni_surum: true, kanal: "panel" }, ip: "78.177.165.74" },
      { id: 15, zaman: "2026-10-24T23:12:00Z", kapsam: "musteri", aktor_id: "u1", aktor_eposta: "operasyon@meridyen.example", tenant_id: "19bf0a66-39dc-42e5-a9bb-269466de3f7a", kiraci_ad: "Meridyen Enerji", eylem: "santral_segment", nesne_tur: "plant", nesne_id: "pl-2", ayrinti: { segment: "lisansli_serbest", uevcb: "40X000000000123A" }, ip: "78.177.165.74" },
      { id: 13, zaman: "2026-10-24T22:10:00Z", kapsam: "platform", aktor_id: null, aktor_eposta: "smoke-denetim@pvquant.invalid", tenant_id: null, eylem: "giris_basarisiz", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 14, zaman: "2026-10-24T22:05:00Z", kapsam: "platform", aktor_id: null, aktor_eposta: "cli", tenant_id: null, eylem: "operator_ekle", nesne_tur: "platform_user", nesne_id: "90985188", ayrinti: { rol: "sahip", email: "sahip@pvquant.com", kaynak: "script" }, ip: null },
      { id: 12, zaman: "2026-10-24T21:53:35Z", kapsam: "platform", aktor_id: "p1", aktor_eposta: "sahip@pvquant.com", tenant_id: null, eylem: "iki_adim_ac", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 11, zaman: "2026-10-24T21:48:28Z", kapsam: "platform", aktor_id: null, aktor_eposta: "sahip@pvquant.com", tenant_id: null, eylem: "giris", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 10, zaman: "2026-10-24T20:30:21Z", kapsam: "platform", aktor_id: null, aktor_eposta: "yok@pvquant.invalid", tenant_id: null, eylem: "giris_basarisiz", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 9, zaman: "2026-10-24T20:15:00Z", kapsam: "musteri", aktor_id: "u1", aktor_eposta: "deneme@example.com", tenant_id: KIRACILAR[1].id, kiraci_ad: "Deneme Lab", eylem: "giris", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 8, zaman: "2026-10-24T20:00:00Z", kapsam: "platform", aktor_id: "p1", aktor_eposta: "sahip@pvquant.com", tenant_id: KIRACILAR[2].id, kiraci_ad: "Askıdaki Enerji", eylem: "kiraci_guncelle", nesne_tur: "tenant", nesne_id: KIRACILAR[2].id, ayrinti: { eski: { status: "active" }, yeni: { status: "suspended" } }, ip: "78.177.165.74" }] });
  // ---- 26.10 Faz 6: kuruluş (müşteri)
  if (yol === "/v1/kurulus/ayarlar") return yanit(200, { yonetici_2fa_zorunlu: req.method === "PUT", iki_adimsiz_yonetici: 1 });
  if (yol === "/v1/kurulus/denetim") return yanit(200, { kayitlar: [
      { id: 31, zaman: dkOnce(12), kapsam: "musteri", aktor_id: "u1", aktor_eposta: "deneme@example.com", tenant_id: KIRACILAR[1].id, eylem: "giris", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 30, zaman: dkOnce(60 * 5), kapsam: "platform", aktor_id: "p1", aktor_eposta: "yonetim@pvquant.com", tenant_id: KIRACILAR[1].id, eylem: "kiraci_temsil", nesne_tur: "tenant", nesne_id: KIRACILAR[1].id, ayrinti: { sure_dk: 15, rol: "viewer" }, ip: "78.177.165.74" },
      { id: 29, zaman: dkOnce(60 * 30), kapsam: "musteri", aktor_id: "u1", aktor_eposta: "deneme@example.com", tenant_id: KIRACILAR[1].id, eylem: "kurulus_ayar", nesne_tur: "tenant", nesne_id: KIRACILAR[1].id, ayrinti: { yonetici_2fa_zorunlu: true }, ip: "78.177.165.74" }] });
  if (yol === "/v1/portfoy") return yanit(200, PORTFOY);
  if (yol === "/v1/portfoy/tahmin") return yanit(process.env.TAHMIN_OK ? 200 : 500, process.env.TAHMIN_OK ? { durum: "ok", yontem: "bottom-up", tutarli: true, gunler: [{ gun: "2026-10-24", p50_mwh: 1798.7, p10_mwh: 1600, p90_mwh: 1950, saat: 24 }], not: "Santral tahminleri toplanır." } : { detail: "Internal Server Error" });
  if (yol === "/v1/portfoy/dsg") return yanit(200, DSG);
  if (yol === "/v1/plants") return yanit(200, PLANTS);
  // 26.10 eşzamanlama sınaması: damga ucu (ETag/304) + kontrol ucu; __kontrol/damga her çağrıda damgayı değiştirir, özetin
  // bugün beklenen değeri de sürümle artar → tarayıcı testi «damga değişince sayfa yeniden çekti mi» sorusunu ölçer
  if (yol === "/__kontrol/damga") { DAMGA_SURUM += 1; return yanit(200, { surum: DAMGA_SURUM }); }
  if (/^\/v1\/plants\/[^/]+\/damga$/.test(yol)) {
    const et = `W/"sahte-${DAMGA_SURUM}"`;
    if (req.headers["if-none-match"] === et) { res.writeHead(304, { ETag: et }); return res.end(); }
    return yanit(200, { son_kosu: `2026-10-26T09:33:00+00:00`, surum: DAMGA_SURUM }, { ETag: et });
  }
  if (/^\/v1\/plants\/[^/]+\/summary$/.test(yol)) return yanit(200, {   // OzetYanit biçimi (client.ts uyarlaOzet); bugün değeri damga sürümüyle artar
    plant: { id: "a1", name: "Edikli GES", capacity_kwp: 15230, ac_limit_kw: 10000, lat: 38.2856, lon: 34.9628, tz: "Europe/Istanbul", tilt: 25, azimuth: 180, panel_tech: "bifacial" },
    mode: null, sapma_pct: null, anlati: "Yarın beklenen üretim bugünden %36 düşük.", bugun_kwh: 69760 + DAMGA_SURUM, yarin_kwh: 44891, yarin_hava: "2,8 kWh/m² ışınım",
    hafta_mwh: 359.1, model_alt: "", kalibrasyon_tarihi: null,
    hava: [{ gun: "BUGÜN", derece: 20.4, kwhm2: 4.0 }, { gun: "YARIN", derece: 16.8, kwhm2: 2.8 }, { gun: "ÇAR", derece: 18.0, kwhm2: 3.5 }],
    gunler: [{ etiket: "Pzt", mwh: 69.8 }, { etiket: "Sal", mwh: 44.9 }], saglik: { son_scada: "2026-10-25T20:00:00+00:00", islenen_saat: 24, anomali: 0 },
    aylik: [{ ay: "2026-09", mwh: 1800, saglam_saat: 700, kapsam_pct: 97, beklenti_mwh: 1750 }], damga_surum: DAMGA_SURUM });
  if (yol === "/v1/oturum/yenile") return yanit(200, { token: "x." + Buffer.from('{"role":"admin"}').toString("base64url") + ".y", role: "admin", firma: "Deneme Lab", email: "deneme@example.com" });
  if (yol === "/v1/api-anahtarlari") return yanit(200, { anahtarlar: [], kapsamlar: ["tahmin:oku", "kgup:oku"] });
  if (yol === "/v1/webhooklar") return yanit(200, { webhooklar: [] });
  if (yol === "/v1/paylasimlar") return yanit(200, { verilenler: [], alinanlar: [], izin_secenekleri: ["tahmin:oku"] });
  if (yol === "/v1/plants-arsiv") return yanit(200, { santraller: [] });
  if (yol === "/v1/takim") return yanit(200, { uyeler: [{ id: "u1", email: "deneme@example.com", rol: "admin", aktif: true, iki_adim: false }], roller: ["admin", "viewer"] });
  if (yol === "/v1/iki-adim") return yanit(200, { aktif: false, kalan_kurtarma: 0 });
  if (yol === "/v1/vitrin/basvurular") return yanit(200, { basvurular: [] });
  if (yol === "/v1/kullanicilar") return yanit(200, []);
  if (/^\/v1\/plants\/[^/]+\/alerts/.test(yol) || /\/alarmlar/.test(yol)) return yanit(200, []);   // 26.10: alarm-kurallari nesne bekler → 404 (sayfa null yolu)
  if (/^\/v1\/plants\/[^/]+\/runs/.test(yol) || /kosu/.test(yol)) return yanit(200, []);
  return yanit(404, { detail: "yok" });
}).listen(PORT, "127.0.0.1", () => console.log("sahte api", PORT));
