import { useEffect, useState } from "react";
import { yonetim, zamanTr, type KullanimOzet, type KullanimKiraci, type KullanimToplam, type KullanimGunler } from "../../api/yonetim";
import { Kart, Sayfa, SayfaIskeleti, sayiTr } from "../sayfalar/parcalar";
import { Meta } from "../../lib/Meta";

/** 25.10 Faz 4 — KULLANIM: kiracı başına aylık sayımlar. dis_api / webhook sayaçtan (kullanim_sayac), rapor / koşu / SCADA saati /
 *  yükleme mevcut tablolardan türetilir; hepsi uçtan, arayüz toplar ve gösterir. Plan limiti yok (Faz 5): yalnız ölçüm. */

const mesajCikar = (e: unknown) => String((e as Error).message ?? e);
function Hata({ m }: { m: string | null }) { return m ? <p role="alert" className="giris-hata" style={{ marginTop: 10 }}>{m}</p> : null; }
function Bos({ bas, alt }: { bas: string; alt?: string }) { return <div className="bos-durum"><div className="bos-bas">{bas}</div>{alt && <p>{alt}</p>}</div>; }
const KULLANIM_SUTUNLAR: { k: keyof KullanimToplam; ad: string; birim?: string }[] = [
  { k: "dis_api", ad: "Dış API", birim: "istek" }, { k: "webhook", ad: "Webhook", birim: "teslim" }, { k: "rapor", ad: "Rapor" },
  { k: "kosu", ad: "Tahmin koşusu" }, { k: "scada_saat", ad: "SCADA", birim: "saat" }, { k: "yukleme", ad: "Yükleme" }];
const BOS: KullanimToplam = { dis_api: 0, webhook: 0, webhook_hata: 0, rapor: 0, kosu: 0, scada_saat: 0, yukleme: 0 };
const topla = (a: KullanimToplam, b: KullanimToplam): KullanimToplam =>
  ({ dis_api: a.dis_api + b.dis_api, webhook: a.webhook + b.webhook, webhook_hata: a.webhook_hata + b.webhook_hata, rapor: a.rapor + b.rapor,
     kosu: a.kosu + b.kosu, scada_saat: a.scada_saat + b.scada_saat, yukleme: a.yukleme + b.yukleme });
/** Son 6 ay 'YYYY-MM' (bu ay önce) */
function aylar(n = 6): string[] {
  const s = new Date(); const out: string[] = [];
  for (let i = 0; i < n; i++) { const d = new Date(Date.UTC(s.getUTCFullYear(), s.getUTCMonth() - i, 1)); out.push(d.toISOString().slice(0, 7)); }
  return out;
}
const ayAdi = (ay: string) => new Date(Date.UTC(Number(ay.slice(0, 4)), Number(ay.slice(5, 7)) - 1, 1)).toLocaleDateString("tr-TR", { month: "long", year: "numeric", timeZone: "UTC" });
/** Sayı; sıfır soluk «0» (gerçek sayım; «—» yalnız eksik değer içindir), webhook hücresi hata sayısını rozetle söyler */
function Hucre({ k, t }: { k: keyof KullanimToplam; t: KullanimToplam }) {
  const n = t[k] === 0 ? <span className="bos">0</span> : sayiTr(t[k]);
  if (k === "webhook") return <>{n}{t.webhook_hata > 0 && <span className="rozet rozet-kucuk rozet-uyari" style={{ marginLeft: 6 }}>{sayiTr(t.webhook_hata)} hata</span>}</>;
  return <>{n}</>;
}

export function Kullanim() {
  const [ay, setAy] = useState(aylar()[0]);
  const [o, setO] = useState<KullanimOzet | null>(null); const [hata, setHata] = useState<string | null>(null);
  const [secili, setSecili] = useState<KullanimKiraci | null>(null);
  useEffect(() => { setO(null); setHata(null); yonetim.kullanim(ay).then(setO).catch((e) => setHata(mesajCikar(e))); }, [ay]);
  if (secili) return <KullanimDetay kiraci={secili} ay={ay} geri={() => setSecili(null)} />;
  const toplam = o ? o.kiracilar.reduce((a, k) => topla(a, k.bu_ay), BOS) : BOS;
  const onceki = o ? o.kiracilar.reduce((a, k) => topla(a, k.onceki_ay), BOS) : BOS;
  return (
    <Sayfa baslik="Kullanım" alt="Kiracı başına aylık sayımlar; dış API ve webhook sayaçtan, rapor, koşu, SCADA ve yükleme kayıtlardan. Plan sınırı yok, yalnız ölçüm."
      sag={<label className="girdi-etiket" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>Ay
        <select className="girdi kucuk" value={ay} onChange={(e) => setAy(e.target.value)}>{aylar().map((a) => <option key={a} value={a}>{ayAdi(a)}</option>)}</select></label>}>
      <Hata m={hata} />
      <Kart baslik={ayAdi(ay)} alt={o ? `${sayiTr(o.kiracilar.length)} kiracı; satır günlük kırılımı açar; parantez içi önceki ay (${ayAdi(o.onceki_ay)})` : undefined}>
        {!o ? <SayfaIskeleti kpi={0} kart={1} /> : o.kiracilar.length === 0 ? <Bos bas="Kiracı yok." /> : (
          <div className="grafik-kaydir"><table className="veri sayisal santral">
            <thead><tr><th>Kiracı</th><th>Plan</th>{KULLANIM_SUTUNLAR.map((c) => <th key={c.k}>{c.ad}{c.birim && <span className="birim">{c.birim}</span>}</th>)}<th>Anahtar</th><th>Son API kullanımı</th><th aria-hidden="true"></th></tr></thead>
            <tbody>
              {o.kiracilar.map((k) => (
                <tr key={k.id} className="satir-tikla" tabIndex={0} onClick={() => setSecili(k)} onKeyDown={(e) => { if (e.key === "Enter") setSecili(k); }}>
                  <td className="ad">{k.ad}{k.durum !== "active" && <span className="rozet rozet-kucuk rozet-uyari" style={{ marginLeft: 8 }}>askıda</span>}</td><td>{k.plan}</td>
                  {KULLANIM_SUTUNLAR.map((c) => <td key={c.k}><Hucre k={c.k} t={k.bu_ay} /><span className="hucre-alt soluk" style={{ display: "block", fontSize: 12 }}>({sayiTr(k.onceki_ay[c.k])})</span></td>)}
                  <td>{sayiTr(k.etkin_anahtar)}{k.etkin_webhook > 0 && <span className="hucre-alt soluk" style={{ display: "block", fontSize: 12 }}>{sayiTr(k.etkin_webhook)} webhook</span>}</td>
                  <td>{zamanTr(k.son_api_kullanim)}</td>
                  <td><svg className="satir-ok" width="14" height="14" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M7 4l6 6-6 6"/></svg></td>
                </tr>))}
              <tr><td className="ad">Toplam</td><td></td>{KULLANIM_SUTUNLAR.map((c) => <td key={c.k} style={{ fontWeight: 600 }}><Hucre k={c.k} t={toplam} /><span className="hucre-alt soluk" style={{ display: "block", fontSize: 12, fontWeight: 400 }}>({sayiTr(onceki[c.k])})</span></td>)}<td></td><td></td><td></td></tr>
            </tbody>
          </table></div>)}
      </Kart>
    </Sayfa>
  );
}

function KullanimDetay({ kiraci, ay, geri }: { kiraci: KullanimKiraci; ay: string; geri: () => void }) {
  const [g, setG] = useState<KullanimGunler | null>(null); const [hata, setHata] = useState<string | null>(null);
  useEffect(() => { yonetim.kullanimGunler(kiraci.id, ay).then(setG).catch((e) => setHata(mesajCikar(e))); }, [kiraci.id, ay]);
  return (
    <Sayfa baslik={kiraci.ad} alt={`${ayAdi(ay)} günlük kullanım; ${kiraci.plan} planı`} sag={<span className="cip"><Meta items={[`${sayiTr(kiraci.etkin_anahtar)} etkin anahtar`, `${sayiTr(kiraci.etkin_webhook)} webhook`]} /></span>}>
      <button className="giris-bag" onClick={geri}>← Kullanım</button>
      <Hata m={hata} />
      <Kart baslik="Günlük kırılım" alt="yalnız kaydı olan günler; SCADA saati veri gününe göre, diğerleri işlem gününe göre (UTC)">
        {!g ? <SayfaIskeleti kpi={0} kart={1} /> : g.gunler.length === 0 ? <Bos bas="Bu ay kayıt yok." /> : (
          <div className="grafik-kaydir"><table className="veri sayisal santral">
            <thead><tr><th>Gün</th>{KULLANIM_SUTUNLAR.map((c) => <th key={c.k}>{c.ad}{c.birim && <span className="birim">{c.birim}</span>}</th>)}</tr></thead>
            <tbody>{g.gunler.map((d) => (<tr key={d.gun}><td className="ad mono">{new Date(d.gun + "T00:00:00Z").toLocaleDateString("tr-TR", { timeZone: "UTC" })}</td>
              {KULLANIM_SUTUNLAR.map((c) => <td key={c.k}><Hucre k={c.k} t={d} /></td>)}</tr>))}</tbody>
          </table></div>)}
      </Kart>
    </Sayfa>
  );
}

/** Müşteri detayında «Bu ay kullanım» kartı: günlük kırılımın toplamı (aynı uç). */
export function KullanimKarti({ tenantId }: { tenantId: string }) {
  const [g, setG] = useState<KullanimGunler | null | "hata">(null);
  useEffect(() => { yonetim.kullanimGunler(tenantId).then(setG).catch(() => setG("hata")); }, [tenantId]);
  const t = g && g !== "hata" ? g.gunler.reduce((a, d) => topla(a, d), BOS) : BOS;
  return (
    <Kart baslik="Bu ay kullanım" alt={g && g !== "hata" ? `${ayAdi(g.ay)}; ayrıntı Kullanım sayfasında` : undefined}>
      {g === null ? <SayfaIskeleti kpi={0} kart={1} /> : g === "hata" ? <Bos bas="Kullanım verisi alınamadı." /> : (
        <dl className="kunye">{KULLANIM_SUTUNLAR.map((c) => (<div key={c.k}><dt>{c.ad}{c.birim ? ` (${c.birim})` : ""}</dt><dd className="mono"><Hucre k={c.k} t={t} /></dd></div>))}</dl>)}
    </Kart>
  );
}
