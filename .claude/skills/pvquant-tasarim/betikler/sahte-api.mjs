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
