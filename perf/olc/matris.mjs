// matris.mjs — yükleme matrisi: motor × görünüm × ağ × sayfa × koşu; her koşu soğuk (yeni bağlam) + sıcak (aynı bağlam, ikinci gezinme).
// node olc/matris.mjs --hedef once --cikti baseline [--motor chromium,firefox,webkit] [--gorunum ...] [--ag yok,hizli3g,yavas4g] [--sayfa ana,yontem] [--kosu 3]
// Çıktı: <cikti>/matris.jsonl (satır başına bir yükleme). Yarıda kalırsa aynı komut kaldığı yerden sürer.
import fs from "node:fs";
import path from "node:path";
import { KOK, HEDEFLER, GORUNUMLER, SAYFALAR, motorAc, baglamAyar, OLCUM_BETIGI, topla } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "once");
const cikti = path.join(KOK, arg("cikti", "baseline"));
const motorlar = arg("motor", "chromium,firefox,webkit").split(",");
const gorunumler = arg("gorunum", Object.keys(GORUNUMLER).join(",")).split(",");
const aglar = arg("ag", Object.keys(HEDEFLER[hedef]).filter((k) => k !== "spki").join(",")).split(",");
const sayfalar = arg("sayfa", Object.keys(SAYFALAR).join(",")).split(",");
const kosu = Number(arg("kosu", "3"));
fs.mkdirSync(cikti, { recursive: true });
const dosya = path.join(cikti, "matris.jsonl");
const yapilan = new Set(fs.existsSync(dosya) ? fs.readFileSync(dosya, "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s).anahtar) : []);
const BEKLE = { yok: 3000, hizli3g: 6000, yavas4g: 5000 };    // load sonrası gözlem penceresi (ms)
const toplam = motorlar.length * gorunumler.length * aglar.length * sayfalar.length * kosu;
let sayac = 0;
const bas = Date.now();

/** Kısıtlı hatta önceki yüklemeden kalan aktarım bitene dek bekle (denetim ucu: hedef portu + 1). */
async function hatBos(url, ag) {
  if (ag === "yok") return 0;
  const port = Number(new URL(url).port) + 1, bas = Date.now();
  let bosSure = 0;
  while (Date.now() - bas < 90000) {
    const d = await fetch(`http://127.0.0.1:${port}/`).then((r) => r.json()).catch(() => null);
    if (d && d.kuyruk <= 0 && d.asagiMs <= 0 && d.yukariMs <= 0) { if ((bosSure += 250) >= 750) return Date.now() - bas; } else bosSure = 0;
    await new Promise((r) => setTimeout(r, 250));
  }
  return -1;
}

async function yukle(sayfa, url, ag) {
  await sayfa.goto("about:blank").catch(() => {});                // önceki sayfanın istekleri iptal
  const bosBekleme = await hatBos(url, ag);
  // vekil bayt sayacı (kısıtlı hatlarda): gezinme başından gözlem penceresi sonuna dek alıcıya yazılan bayt — süren medya dahil
  const bayt = async () => (ag === "yok" ? null : await fetch(`http://127.0.0.1:${Number(new URL(url).port) + 1}/`).then((r) => r.json()).then((d) => d.asagiBayt ?? null).catch(() => null));
  const b0 = await bayt();
  const hata = { konsol: [], sayfa: [], http: [], basarisiz: [] };
  const k1 = (m) => { if (m.type() === "error") hata.konsol.push(m.text().slice(0, 200)); };
  const k2 = (e) => hata.sayfa.push(String(e.message || e).slice(0, 200));
  const k3 = (r) => { if (r.status() >= 400) hata.http.push(r.status() + " " + r.url().replace(/^https?:\/\/[^/]+/, "").slice(0, 100)); };
  const k4 = (r) => { const f = r.failure()?.errorText || ""; if (!/ERR_ABORTED|NS_BINDING_ABORTED|NS_ERROR_PARSED_DATA_CACHED|cancelled|Load request cancelled/i.test(f)) hata.basarisiz.push(f + " " + r.url().replace(/^https?:\/\/[^/]+/, "").slice(0, 100)); };
  sayfa.on("console", k1); sayfa.on("pageerror", k2); sayfa.on("response", k3); sayfa.on("requestfailed", k4);
  const t0 = Date.now();
  let gezinmeHatasi = null;
  try { await sayfa.goto(url, { waitUntil: "load", timeout: 180000 }); } catch (e) { gezinmeHatasi = String(e.message).split("\n")[0]; }
  await sayfa.waitForTimeout(BEKLE[ag] ?? 3000);
  let m = null;
  try { m = await topla(sayfa); } catch (e) { gezinmeHatasi = (gezinmeHatasi || "") + " topla: " + String(e.message).split("\n")[0]; }
  sayfa.off("console", k1); sayfa.off("pageerror", k2); sayfa.off("response", k3); sayfa.off("requestfailed", k4);
  const b1 = await bayt();
  return { ...m, hata, gezinmeHatasi, duvarSaati: Date.now() - t0, bosBekleme, hatBayt: b0 !== null && b1 !== null ? b1 - b0 : null };
}

for (const motor of motorlar) {
  const tarayici = await motorAc(motor, hedef);
  const surum = tarayici.version();
  for (const gAd of gorunumler) for (const ag of aglar) for (const sAd of sayfalar) for (let k = 1; k <= kosu; k++) {
    const anahtar = [hedef, motor, gAd, ag, sAd, k].join("|");
    sayac++;
    if (yapilan.has(anahtar)) continue;
    const url = HEDEFLER[hedef][ag] + SAYFALAR[sAd];
    const baglam = await tarayici.newContext(baglamAyar(motor, GORUNUMLER[gAd]));
    await baglam.addInitScript(OLCUM_BETIGI);
    const sayfa = await baglam.newPage();
    const soguk = await yukle(sayfa, url, ag);
    const sicak = await yukle(sayfa, url, ag);
    await baglam.close();
    const satir = { anahtar, hedef, motor, surum, gorunum: gAd, ag, sayfa: sAd, kosu: k, zaman: new Date().toISOString(), soguk, sicak };
    fs.appendFileSync(dosya, JSON.stringify(satir) + "\n");
    const gecen = (Date.now() - bas) / 1000;
    console.log(`[${sayac}/${toplam}] ${motor} ${gAd} ${ag} ${sAd} #${k}  soğuk LCP ${soguk.lcp?.toFixed?.(0) ?? "-"} FCP ${soguk.fcp?.toFixed?.(0) ?? "-"} · sıcak LCP ${sicak.lcp?.toFixed?.(0) ?? "-"}  (${gecen.toFixed(0)} sn)`);
  }
  await tarayici.close();
}
console.log("bitti:", dosya);
