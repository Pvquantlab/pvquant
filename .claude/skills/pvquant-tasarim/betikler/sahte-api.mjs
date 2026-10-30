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
  if (yol === "/v1/yonetim/sistem") return yanit(200, {
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
    return yanit(200, { ay, onceki_ay: onceki, turler: ["dis_api", "webhook", "webhook_hata"], kiracilar: [
      { id: KIRACILAR[1].id, ad: "Deneme Lab", plan: "pilot", durum: "active", etkin_anahtar: 2, etkin_webhook: 1, son_api_kullanim: dkOnce(42), bu_ay: T(1184, 25, 1, 3, 125, 3000, 2, 18, 4), onceki_ay: T(960, 30, 0, 4, 150, 3720, 3, 12, 0) },
      { id: KIRACILAR[0].id, ad: "Meridyen Enerji", plan: "pilot", durum: "active", etkin_anahtar: 1, etkin_webhook: 0, son_api_kullanim: dkOnce(60 * 30), bu_ay: T(312, 0, 0, 1, 25, 600, 0, 22, 20), onceki_ay: T(280, 0, 0, 2, 31, 744, 1, 25, 23) },
      { id: KIRACILAR[2].id, ad: "Askıdaki Enerji", plan: "standart", durum: "suspended", etkin_anahtar: 0, etkin_webhook: 0, son_api_kullanim: null, bu_ay: T(0, 0, 0, 0, 0, 0, 0), onceki_ay: T(12, 0, 0, 0, 10, 240, 0) }] });
  }
  // ---- 26.10 Faz 5: planlar + temsil
  const PLANLAR = [
    { ad: "pilot", baslik: "Pilot", santral_limit: 3, kullanici_limit: 3, api_rpm_limit: 60, aylik_rapor_limit: 50, aylik_dis_api_limit: 5000, notlar: null, sira: 1, guncelleme: "2026-10-26T00:00:00Z", kiraci: 2 },
    { ad: "standart", baslik: "Standart", santral_limit: 25, kullanici_limit: 10, api_rpm_limit: 120, aylik_rapor_limit: 500, aylik_dis_api_limit: 50000, notlar: null, sira: 2, guncelleme: "2026-10-26T00:00:00Z", kiraci: 1 },
    { ad: "kurumsal", baslik: "Kurumsal", santral_limit: null, kullanici_limit: null, api_rpm_limit: null, aylik_rapor_limit: null, aylik_dis_api_limit: null, notlar: null, sira: 3, guncelleme: "2026-10-26T00:00:00Z", kiraci: 0 }];
  if (yol === "/v1/yonetim/planlar") return yanit(200, { planlar: PLANLAR, limit_alanlari: ["santral_limit", "kullanici_limit", "api_rpm_limit", "aylik_rapor_limit", "aylik_dis_api_limit"] });
  if (/^\/v1\/yonetim\/planlar\//.test(yol)) return yanit(200, PLANLAR[0]);
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
