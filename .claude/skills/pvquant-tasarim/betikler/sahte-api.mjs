/** Sahte API — canlıda ölçülen sunucu süreleriyle (24.10, Deneme Lab kiracısı, konteyner içi sıcak):
 *  /v1/portfoy ≈ 270 ms · /v1/portfoy/tahmin ≈ 400 ms sonra 500 · /v1/portfoy/dsg ≈ 1000 ms · diğer GET'ler ≈ 60 ms.
 *  node sahte-api.mjs [port=4807] ; GET /_log istek günlüğü (zaman, yol), POST /_sifirla günlüğü temizler. */
import http from "node:http";
const PORT = Number(process.argv[2] ?? 4807);
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
  res.setHeader("Access-Control-Allow-Origin", "*"); res.setHeader("Access-Control-Allow-Headers", "authorization,content-type"); res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
  if (req.method === "OPTIONS") { res.writeHead(204); return res.end(); }
  if (yol === "/_log") { res.setHeader("content-type", "application/json"); return res.end(JSON.stringify(gunluk)); }
  if (yol === "/_sifirla") { gunluk.length = 0; return res.end("ok"); }
  gunluk.push({ t: Math.round(performance.now()), m: req.method, yol: yol + url.search });
  const gec = LAT[yol] ?? 60;
  const yanit = (kod, govde) => setTimeout(() => { res.writeHead(kod, { "content-type": "application/json" }); res.end(JSON.stringify(govde)); }, gec);
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
    santraller: PORTFOY.santraller.map((s) => ({ id: s.id, ad: s.ad, kapasite_kwp: s.kapasite_kwp, tz: s.tz, arsivli: false, olusturma: "2026-09-02T14:30:00Z", son_scada: s.son_olcum, son_kosu: s.son_kosu })) }); }
  if (/^\/v1\/yonetim\/kiracilar\/[^/]+$/.test(yol) && req.method === "PUT") return yanit(200, { tamam: true, eski: {}, yeni: {} });
  if (yol === "/v1/yonetim/kullanicilar" && req.method === "GET") return yanit(200, { kullanicilar: [
      { id: "u1", email: "deneme@example.com", rol: "admin", aktif: true, totp_aktif: true, son_giris: "2026-10-24T20:15:00Z", olusturma: "2026-09-02T14:20:00Z", tenant_id: KIRACILAR[1].id, firma: "Deneme Lab" },
      { id: "u3", email: "ops@meridyen.example", rol: "admin", aktif: true, totp_aktif: false, son_giris: "2026-10-24T18:10:00Z", olusturma: "2026-07-12T09:00:00Z", tenant_id: KIRACILAR[0].id, firma: "Meridyen Enerji" },
      { id: "u2", email: "izleyici@example.com", rol: "viewer", aktif: false, totp_aktif: false, son_giris: null, olusturma: "2026-09-10T10:00:00Z", tenant_id: KIRACILAR[1].id, firma: "Deneme Lab" }] });
  if (/^\/v1\/yonetim\/kullanicilar\//.test(yol)) return yanit(200, yol.endsWith("parola-sifirlama") ? { gonderildi: false, baglanti: "https://pvquant.com/parola-yenile?jeton=ORNEK" } : { tamam: true });
  if (yol === "/v1/yonetim/basvurular") return yanit(200, { basvurular: [
      { id: "b1", eposta: "ali@gunesenerji.example", santral_adi: "Konya 2 GES", kurulu_guc_kwp: 9800, okundu: false, created_at: "2026-10-24T11:05:00Z" },
      { id: "b2", eposta: "info@tarimsal.example", santral_adi: null, kurulu_guc_kwp: null, okundu: true, created_at: "2026-10-19T08:40:00Z" }] });
  if (/^\/v1\/yonetim\/basvurular\//.test(yol)) return yanit(200, { tamam: true });
  if (yol === "/v1/yonetim/operatorler" && req.method === "GET") return yanit(200, { operatorler: [
      { id: "p1", email: "sahip@pvquant.com", rol: "sahip", aktif: true, totp_aktif: true, son_giris: "2026-10-24T21:48:28Z", olusturma: "2026-10-24T20:40:00Z" },
      { id: "p2", email: "destek@pvquant.com", rol: "operator", aktif: true, totp_aktif: false, son_giris: null, olusturma: "2026-10-25T08:00:00Z" }], roller: ["operator", "sahip"] });
  if (yol === "/v1/yonetim/operatorler" && req.method === "POST") return yanit(201, { id: "p3", email: "yeni@pvquant.com", rol: "operator", aktif: true, totp_aktif: false, son_giris: null, olusturma: "2026-10-25T09:00:00Z", gecici_parola: "Xy9-ornek-gecici" });
  if (/^\/v1\/yonetim\/operatorler\//.test(yol)) return yanit(200, { tamam: true });
  if (yol === "/v1/yonetim/parola") return yanit(200, { tamam: true });
  if (yol === "/v1/yonetim/denetim") return yanit(200, { kayitlar: [
      { id: 12, zaman: "2026-10-24T21:53:35Z", kapsam: "platform", aktor_id: "p1", aktor_eposta: "sahip@pvquant.com", tenant_id: null, eylem: "iki_adim_ac", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 11, zaman: "2026-10-24T21:48:28Z", kapsam: "platform", aktor_id: null, aktor_eposta: "sahip@pvquant.com", tenant_id: null, eylem: "giris", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 10, zaman: "2026-10-24T20:30:21Z", kapsam: "platform", aktor_id: null, aktor_eposta: "yok@pvquant.invalid", tenant_id: null, eylem: "giris_basarisiz", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 9, zaman: "2026-10-24T20:15:00Z", kapsam: "musteri", aktor_id: "u1", aktor_eposta: "deneme@example.com", tenant_id: KIRACILAR[1].id, eylem: "giris", nesne_tur: null, nesne_id: null, ayrinti: {}, ip: "78.177.165.74" },
      { id: 8, zaman: "2026-10-24T20:00:00Z", kapsam: "platform", aktor_id: "p1", aktor_eposta: "sahip@pvquant.com", tenant_id: KIRACILAR[2].id, eylem: "kiraci_guncelle", nesne_tur: "tenant", nesne_id: KIRACILAR[2].id, ayrinti: { eski: { status: "active" }, yeni: { status: "suspended" } }, ip: "78.177.165.74" }] });
  if (yol === "/v1/portfoy") return yanit(200, PORTFOY);
  if (yol === "/v1/portfoy/tahmin") return yanit(process.env.TAHMIN_OK ? 200 : 500, process.env.TAHMIN_OK ? { durum: "ok", yontem: "bottom-up", tutarli: true, gunler: [{ gun: "2026-10-24", p50_mwh: 1798.7, p10_mwh: 1600, p90_mwh: 1950, saat: 24 }], not: "Santral tahminleri toplanır." } : { detail: "Internal Server Error" });
  if (yol === "/v1/portfoy/dsg") return yanit(200, DSG);
  if (yol === "/v1/plants") return yanit(200, PLANTS);
  if (yol === "/v1/oturum/yenile") return yanit(200, { token: "x." + Buffer.from('{"role":"admin"}').toString("base64url") + ".y", role: "admin", firma: "Deneme Lab", email: "deneme@example.com" });
  if (yol === "/v1/api-anahtarlari") return yanit(200, { anahtarlar: [], kapsamlar: ["tahmin:oku", "kgup:oku"] });
  if (yol === "/v1/webhooklar") return yanit(200, { webhooklar: [] });
  if (yol === "/v1/paylasimlar") return yanit(200, { verilenler: [], alinanlar: [], izin_secenekleri: ["tahmin:oku"] });
  if (yol === "/v1/plants-arsiv") return yanit(200, { santraller: [] });
  if (yol === "/v1/takim") return yanit(200, { uyeler: [{ id: "u1", email: "deneme@example.com", rol: "admin", aktif: true, iki_adim: false }], roller: ["admin", "viewer"] });
  if (yol === "/v1/iki-adim") return yanit(200, { aktif: false, kalan_kurtarma: 0 });
  if (yol === "/v1/vitrin/basvurular") return yanit(200, { basvurular: [] });
  if (yol === "/v1/kullanicilar") return yanit(200, []);
  if (/^\/v1\/plants\/[^/]+\/alerts/.test(yol) || /alarm/.test(yol)) return yanit(200, []);
  if (/^\/v1\/plants\/[^/]+\/runs/.test(yol) || /kosu/.test(yol)) return yanit(200, []);
  return yanit(404, { detail: "yok" });
}).listen(PORT, "127.0.0.1", () => console.log("sahte api", PORT));
