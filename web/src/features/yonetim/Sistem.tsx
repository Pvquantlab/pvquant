import { useEffect, useState } from "react";
import { SOZLUK, isDurumu, tazelik, sorunAdi } from "../../lib/sozluk";
import { yonetim, yasTr, type SistemOzet, type IsKaydi, type SantralEnvanter, type Kiraci } from "../../api/yonetim";
import { Zaman } from "./ortak";
import { Kart, Kpi, Sayfa, SayfaIskeleti, sayiTr, gucTr } from "../sayfalar/parcalar";
import { Meta } from "../../lib/Meta";

/** 25.10 Faz 3 — SİSTEM: zamanlayıcı nabzı, gece turu tazeliği, hava/piyasa/yedek yaşı; müşteriler arası iş kayıtları (hata
 *  AYRINTISIYLA — müşteri panelinde bilerek yok); santral envanteri (sorun süzgeci); meteoroloji arşivi.
 *  Bayatlık hükümleri (durum/taze/bayat) ve eşikler uçtan gelir; arayüz yalnız okur ve renklendirir. Her sayı gerçek. */

const mesajCikar = (e: unknown) => String((e as Error).message ?? e);
function Hata({ m }: { m: string | null }) { return m ? <p role="alert" className="giris-hata" style={{ marginTop: 10 }}>{m}</p> : null; }
function Bos({ bas, alt }: { bas: string; alt?: string }) { return <div className="bos-durum"><div className="bos-bas">{bas}</div>{alt && <p>{alt}</p>}</div>; }
const boyutTr = (bayt: number) => bayt >= 1024 ** 3 ? `${sayiTr(bayt / 1024 ** 3, 2)} GB` : `${sayiTr(bayt / 1024 ** 2, 1)} MB`;
const sureTr = (sn: number | null) => sn == null ? "—" : sn >= 60 ? `${sayiTr(sn / 60, 1)} dk` : `${sayiTr(sn, 1)} sn`;
// 26.10 ortak sözlük: sorun adları, tazelik ve iş durumu sözcükleri lib/sozluk'tan (müşteri paneliyle aynı dil)
const sol = { textAlign: "left" as const };
/** Ayrıntı sütunu: .santral tablosunda öbür sütunlar 1 % (içerik genişliği); hata metni okunacak gerçek yer ister. */
const AYRINTI = { textAlign: "left" as const, whiteSpace: "normal" as const, width: "38%", minWidth: 240 };
const tarihTr = (s: string | null | undefined) => s ? new Date(s).toLocaleDateString("tr-TR") : "—";
// Meteo arşivi tablosu yarım kartta: .grafik-kaydir > table 620 px tabanı orada 440 (1440'ta kaydırmasız, 375'te kayar).

export function Sistem() {
  const [o, setO] = useState<SistemOzet | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const [sayac, setSayac] = useState(0);
  const [secSantral, setSecSantral] = useState<{ id: string; ad: string } | null>(null);   // 26.10 D2: envanterden «son hata» → iş kayıtları süzgeci
  useEffect(() => { yonetim.sistem().then(setO).catch((e) => setHata(mesajCikar(e))); }, [sayac]);
  if (!o && !hata) return <Sayfa baslik="Sistem"><SayfaIskeleti kpi={6} kart={2} /></Sayfa>;
  return (
    <Sayfa baslik="Sistem" alt="Zamanlayıcı, gece işlemleri, veri tazeliği ve yedek; tüm müşterilerin iş kayıtları ve santralleri."
      sag={<span className="dugme-sira">{o && <span className="cip"><Meta items={[`veritabanı ${boyutTr(o.db.boyut_bayt)}`, `${sayiTr(o.santral.etkin)} etkin santral`, `${sayiTr(o.santral.arsivli)} arşivli`]} /></span>}
        <button className="dugme kucuk" onClick={() => { setO(null); setHata(null); setSayac((x) => x + 1); }}>Yenile</button></span>}>
      <Hata m={hata} />
      {o && <>
        <div className="ızgara satir-3" style={{ marginBottom: 14 }}>
          <Kpi etiket={SOZLUK.kaynak.zamanlayici} deger={o.nabiz.durum === "calisiyor" ? "çalışıyor" : o.nabiz.durum === "sessiz" ? "sessiz" : "nabız yok"}
            ton={o.nabiz.durum === "calisiyor" ? undefined : "uyari"}
            alt={o.nabiz.son ? `son nabız ${yasTr(o.nabiz.son)}; her ${sayiTr(o.nabiz.aralik_dk)} dk beklenir` : "worker henüz nabız yazmadı (eski imaj ya da kapalı)"} />
          <Kpi etiket={SOZLUK.kaynak.geceIsleri} deger={tazelik(!o.gece_turu.taze)} ton={o.gece_turu.taze ? undefined : "uyari"}
            alt={o.gece_turu.taze ? `son üretici iş ${yasTr(o.gece_turu.son)}` : `${o.gece_turu.esik_saat} saattir koşmayan: ${o.gece_turu.bayat_isler.join(", ")}`} />
          <Kpi etiket="İşler" deger={sayiTr(o.isler_24.hata)} birim="hata" ton={o.isler_24.hata > 0 ? "uyari" : undefined}
            alt={`son 24 saatte ${sayiTr(o.isler_24.toplam)} iş kaydı`} />
          <Kpi etiket="Hava verisi" deger={o.meteo.kaynaklar.length ? yasTr(en_yeni(o.meteo.kaynaklar.map((k) => k.son_indirme))) : "arşiv yok"}
            ton={o.meteo.kaynaklar.length === 0 || o.meteo.kaynaklar.some((k) => k.bayat) ? "uyari" : undefined}
            alt={o.meteo.kaynaklar.length === 0 ? "meteo_arsiv tablosu boş"
              : o.meteo.kaynaklar.some((k) => k.bayat) ? `eski: ${o.meteo.kaynaklar.filter((k) => k.bayat).map((k) => `${k.kaynak} (${k.yas_saat == null ? "hiç" : sayiTr(k.yas_saat, 0) + " saat"})`).join(", ")}`
              : `${sayiTr(o.meteo.kaynaklar.length)} kaynak; ${o.meteo.esik_saat} saatten eskisi eski sayılır`} />
          <Kpi etiket={SOZLUK.kaynak.piyasaKisa} deger={yasTr(o.piyasa.son_guncelleme)} ton={o.piyasa.bayat ? "uyari" : undefined}
            alt={o.piyasa.son_ts ? `gerçekleşen PTF/SMF ${tarihTr(o.piyasa.son_ts)} gününe kadar (gece dünü çeker; ileri fiyat değil); ${sayiTr(o.piyasa.satir)} saat` : "piyasa_fiyat tablosu boş"} />
          <Kpi etiket={SOZLUK.kaynak.yedek} deger={yasTr(o.yedek.son_basarili)} ton={o.yedek.bayat || (o.yedek.son_deneme ? !o.yedek.son_deneme.tamam : false) ? "uyari" : undefined}
            alt={o.yedek.son_deneme ? (o.yedek.son_deneme.tamam ? `son deneme başarılı; ${o.yedek.esik_saat} saatten eskisi eski sayılır` : `son deneme başarısız: ${o.yedek.son_deneme.ayrinti ?? "ayrıntı yok"}`) : "henüz yedek kaydı yok"} />
        </div>
        <IsKayitlari santral={secSantral} temizle={() => setSecSantral(null)} />
        <SantralEnvanteri santralSec={(id, ad) => { setSecSantral({ id, ad }); document.getElementById("is-kayitlari")?.scrollIntoView({ behavior: "smooth", block: "start" }); }} />
        <div className="ızgara-cift">
          <Kart baslik="Üretici işler" alt={`tazelik ölçütü: son başarılı koşu ${o.gece_turu.esik_saat} saatten yeni`}>
            <div className="grafik-kaydir"><table className="veri sayisal" style={{ minWidth: 0 }}>
              <thead><tr><th style={sol}>İş</th><th style={sol}>Son başarılı koşu</th><th>Durum</th></tr></thead>
              <tbody>{o.gece_turu.uretici_isler.map((u) => { const bayat = o.gece_turu.bayat_isler.includes(u.is); return (
                <tr key={u.kod}><td style={sol}><span title={u.kod}>{u.is}</span></td><td style={sol}><Zaman s={u.son_ok} /></td>
                  <td><span className={`rozet ${bayat ? "rozet-uyari" : "rozet-ok"}`}>{tazelik(bayat)}</span></td></tr>); })}</tbody>
            </table></div>
          </Kart>
          <Kart baslik="Meteoroloji arşivi" alt="kaynak başına son indirme, nokta ve satır sayısı, kapsam">
            {o.meteo.kaynaklar.length === 0 ? <Bos bas="Arşivde kayıt yok." /> : (
              <div className="grafik-kaydir"><table className="veri sayisal" style={{ minWidth: 440 }}>
                <thead><tr><th style={sol}>Kaynak</th><th style={sol}>Son indirme</th><th>Nokta</th><th>Satır</th><th style={sol}>Kapsam</th></tr></thead>
                <tbody>{o.meteo.kaynaklar.map((k) => (
                  <tr key={k.kaynak}><td style={sol}>{k.kaynak}{k.bayat && <span className="rozet rozet-uyari" style={{ marginLeft: 8 }}>{SOZLUK.tazelik.eski}</span>}</td>
                    <td style={sol}><Zaman s={k.son_indirme} sar /></td><td>{k.nokta == null ? "—" : sayiTr(k.nokta)}</td>
                    <td>{k.satir == null ? "—" : sayiTr(k.satir)}</td>
                    <td style={sol}><span style={{ whiteSpace: "nowrap" }}>{tarihTr(k.ilk)}</span><br /><span style={{ whiteSpace: "nowrap" }}>→ {tarihTr(k.son_ts)}</span></td></tr>))}</tbody>
              </table></div>)}
          </Kart>
        </div>
      </>}
    </Sayfa>
  );
}

const en_yeni = (zamanlar: (string | null)[]): string | null =>
  zamanlar.filter((z): z is string => !!z).sort().at(-1) ?? null;

// ---------------- iş kayıtları (müşteriler arası, hata ayrıntısıyla) ----------------
function IsKayitlari({ santral, temizle }: { santral: { id: string; ad: string } | null; temizle: () => void }) {
  const [saat, setSaat] = useState(48); const [yalnizHata, setYalnizHata] = useState(false); const [job, setJob] = useState(""); const [tenant, setTenant] = useState("");
  const [liste, setListe] = useState<IsKaydi[] | null>(null); const [turler, setTurler] = useState<{ kod: string; is: string }[]>([]);
  const [kiracilar, setKiracilar] = useState<Kiraci[]>([]); const [hata, setHata] = useState<string | null>(null);
  const getir = (ek: { saat?: number; yalniz_hata?: boolean; plant?: string | null } = {}) => yonetim.isler({ saat: ek.saat ?? saat, yalniz_hata: ek.yalniz_hata ?? yalnizHata, job: job || undefined,
      tenant_id: tenant || undefined, limit: 200, plant_id: ek.plant === undefined ? santral?.id : ek.plant ?? undefined })
    .then((r) => { setListe(r.isler); setTurler(r.is_turleri); }).catch((e) => setHata(mesajCikar(e)));
  useEffect(() => { void getir(); yonetim.kiracilar().then((r) => setKiracilar(r.kiracilar)).catch(() => {}); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  // 26.10 D2: envanterden santral seçilince son 30 gün + yalnız başarısız; temizlenince varsayılan pencere
  useEffect(() => { if (santral) { setSaat(720); setYalnizHata(true); void getir({ saat: 720, yalniz_hata: true }); } }, [santral]);   // eslint-disable-line react-hooks/exhaustive-deps
  const hataSayisi = liste ? liste.filter((x) => !x.tamam).length : 0;
  return (
    <Kart baslik="İş kayıtları" alt="tüm müşteriler; başarısız işin ayrıntısı burada görünür, müşteri panelinde görünmez" id="is-kayitlari"
      sag={<span className="dugme-sira">{santral && <span className="rozet rozet-uyari">santral: {santral.ad} <button type="button" className="plat-rozet-kapat" aria-label="santral süzgecini kaldır" onClick={() => { temizle(); setSaat(48); setYalnizHata(false); void getir({ saat: 48, yalniz_hata: false, plant: null }); }}>×</button></span>}
        {liste && <span className="cip"><Meta items={[`${sayiTr(liste.length)} kayıt`, `${sayiTr(hataSayisi)} hata`]} /></span>}</span>}>
      <form className="form-izgara" style={{ maxWidth: 900, marginBottom: 12 }} onSubmit={(e) => { e.preventDefault(); void getir(); }}>
        <label className="girdi-etiket">Pencere<select className="girdi" value={saat} onChange={(e) => setSaat(Number(e.target.value))}>
          <option value={24}>son 24 saat</option><option value={48}>son 48 saat</option><option value={72}>son 72 saat</option><option value={168}>son 7 gün</option><option value={720}>son 30 gün</option></select></label>
        <label className="girdi-etiket">Durum<select className="girdi" value={yalnizHata ? "hata" : ""} onChange={(e) => setYalnizHata(e.target.value === "hata")}>
          <option value="">tümü</option><option value="hata">yalnız başarısız</option></select></label>
        <label className="girdi-etiket">İş<select className="girdi" value={job} onChange={(e) => setJob(e.target.value)}>
          <option value="">tümü</option>{turler.map((t) => <option key={t.kod} value={t.kod}>{t.is}</option>)}</select></label>
        <label className="girdi-etiket">Müşteri<select className="girdi" value={tenant} onChange={(e) => setTenant(e.target.value)}>
          <option value="">tümü</option>{kiracilar.map((k) => <option key={k.id} value={k.id}>{k.ad}</option>)}</select></label>
        <button className="dugme" type="submit">Süz</button>
      </form>
      <Hata m={hata} />
      {!liste ? <SayfaIskeleti kpi={0} kart={1} /> : liste.length === 0 ? <Bos bas="Süzgece uyan iş kaydı yok." /> : (
        <div className="grafik-kaydir"><table className="veri santral">
          <thead><tr><th>İş</th><th>Zaman</th><th>Müşteri</th><th>Santral</th><th>Süre</th><th>Durum</th><th style={AYRINTI}>Ayrıntı</th></tr></thead>
          <tbody>{liste.map((x) => (
            <tr key={x.id}><td className="ad">{x.is}</td><td style={{ whiteSpace: "nowrap" }}><Zaman s={x.zaman} /></td>
              <td style={{ whiteSpace: "nowrap" }}>{x.kiraci ?? (x.tenant_id ? x.tenant_id.slice(0, 8) : "—")}</td>
              <td style={{ whiteSpace: "nowrap" }}>{x.santral ?? (x.plant_id ? x.plant_id.slice(0, 8) : "—")}</td><td style={{ whiteSpace: "nowrap" }}>{sureTr(x.sure_sn)}</td>
              <td><span className={`rozet ${x.tamam ? "rozet-ok" : "rozet-uyari"}`}>{isDurumu(x.tamam)}</span></td>
              <td style={{ ...AYRINTI, fontSize: 13.5, color: x.tamam ? "var(--ikincil)" : undefined }}>{x.ayrinti ?? "—"}</td></tr>))}</tbody>
        </table></div>)}
    </Kart>
  );
}

// ---------------- santral envanteri ----------------
function SantralEnvanteri({ santralSec }: { santralSec: (id: string, ad: string) => void }) {
  const [sorunlu, setSorunlu] = useState(false);
  const [veri, setVeri] = useState<{ santraller: SantralEnvanter[]; esik: { scada_saat: number; kosu_saat: number }; toplam: number } | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  useEffect(() => { setVeri(null); yonetim.santraller(sorunlu).then(setVeri).catch((e) => setHata(mesajCikar(e))); }, [sorunlu]);
  return (
    <Kart baslik="Santral envanteri" alt={veri ? `SCADA ${veri.esik.scada_saat} saatten, tahmin koşusu ${veri.esik.kosu_saat} saatten eskiyse sorun sayılır` : undefined}
      sag={<label className="ayar-onay" style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13.5, cursor: "pointer" }}>
        <input type="checkbox" checked={sorunlu} onChange={(e) => setSorunlu(e.target.checked)} />yalnız sorunlu</label>}>
      <Hata m={hata} />
      {!veri ? <SayfaIskeleti kpi={0} kart={1} /> : veri.santraller.length === 0 ? <Bos bas={sorunlu ? "Sorunlu santral yok." : "Etkin santral yok."} alt={sorunlu ? `${sayiTr(veri.toplam)} etkin santralin hepsi veri alıyor ve koşuyor.` : undefined} /> : (
        <div className="grafik-kaydir"><table className="veri sayisal santral">
          <thead><tr><th>Müşteri</th><th>Santral</th><th>Kurulu güç<span className="birim">kWp</span></th><th>Son veri<span className="birim">SCADA</span></th><th>Son tahmin</th><th>Son hata</th><th>Sorun</th></tr></thead>
          <tbody>{veri.santraller.map((p) => (
            <tr key={p.id}><td className="ad">{p.kiraci}</td><td>{p.ad}</td><td>{p.kapasite_kwp ? gucTr(p.kapasite_kwp) : <span className="bos">—</span>}</td>
              <td><Zaman s={p.son_scada} /></td><td><Zaman s={p.son_kosu} /></td>
              <td>{p.son_hata ? <button type="button" className="plat-baglanti" title="İş kayıtlarında bu santralin hatalarını göster" onClick={() => santralSec(p.id, p.ad)}
                style={Date.now() - new Date(p.son_hata).getTime() > 7 * 86400000 ? { color: "var(--soluk)" } : undefined}>{yasTr(p.son_hata)}</button> : <span className="bos">—</span>}</td>
              <td>{p.sorunlar.length === 0 ? <span className="rozet rozet-ok">yok</span>
                : <span className="dugme-sira">{p.sorunlar.map((s) => <span key={s} className="rozet rozet-uyari">{sorunAdi(s)}</span>)}</span>}</td></tr>))}</tbody>
        </table></div>)}
      {veri && sorunlu && veri.santraller.length > 0 && <p className="soluk" style={{ fontSize: 13.5, margin: "10px 0 0" }}>{sayiTr(veri.santraller.length)} / {sayiTr(veri.toplam)} etkin santralde sorun var.</p>}
    </Kart>
  );
}
