// kisitla.mjs — TCP düzeyinde bağlantı kısıtlayıcı (motor bağımsız: Chromium, Firefox, WebKit aynı hattı görür).
// node kisitla.mjs <dinle-port> <hedef-port> <profil>
// Profil: tek yön gecikme (RTT/2) her pakete, bant genişliği yön başına ORTAK kova (tüm bağlantılar tek hattı paylaşır),
// TCP el sıkışması için bağlantı başına 1 RTT bekleme. TLS ve HTTP/2 olduğu gibi geçer.
import net from "node:net";
import http from "node:http";
export const PROFILLER = {
  hizli3g: { rttMs: 562.5, asagiKbps: 1638.4, yukariKbps: 750 },   // DevTools eski «Fast 3G»
  yavas4g: { rttMs: 150, asagiKbps: 1638.4, yukariKbps: 750 },     // Lighthouse mobil «Slow 4G»
  kablo20: { rttMs: 40, asagiKbps: 20000, yukariKbps: 5000 },      // ev/4G ortası: poster 0,2 sn (video oynar), 37 MB video ≈ 15 sn
  seffaf: { rttMs: 0, asagiKbps: Infinity, yukariKbps: Infinity },  // kısıtsız; yalnız bayt sayacı için (A/B deneyleri)
};
const [dinle, hedef, ad] = process.argv.slice(2);
const p = PROFILLER[ad];
if (!p) { console.error("profil: " + Object.keys(PROFILLER).join(", ")); process.exit(2); }
const tek = p.rttMs / 2;
const hat = { asagi: 0, yukari: 0 };
let toplamKuyruk = 0;                                      // tüm bağlantılarda teslim bekleyen bayt (denetim ucu için)
const teslimEdilen = { asagi: 0, yukari: 0 };              // açılıştan beri alıcıya yazılan bayt (denetim ucu; süren medya indirmeleri dahil)
const hiz = { asagi: p.asagiKbps * 1000 / 8 / 1000, yukari: p.yukariKbps * 1000 / 8 / 1000 };   // bayt/ms
// Akış denetimi: bağlantı başına teslim edilmemiş en fazla PENCERE bayt; dolunca kaynak durur (TCP alıcı penceresi gibi).
// Yoksa hızlı yerel sunucu 29 MB'lık videoyu bir anda kuyruğa döker, terk edilen indirmeler hattı dakikalarca meşgul gösterirdi.
const PENCERE = 256 * 1024;   // ≥ bant×RTT (3G: 205 KB/s × 0,5625 s ≈ 115 KB) — pencere hattı kısmasın
function boru(kaynak, hedefSoket, yon) {
  // Teslim sırası TEK zamanlayıcılı FIFO ile korunur. (İlk sürüm parça başına ayrı setTimeout kuruyordu: yoğun olay
  // döngüsünde libuv'nin önbellekli saati yüzünden aynı ana düşen parçalar yer değiştirebiliyor, bayt sırası bozulunca
  // TLS kaydı çözülemiyordu → Chromium ERR_SSL_PROTOCOL_ERROR, Firefox NS_ERROR_NET_PARTIAL_TRANSFER. Bkz. baseline/SUMMARY.md.)
  const sira = [];                                         // [{ parca, teslim }]; teslim artan
  let sonTeslim = 0, kuyruk = 0, dustu = false, zamanlayici = null, bitti = false;
  const bosalt = () => {
    zamanlayici = null;
    const simdi = performance.now();
    while (sira.length && sira[0].teslim <= simdi + 0.5) {
      const { parca } = sira.shift();
      kuyruk -= parca.length; toplamKuyruk -= parca.length;
      if (!dustu && !hedefSoket.destroyed) { hedefSoket.write(parca); teslimEdilen[yon] += parca.length; }
    }
    if (kuyruk <= PENCERE / 2 && kaynak.isPaused() && !kaynak.destroyed) kaynak.resume();
    if (sira.length) zamanlayici = setTimeout(bosalt, Math.max(0, sira[0].teslim - performance.now()));
    else if (bitti && !hedefSoket.destroyed) hedefSoket.end();
  };
  hedefSoket.on("close", (hataVar) => {                    // alıcı gitti → bu yöndeki kuyruk hattan düşer
    if (!dustu) { dustu = true; hat[yon] = Math.max(performance.now(), hat[yon] - kuyruk / hiz[yon]); toplamKuyruk -= kuyruk; kuyruk = 0; sira.length = 0; }
    // Sunucu düzgün kapattıysa (FIN) istemciyi hemen öldürme: ters yöndeki kuyruk teslim edilip «end» ile kapanır.
    if (hataVar || yon === "asagi") kaynak.destroy();
  });
  kaynak.on("data", (parca) => {
    const simdi = performance.now();
    const bitis = Math.max(hat[yon], simdi) + parca.length / hiz[yon];
    hat[yon] = bitis;
    const teslim = Math.max(bitis + tek, sonTeslim);
    sonTeslim = teslim;
    kuyruk += parca.length; toplamKuyruk += parca.length;
    sira.push({ parca, teslim });
    if (kuyruk > PENCERE) kaynak.pause();
    if (!zamanlayici) zamanlayici = setTimeout(bosalt, Math.max(0, sira[0].teslim - simdi));
  });
  kaynak.on("end", () => { bitti = true; if (!sira.length && !zamanlayici && !hedefSoket.destroyed) hedefSoket.end(); });
  kaynak.on("error", () => hedefSoket.destroy());
}
net.createServer((istemci) => {
  istemci.pause();
  setTimeout(() => {                                       // TCP el sıkışması ≈ 1 RTT
    const sunucu = net.connect(Number(hedef), "127.0.0.1", () => { boru(istemci, sunucu, "yukari"); boru(sunucu, istemci, "asagi"); istemci.resume(); });
    sunucu.on("error", () => istemci.destroy());
  }, p.rttMs);
  istemci.on("error", () => {});
}).listen(Number(dinle), "127.0.0.1", () => console.log(`kisitla ${ad}: 127.0.0.1:${dinle} → :${hedef} (RTT ${p.rttMs} ms, ↓${p.asagiKbps} kbps ↑${p.yukariKbps} kbps)`));

// denetim ucu (dinle+1): ölçüm düzeneği her yüklemeden önce hattın boşalmasını bekler (önceki sayfanın terk edilen indirmeleri
// yeni ölçüme karışmasın — gerçek geri dönen ziyaretçi boş hatla gelir).
http.createServer((_, yanit) => {
  const simdi = performance.now();
  yanit.setHeader("content-type", "application/json");
  yanit.end(JSON.stringify({ kuyruk: toplamKuyruk, asagiMs: Math.max(0, hat.asagi - simdi), yukariMs: Math.max(0, hat.yukari - simdi), asagiBayt: teslimEdilen.asagi, yukariBayt: teslimEdilen.yukari }));
}).listen(Number(dinle) + 1, "127.0.0.1");
