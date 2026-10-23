import { useEffect, useState } from "react";
import { api, rolum } from "../../api/client";
import type { PaylasimListesi, PaylasilanVeri, TakimUyesi, Portfoy as PortfoyT, PortfoyDsg, PortfoyTahmin, ApiAnahtar, Webhook } from "../../api/types";
import { Kart, Kpi, Sayfa, sayiTr, gucTr, enerjiTr } from "./parcalar";
import { Meta } from "../../lib/Meta";

/** v2.263 (Dalga 5.15) — Portföy: kiracının tüm santralleri tek tabloda; toplamlar dürüst
 *  (bir santralin beklentisi yoksa toplam da yok). Satıra tıklayınca o santrala geçilir. */
export function Portfoy({ onSec, santralYenile }: { onSec: (id: string) => void;
  /** v2.303: arşivleme/geri alma sonrası üst listeyi tazele */ santralYenile?: () => void }) {
  const [p, setP] = useState<PortfoyT | null | undefined>(undefined);
  const [dsg, setDsg] = useState<PortfoyDsg | null>(null);   // v2.276
  const [pt, setPt] = useState<PortfoyTahmin | null>(null);   // v2.280
  // v2.324: TEK KAPI — üç çekirdek istek paralel gider, ÜÇÜ DE yerleşince sayfa
  // bir bütün olarak belirir. Önceki hâlde her bölüm kendi anında doluyordu
  // ("parça parça" şikâyeti); API v2.323 ile ~60-130 ms olduğundan hepsini
  // beklemek en yavaş isteğin bedeli kadardır. null artık "yok" demektir,
  // "bekliyor" değil — bölümlerin boş dalları buna göre dürüstleştirildi.
  const [hazir, setHazir] = useState(false);
  useEffect(() => {
    let acik = true;
    Promise.allSettled([api.portfoy(), api.portfoyTahmin(), api.portfoyDsg()])
      .then(([rp, rpt, rdsg]) => {
        if (!acik) return;
        setP(rp.status === "fulfilled" ? rp.value : null);
        setPt(rpt.status === "fulfilled" ? rpt.value : null);
        setDsg(rdsg.status === "fulfilled" ? rdsg.value : null);
        setHazir(true);
      });
    return () => { acik = false; };
  }, []);
  const t = p?.toplam ?? null;
  // v2.362: santraller listesi de ölçekle konuşur (bulgu 14 — 0,0 MWh kalıntısı)
  const kwhYaz = (v: number | null | undefined) => v == null ? "—" : enerjiTr(v);
  // v2.360: KPI'da birim değerin yanında ölçekle gelir (küçükte kWh, büyükte MWh)
  const enj = (v: number | null | undefined) => v == null ? "—" : enerjiTr(v);
  const tarih = (s: string | null) => s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  if (!hazir) return (
    <Sayfa baslik="Portföy" alt="Tüm santraller bir bakışta; sayılar kurulu güçle ağırlıklıdır, hesaplanamayan değerler — ile gösterilir.">
      <p className="soluk" style={{ margin: 0 }}>Yükleniyor…</p>
    </Sayfa>
  );
  return (
    <Sayfa baslik="Portföy" alt="Tüm santraller bir bakışta; sayılar kurulu güçle ağırlıklıdır, hesaplanamayan değerler — ile gösterilir."
      sag={<span className="cip">{p ? <Meta items={[`${sayiTr(p.santraller.length)} santral`, new Date(p.gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" })]} /> : "—"}</span>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        {/* v2.360: küçük portföyde MWp "0,00" okunuyordu — birim ölçekle gelir */}
        <Kpi etiket="Toplam kurulu güç"
             deger={t ? (t.kapasite_kwp < 100 ? gucTr(t.kapasite_kwp) : sayiTr(t.kapasite_kwp / 1000, 2)) : "—"}
             birim={t && t.kapasite_kwp < 100 ? "kWp" : "MWp"} alt={t ? `${sayiTr(t.santral)} santral` : ""} />
        {/* 22.10 (v2.463): iki değer tek birimle — «1.754,1 MWh · 1.755,1 MWh» kartta kesiliyordu;
            birim Kpi'nin kendi alanında bir kez yazılır, ölçek büyük olana göre seçilir. */}
        {/* 23.10 yedinci tur: «1.914,2 · 1.827,6 MWh» iki sayı tek noktalamayla okunmuyordu — bugün ana değer, yarın
            kendi etiketiyle ikinci satır (Kpi.ikinci); ölçek yine büyük olana göre ortak. */}
        {(() => {
          const ikisi = !!t && t.bugun_kwh != null && t.yarin_kwh != null;
          const kucuk = ikisi && Math.max(Math.abs(t!.bugun_kwh!), Math.abs(t!.yarin_kwh!)) < 10_000;
          const b = kucuk ? "kWh" : "MWh";
          const yaz = (v: number) => kucuk ? sayiTr(v, 0) : sayiTr(v / 1000, 1);
          return <Kpi etiket="Bugün beklenen üretim"
             deger={ikisi ? yaz(t!.bugun_kwh!) : t ? enj(t.bugun_kwh) : "—"}
             birim={ikisi ? b : undefined}
             ikinci={t ? { etiket: "Yarın", deger: ikisi ? yaz(t.yarin_kwh!) : enj(t.yarin_kwh), birim: ikisi ? b : undefined } : undefined}
             alt={t && (t.bugun_kwh == null || t.yarin_kwh == null) ? "bir santralde tahmin yok; toplam gösterilmez" : "tüm santrallerin beklenen (P50) toplamı"} />;
        })()}
        <Kpi etiket="30 günlük tahmin hatası (WMAPE)" deger={t?.wmape_agirlikli != null ? `%${sayiTr(t.wmape_agirlikli, 1)}` : "—"}
             alt={t ? `${sayiTr(t.wmape_kapsanan_kwp / 1000, 2)} MWp değerlendirmede` : ""} />
        <Kpi etiket="Açık alarm" deger={t ? sayiTr(t.acik_alarm) : "—"}
             ikinci={t ? { etiket: "Veri gecikmiş", deger: sayiTr(t.veri_gecikmis), birim: "santral" } : undefined}
             alt={t && t.santral > 0 ? "alarm: son 7 günde okunmamış kayıt; gecikme: son ölçüm 2 günden eski" : ""} ton={t && (t.acik_alarm > 0 || t.veri_gecikmis > 0) ? "uyari" : undefined} />
      </div>
      <Kart baslik="Santraller" sag={<span className="cip">satıra tıkla → santral</span>}>
        {!p || p.santraller.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu hesapta santral yok.</p>
         : (
          <div className="grafik-kaydir">
            {/* 23.10 beşinci tur: gövde ailesi + tabular (tarih/saat mono gerekmez); eski ölçüm renk + rozet metniyle
                («N gün eski») — renk dışı gösterge; satır klavyeyle odaklanır ve Enter'la açılır (davranış aynı) */}
            <table className="veri sayisal" style={{ fontSize: 14 }}>
              <thead><tr><th>Santral</th><th>kWp</th><th>Segment</th><th>Son ölçüm</th><th>Hata 30g (WMAPE)</th><th>Bugün</th><th>Yarın</th><th>Alarm</th><th>Son tahmin</th></tr></thead>
              <tbody>
                {p.santraller.map((r) => {
                  const eski = r.kesinti_gun != null && r.kesinti_gun > 2;
                  return (
                  <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => onSec(r.id)} tabIndex={0}
                      aria-label={`${r.ad}, santral sayfasını aç`}
                      onKeyDown={(e) => { if (e.key === "Enter") onSec(r.id); }}>
                    <td style={{ fontWeight: 600 }}>{r.ad}</td><td>{sayiTr(r.kapasite_kwp)}</td><td>{r.segment ?? "—"}</td>
                    <td style={{ color: eski ? "var(--uyari-metin)" : undefined }}>{tarih(r.son_olcum)}{eski && (
                      <span className="rozet rozet-uyari" style={{ marginLeft: 8, fontSize: 12 }} title="Son ölçüm 2 günden eski">{sayiTr(r.kesinti_gun!)} gün eski</span>)}</td>
                    <td>{r.wmape_30g != null ? `%${sayiTr(r.wmape_30g, 1)}` : "—"}</td><td>{kwhYaz(r.bugun_kwh)}</td><td>{kwhYaz(r.yarin_kwh)}</td>
                    <td style={{ color: r.acik_alarm > 0 ? "var(--uyari-metin)" : undefined, fontWeight: r.acik_alarm > 0 ? 600 : undefined }}>{sayiTr(r.acik_alarm)}</td><td>{tarih(r.son_kosu)}</td>
                  </tr>);
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="soluk" style={{ fontSize: 13.5, margin: "12px 0 0", maxWidth: "90ch", lineHeight: 1.55 }}>
          <b style={{ color: "var(--ikincil)", fontWeight: 500 }}>Bugün/yarın:</b> son tahminin yerel gün toplamı (beklenen, P50); 20 saatten az kapsanan gün gösterilmez.{" "}
          <b style={{ color: "var(--ikincil)", fontWeight: 500 }}>WMAPE:</b> son 30 günün 0–24 saat tahmin hatası.{" "}
          <b style={{ color: "var(--ikincil)", fontWeight: 500 }}>Alarm:</b> son 7 günde okunmamış kayıt.
        </p>
      </Kart>
      {/* v2.280 (Tablo 3.2 satır 11): hiyerarşik uzlaştırılmış portföy tahmini — toplam santral tahminleriyle tutarlı */}
      <Kart baslik="Portföyün günlük üretim tahmini" sag={<span className="cip">{pt?.durum === "ok" ? <Meta items={[pt.yontem, pt.tutarli === false && "tutarsız"]} /> : "—"}</span>}>
        {/* 23.10 yedinci tur: cümle başı tire kalktı — tire yalnız değer yerinde (tablo/KPI hücresi) */}
        {!pt || pt.durum !== "ok" ? <p className="soluk" style={{ margin: 0 }}>Henüz tahmin yok.</p> : (
          <>
            <div className="grafik-kaydir">
              <table className="veri" style={{ fontSize: 13.5 }}>
                {/* v2.362: küçük portföyde günlük toplamlar kWh konuşur (bulgu 14) */}
                {(() => { const kucukP = !(pt.gunler ?? []).some((g) => (g.p90_mwh ?? 0) >= 10);
                  const b = kucukP ? "kWh" : "MWh";
                  const yaz = (v: number) => kucukP ? sayiTr(v * 1000, 0) : sayiTr(v, 1);
                  return (<>
                <thead><tr><th>Gün</th><th>P10 ({b})</th><th>P50 ({b})</th><th>P90 ({b})</th><th>Saat</th></tr></thead>
                <tbody className="mono">
                  {(pt.gunler ?? []).map((g) => (
                    <tr key={g.gun}><td>{new Date(g.gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}</td>
                      <td>{yaz(g.p10_mwh)}</td><td style={{ fontWeight: 600 }}>{yaz(g.p50_mwh)}</td><td>{yaz(g.p90_mwh)}</td><td>{sayiTr(g.saat)}</td></tr>))}
                </tbody>
                  </>); })()}
              </table>
            </div>
            <p className="soluk" style={{ fontSize: 14, margin: "10px 0 0" }}>Santral tahminleri toplanır; toplam, santral tahminleriyle çelişmez. {pt.not}{pt.artik_gun ? ` Düzeltme geçmişi ${sayiTr(pt.artik_gun)} gün.` : ""}</p>
          </>
        )}
      </Kart>
      {/* v2.276 (Dalga 5): DSG/toplayıcı netleştirmesi — portföy tek dengesizlik hesabına girerse ne kazanılır */}
      <Kart baslik="Dengeden sorumlu grup (DSG) netleştirmesi — portföy dengesizliği" sag={<span className="cip">{dsg ? <Meta items={[`${sayiTr(dsg.pencere_gun)} gün`, dsg.fiyat.senaryo_saat > 0 ? "senaryo fiyatı" : "piyasa fiyatı (EPİAŞ)"]} /> : "—"}</span>}>
        {!dsg ? <p className="soluk" style={{ margin: 0 }}>Veri yok.</p> : dsg.ayri_tl == null ? (
          <p className="soluk" style={{ margin: 0 }}>{dsg.not ?? "Ortak saat yetersiz."}</p>
        ) : (
          <>
            <div className="ızgara satir-3" style={{ marginBottom: 10 }}>
              <Kpi etiket="Santraller ayrı ayrı" deger={sayiTr(dsg.ayri_tl / 1000, 1)} birim="bin TL" alt={`${sayiTr(dsg.santral)} santral, ${sayiTr(dsg.sapma_ayri_mwh ?? 0, 1)} MWh sapma`} />
              <Kpi etiket="Portföy netleşmiş" deger={sayiTr((dsg.net_tl ?? 0) / 1000, 1)} birim="bin TL" alt={`${sayiTr(dsg.sapma_net_mwh ?? 0, 1)} MWh net sapma`} />
              <Kpi etiket="Netleşme kazancı" deger={sayiTr((dsg.kazanc_tl ?? 0) / 1000, 1)} birim="bin TL" alt={dsg.kazanc_pct != null ? `ayrı maliyetin %${sayiTr(dsg.kazanc_pct, 1)}'i` : "—"} />
            </div>
            <p className="soluk" style={{ fontSize: 14, margin: 0 }}>{dsg.not}</p>
          </>
        )}
      </Kart>
      {rolum() === "admin" && <GelenTalepler />}
      {rolum() === "admin" && <DisErisim santraller={p?.santraller.map((s) => ({ id: s.id, ad: s.ad })) ?? []} />}
      {rolum() === "admin" && <SantralArsivi santralYenile={santralYenile} />}
      <Paylasimlar santraller={p?.santraller.map((s) => ({ id: s.id, ad: s.ad })) ?? []} />
      <HesapVeEkip />
    </Sayfa>
  );
}

/** v2.328 — vitrin "Karneni başlat" başvuruları. Yalnız yönetici görür; e-posta
 *  altyapısı bilerek yok — dönüş buradaki adrese elle yapılır, sonra "okundu". */
function GelenTalepler() {
  const [liste, setListe] = useState<{ id: string; eposta: string; santral_adi: string | null;
    kurulu_guc_kwp: number | null; okundu: boolean; created_at: string }[] | null>(null);
  const yenile = () => { api.basvurular().then((r) => setListe(r.basvurular)).catch(() => setListe([])); };
  useEffect(yenile, []);
  const acik = (liste ?? []).filter((b) => !b.okundu).length;
  if (liste !== null && liste.length === 0) return null;   // hiç başvuru yoksa kart yer kaplamaz
  return (
    <Kart baslik="Gelen talepler — web sitesi başvuruları"
      sag={<span className="cip">{liste === null ? "—" : <Meta items={[`${sayiTr(acik)} açık`, `${sayiTr(liste.length)} toplam`]} />}</span>}>
      {liste === null ? <p className="soluk" style={{ margin: 0 }}>Veri yok.</p> : (
        <div className="grafik-kaydir">
          <table className="veri" style={{ fontSize: 13.5 }}>
            <thead><tr><th style={{ textAlign: "left" }}>E-posta</th><th style={{ textAlign: "left" }}>Santral</th>
              <th>Kurulu güç</th><th style={{ textAlign: "left" }}>Tarih</th><th>Durum</th></tr></thead>
            <tbody className="mono">
              {liste.map((b) => (
                <tr key={b.id} style={{ opacity: b.okundu ? 0.55 : 1 }}>
                  <td style={{ fontWeight: b.okundu ? 400 : 600 }}>{b.eposta}</td>
                  <td>{b.santral_adi ?? "—"}</td>
                  <td>{b.kurulu_guc_kwp != null ? `${sayiTr(b.kurulu_guc_kwp / 1000, 1)} MW` : "—"}</td>
                  <td>{new Date(b.created_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" })}</td>
                  <td>{b.okundu ? "okundu" : (
                    <button className="dugme" style={{ fontSize: 13 }}
                      onClick={() => { void api.basvuruOkundu(b.id).then(yenile); }}>Okundu işaretle</button>
                  )}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="soluk" style={{ fontSize: 14, margin: "10px 0 0" }}>
        Web sitesindeki "Karnenizi başlatın" formundan gelir. Yanıt e-postası elle gönderilir;
        yanıtlayınca "okundu" işaretleyin.
      </p>
    </Kart>
  );
}

/** v2.264 (Dalga 5.16) — Dış erişim: API anahtarları + webhook alıcıları. Yalnız admin görür.
 *  Anahtar ve webhook sırrı YALNIZ üretildiği anda gösterilir; sunucu sırrı geri veremez. */
function DisErisim({ santraller }: { santraller: { id: string; ad: string }[] }) {
  const [anahtarlar, setAnahtarlar] = useState<ApiAnahtar[]>([]);
  const [kapsamlar, setKapsamlar] = useState<string[]>([]);
  const [webhooklar, setWebhooklar] = useState<Webhook[]>([]);
  const [ad, setAd] = useState(""); const [secili, setSecili] = useState<string[]>(["tahmin:oku"]);
  const [yeniAnahtar, setYeniAnahtar] = useState<string | null>(null);
  const [url, setUrl] = useState(""); const [whSantral, setWhSantral] = useState<string>("");
  const [yeniSir, setYeniSir] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const yenile = () => {
    api.apiAnahtarlari().then((r) => { setAnahtarlar(r.anahtarlar); setKapsamlar(r.kapsamlar); }).catch((e) => setHata(String(e.message ?? e)));
    api.webhooklar().then((r) => setWebhooklar(r.webhooklar)).catch(() => {});
  };
  useEffect(yenile, []);
  const tarih = (s: string | null) => s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  const dene = async (fn: () => Promise<unknown>) => { setHata(null); setMesaj(null); try { await fn(); yenile(); } catch (e) { setHata(String((e as Error).message ?? e)); } };
  const docs = api.docsAdresi();
  return (
    <Kart baslik="Dış erişim"
          sag={<span style={{ display: "flex", gap: 6 }}><span className="cip">yalnız yönetici</span>
                {docs ? <a className="cip" href={docs} target="_blank" rel="noreferrer">OpenAPI şeması ↗</a> : <span className="cip">örnek kip</span>}</span>}>
      <p className="soluk" style={{ margin: "0 0 14px", fontSize: 14, maxWidth: "100ch" }}>
        Müşteri sistemleri tahmini <span className="kod">X-API-Key</span> başlığıyla çeker; sabah tahmini üretildikten sonra webhook alıcılarına imzalı bildirim gider.
        Anahtar ve sır yalnız üretildiği anda görünür; sunucu yalnız özetini saklar.
      </p>
      {hata && <p className="ayar-durum hata" style={{ margin: "0 0 8px" }}>{hata}</p>}
      {mesaj && <p className="ayar-durum ok" style={{ margin: "0 0 8px" }}>{mesaj}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(340px, 100%), 1fr))", gap: 16 }}>
        <div>
          <div className="etiket-ust">API anahtarları</div>
          {anahtarlar.length === 0 ? <p className="soluk" style={{ fontSize: 14, margin: 0 }}>Henüz anahtar yok.</p> : (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th>Ad</th><th>Önek</th><th>Kapsam</th><th>Son kullanım</th><th>Durum</th><th></th></tr></thead>
              <tbody className="mono">{anahtarlar.map((k) => (
                <tr key={k.id} style={{ opacity: k.iptal ? 0.5 : 1 }}>
                  <td>{k.ad ?? "—"}</td><td>pvq_{k.prefix}…</td><td>{k.kapsamlar.join(", ")}</td><td>{tarih(k.son_kullanim)}</td>
                  <td>{k.iptal ? "iptal" : k.expires_at && new Date(k.expires_at) < new Date() ? "süresi doldu" : "etkin"}</td>
                  <td>{!k.iptal && <button className="dugme" style={{ fontSize: 13 }} onClick={() => dene(() => api.apiAnahtarIptal(k.id))}>İptal et</button>}</td>
                </tr>))}</tbody>
            </table></div>
          )}
          {/* 23.10 beşinci tur: form ızgarası — etiket üstte, onay grubu ve düğme kontrol satırıyla hizalı */}
          <form className="form-izgara"
                onSubmit={(e) => { e.preventDefault(); dene(async () => { const r = await api.apiAnahtarUret(ad, secili, null); setYeniAnahtar(r.anahtar); setAd(""); }); }}>
            <label className="girdi-etiket">Anahtar adı
              <input className="girdi" value={ad} onChange={(e) => setAd(e.target.value)} placeholder="ör. ticaret masası" /></label>
            <div className="girdi-etiket">Kapsam
              <div className="onay-grubu">
                {kapsamlar.map((k) => (
                  <label key={k} className="ayar-onay">
                    <input type="checkbox" checked={secili.includes(k)} onChange={(e) => setSecili(e.target.checked ? [...secili, k] : secili.filter((x) => x !== k))} />
                    <span className="kod">{k}</span>
                  </label>))}
              </div>
            </div>
            <button className="dugme" type="submit" disabled={secili.length === 0}>Anahtar üret</button>
          </form>
          {yeniAnahtar && (
            <div style={{ marginTop: 10, padding: 10, border: "1px solid var(--kenar)", borderRadius: 8, background: "var(--yuzey2)" }}>
              <div style={{ fontSize: 13, marginBottom: 4 }}>Yeni anahtar: <strong>bir daha gösterilmez</strong>, şimdi kopyalayın:</div>
              <code className="mono" style={{ fontSize: 13.5, wordBreak: "break-all", userSelect: "all" }}>{yeniAnahtar}</code>
              <div style={{ marginTop: 6 }}><button className="dugme" style={{ fontSize: 13 }} onClick={() => { navigator.clipboard?.writeText(yeniAnahtar).then(() => setMesaj("Anahtar panoya kopyalandı.")).catch(() => {}); }}>Kopyala</button>
                <button className="dugme" style={{ fontSize: 13, marginLeft: 6 }} onClick={() => setYeniAnahtar(null)}>Kapat</button></div>
            </div>)}
        </div>
        <div>
          <div className="etiket-ust">Webhook alıcıları <span className="soluk">(tahmin.yeni)</span></div>
          {webhooklar.length === 0 ? <p className="soluk" style={{ fontSize: 14, margin: 0 }}>Henüz alıcı yok.</p> : (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th>Adres</th><th>Santral</th><th>Son gönderim</th><th>Durum</th><th></th></tr></thead>
              <tbody className="mono">{webhooklar.map((w) => (
                <tr key={w.id}>
                  <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={w.url}>{w.url}</td>
                  <td>{w.santral ?? "tümü"}</td><td>{tarih(w.son_gonderim)}</td>
                  <td style={{ color: w.son_durum != null && !(w.son_durum >= 200 && w.son_durum < 300) ? "var(--uyari-metin)" : undefined }}>
                    {w.son_durum == null ? "—" : w.son_durum === 0 ? "ulaşılamadı" : `HTTP ${w.son_durum}`}{w.hata_sayisi > 0 ? ` (${sayiTr(w.hata_sayisi)} hata)` : ""}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="dugme" style={{ fontSize: 13 }} onClick={() => dene(async () => { const r = await api.webhookDene(w.id); setMesaj(r.ok ? `Deneme ulaştı (HTTP ${r.durum}).` : `Deneme başarısız (${r.durum === 0 ? "ulaşılamadı" : "HTTP " + r.durum}).`); })}>Dene</button>
                    <button className="dugme" style={{ fontSize: 13, marginLeft: 4 }} onClick={() => dene(() => api.webhookSil(w.id))}>Sil</button>
                  </td>
                </tr>))}</tbody>
            </table></div>
          )}
          <form className="form-izgara"
                onSubmit={(e) => { e.preventDefault(); dene(async () => { const r = await api.webhookEkle(url, whSantral || null); setYeniSir(r.secret); setUrl(""); }); }}>
            <label className="girdi-etiket" style={{ gridColumn: "span 2" }}>Alıcı adresi
              <input className="girdi mono" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…/pvquant-webhook" required /></label>
            <label className="girdi-etiket">Kapsam
              <select className="girdi" value={whSantral} onChange={(e) => setWhSantral(e.target.value)}>
                <option value="">tüm santraller</option>
                {santraller.map((s) => <option key={s.id} value={s.id}>{s.ad}</option>)}
              </select></label>
            <button className="dugme" type="submit">Alıcı ekle</button>
          </form>
          {yeniSir && (
            <div style={{ marginTop: 10, padding: 10, border: "1px solid var(--kenar)", borderRadius: 8 }}>
              <div style={{ fontSize: 13, marginBottom: 4 }}>İmza sırrı: <strong>bir daha gösterilmez</strong>; alıcı <span className="mono">X-PVQ-Signature</span> başlığını bununla doğrular:</div>
              <code className="mono" style={{ fontSize: 13.5, wordBreak: "break-all", userSelect: "all" }}>{yeniSir}</code>
              <div style={{ marginTop: 6 }}><button className="dugme" style={{ fontSize: 13 }} onClick={() => setYeniSir(null)}>Kapat</button></div>
            </div>)}
        </div>
      </div>
      {/* 23.10 sekizinci tur: uç yolları düz paragraf içindeki satır içi kod yerine hap çipleri (.cip-kod — santral
          arşivinin hap düğmeleriyle aynı aile: --kenar çerçeve, 999 köşe, Inter Tight/mono); notlar ayrı ikincil satır.
          Yollar, sınır ve belge yolu aynen; tıklanabilir bağlantı yoktu, eklenmedi. */}
      <div className="uc-listesi">
        <div className="etiket-ust">API uçları</div>
        <div className="uc-sira" role="list" aria-label="API uçları">
          <span className="cip cip-kod" role="listitem">/v1/dis/santraller</span>
          <span className="cip cip-kod" role="listitem">/v1/dis/santral/{"{id}"}/tahmin</span>
          <span className="cip cip-kod" role="listitem">/v1/dis/santral/{"{id}"}/kgup</span>
        </div>
        <p className="uc-not"><Meta className="uzun" items={["tahmin ucu ETag ile 304 döner", "oran sınırı dakikada 120 istek",
          <span key="belge">ayrıntı <span className="kod">docs/api/dis-api.md</span></span>]} /></p>
      </div>
    </Kart>
  );
}


/** v2.289: kuruluşlar arası paylaşım — verdiklerimiz (kurmak yalnız yönetici) + aldıklarımız (herkes görür). */
function Paylasimlar({ santraller }: { santraller: { id: string; ad: string }[] }) {
  const [liste, setListe] = useState<PaylasimListesi | null>(null);
  const [santral, setSantral] = useState(""); const [eposta, setEposta] = useState("");
  const [izinler, setIzinler] = useState<string[]>(["tahmin:oku"]);
  const [bitis, setBitis] = useState(""); const [takmaAd, setTakmaAd] = useState("");
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const [acik, setAcik] = useState<{ id: string; tur: string; veri: PaylasilanVeri } | null>(null);
  const yenile = () => { api.paylasimlar().then(setListe).catch((e) => setHata(String((e as Error).message ?? e))); };
  useEffect(yenile, []);
  const dene = async (fn: () => Promise<unknown>) => { setHata(null); setMesaj(null); try { await fn(); yenile(); } catch (e) { setHata(String((e as Error).message ?? e)); } };
  const etiket = (i: string) => liste?.izin_secenekleri.find((x) => x.deger === i)?.etiket ?? i;
  const yonetici = rolum() === "admin";
  if (liste === null) return null;
  if (!yonetici && liste.verilenler.length === 0 && liste.alinanlar.length === 0) return null;
  return (
    <Kart baslik="Kuruluşlar arası paylaşım" sag={<span className="cip"><Meta items={["yalnız okuma", "zaman sınırlı"]} /></span>}>
      <p className="soluk" style={{ margin: "0 0 10px", fontSize: 14 }}>
        Bir santralin tahmin, karne ya da gerçekleşen özetini başka bir kuruluşa (toplayıcı, danışman, alıcı) açar.
        Karşı taraf yalnız seçtiğiniz kapsamı, günlük toplam düzeyinde görür; istenirse santral adı takma adla gizlenir.
        Her erişim denetim iziyle kayda geçer.
      </p>
      {hata && <p className="ayar-durum hata" style={{ margin: "0 0 8px" }}>{hata}</p>}
      {mesaj && <p className="ayar-durum ok" style={{ margin: "0 0 8px" }}>{mesaj}</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(340px, 100%), 1fr))", gap: 16 }}>
        <div>
          <div className="etiket-ust">Verdiklerimiz</div>
          {liste.verilenler.length === 0 ? <p className="soluk" style={{ fontSize: 14, margin: 0 }}>Henüz paylaşım yok.</p> : (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th>Santral</th><th>Kuruluş</th><th>Kapsam</th><th>Bitiş</th><th>Durum</th><th></th></tr></thead>
              <tbody>{liste.verilenler.map((x) => (
                <tr key={x.id} style={{ opacity: x.aktif ? 1 : 0.5 }}>
                  <td>{x.santral}{x.takma_ad ? <span className="soluk"> → “{x.takma_ad}”</span> : null}</td>
                  <td>{x.karsi_kurulus}</td><td>{x.izinler.map(etiket).join(", ")}</td>
                  <td>{x.bitis ? new Date(x.bitis).toLocaleDateString("tr-TR") : "süresiz"}</td>
                  <td>{x.iptal ? "iptal" : x.aktif ? "etkin" : "süresi doldu"}</td>
                  <td>{yonetici && x.aktif && <button className="dugme" style={{ fontSize: 13 }}
                        onClick={() => dene(async () => { await api.paylasimIptal(x.id); setMesaj("Paylaşım iptal edildi."); })}>İptal et</button>}</td>
                </tr>))}</tbody>
            </table></div>
          )}
        </div>
        <div>
          <div className="etiket-ust">Aldıklarımız</div>
          {liste.alinanlar.length === 0 ? <p className="soluk" style={{ fontSize: 14, margin: 0 }}>Bize açılmış paylaşım yok.</p> : (
            <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th>Santral</th><th>Kuruluş</th><th>Bitiş</th><th>Görüntüle</th></tr></thead>
              <tbody>{liste.alinanlar.map((x) => (
                <tr key={x.id} style={{ opacity: x.aktif ? 1 : 0.5 }}>
                  <td>{x.santral}</td><td>{x.karsi_kurulus}</td>
                  <td>{x.bitis ? new Date(x.bitis).toLocaleDateString("tr-TR") : "süresiz"}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{x.aktif ? x.izinler.map((i) => (
                    <button key={i} className="dugme" style={{ fontSize: 13, marginRight: 4 }}
                            onClick={() => dene(async () => setAcik({ id: x.id, tur: i.split(":")[0], veri: await api.paylasimVeri(x.id, i.split(":")[0]) }))}>{etiket(i)}</button>
                  )) : <span className="soluk">kapandı</span>}</td>
                </tr>))}</tbody>
            </table></div>
          )}
          {acik && (
            <div style={{ marginTop: 10, padding: 10, border: "1px solid var(--kenar)", borderRadius: 8, background: "var(--yuzey2)" }}>
              <div style={{ fontSize: 13, marginBottom: 6, display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span><Meta items={[<strong key="ad">{acik.veri.santral}</strong>, etiket(`${acik.tur}:oku`)]} /></span>
                <button className="dugme" style={{ fontSize: 13 }} onClick={() => setAcik(null)}>Kapat</button>
              </div>
              {acik.tur === "karne" ? (
                <table className="veri" style={{ fontSize: 13 }}><tbody>
                  <tr><td>Değerlendirilen gün</td><td className="mono">{sayiTr(acik.veri.gun ?? 0)}</td></tr>
                  <tr><td>Ağırlıklı hata (WMAPE)</td><td className="mono">{acik.veri.wmape_pct == null ? "—" : `%${sayiTr(acik.veri.wmape_pct, 1)}`}</td></tr>
                  <tr><td>Kurulu güce göre hata (nMAE)</td><td className="mono">{acik.veri.nmae_pct == null ? "—" : `%${sayiTr(acik.veri.nmae_pct, 1)}`}</td></tr>
                  <tr><td>Tahmin aralığı isabeti (P10–P90)</td><td className="mono">{acik.veri.picp80 == null ? "—" : `%${sayiTr(acik.veri.picp80 * 100, 1)}`}</td></tr>
                </tbody></table>
              ) : (acik.veri.gunler?.length ?? 0) === 0 ? <p className="soluk" style={{ fontSize: 14, margin: 0 }}>{acik.veri.not ?? "Veri yok."}</p> : (
                <div className="grafik-kaydir"><table className="veri" style={{ fontSize: 13 }}>
                  <thead>{acik.tur === "tahmin"
                    ? <tr><th>Gün</th><th>P50 (kWh)</th><th>P10–P90 (kWh)</th></tr>
                    : <tr><th>Gün</th><th>Üretim (kWh)</th></tr>}</thead>
                  <tbody className="mono">{acik.veri.gunler!.map((g) => (
                    <tr key={g.gun}>
                      <td>{new Date(g.gun).toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}</td>
                      {acik.tur === "tahmin"
                        ? <><td>{g.p50_kwh == null ? "—" : sayiTr(g.p50_kwh, 0)}</td>
                            <td>{g.p10_kwh == null || g.p90_kwh == null ? "—" : `${sayiTr(g.p10_kwh, 0)} – ${sayiTr(g.p90_kwh, 0)}`}</td></>
                        : <td>{g.kwh == null ? "—" : sayiTr(g.kwh, 0)}</td>}
                    </tr>))}</tbody>
                </table></div>
              )}
            </div>
          )}
        </div>
      </div>
      {/* 23.10 beşinci tur: yeni paylaşım formu iki listenin ALTINDA tam satır (önce yarım sütuna sıkışıp sağda boşluk
          bırakıyordu) — soldan sağa: santral, karşı taraf, kapsam, bitiş, takma ad, Paylaş; isteğe bağlı alanlar
          etiketinde işaretli; gönderilen parametreler ve doğrulamalar aynı */}
      {yonetici && (
        <div className="alt-bolum">
          <div className="etiket-ust">Yeni paylaşım</div>
          <form className="form-izgara" style={{ marginTop: 6 }}
                onSubmit={(e) => { e.preventDefault(); dene(async () => {
                  const r = await api.paylasimEkle({ plant_id: santral || santraller[0]?.id, hedef_eposta: eposta,
                    izinler, bitis: bitis || null, takma_ad: takmaAd || null });
                  setMesaj(`Paylaşım kuruldu: ${r.hedef_kurulus}.`); setEposta(""); setTakmaAd(""); }); }}>
            <label className="girdi-etiket">Santral
              <select className="girdi" value={santral || santraller[0]?.id || ""} onChange={(e) => setSantral(e.target.value)}>
                {santraller.map((x) => <option key={x.id} value={x.id}>{x.ad}</option>)}
              </select></label>
            <label className="girdi-etiket">Karşı tarafın e-postası
              <input className="girdi" type="email" value={eposta} onChange={(e) => setEposta(e.target.value)} required /></label>
            <div className="girdi-etiket">Kapsam
              <div className="onay-grubu">
                {liste.izin_secenekleri.map((k) => (
                  <label key={k.deger} className="ayar-onay">
                    <input type="checkbox" checked={izinler.includes(k.deger)}
                           onChange={(e) => setIzinler(e.target.checked ? [...izinler, k.deger] : izinler.filter((x) => x !== k.deger))} />
                    <span>{k.etiket}</span>
                  </label>))}
              </div>
            </div>
            <label className="girdi-etiket">Bitiş (isteğe bağlı)
              <input className="girdi" type="date" value={bitis} onChange={(e) => setBitis(e.target.value)} /></label>
            <label className="girdi-etiket">Takma ad (isteğe bağlı)
              <input className="girdi" value={takmaAd} onChange={(e) => setTakmaAd(e.target.value)} placeholder="ör. GES-A" /></label>
            <button className="dugme" type="submit" disabled={izinler.length === 0 || santraller.length === 0}>Paylaş</button>
          </form>
        </div>
      )}
    </Kart>
  );
}


/** v2.299 — hesap ve ekip: parola değişimi herkese, ekip yönetimi yalnız yöneticiye.
 *  Geçici parola API anahtarı kalıbıyla YALNIZ bir kez gösterilir; sunucu özet saklar. */
function IkiAdimBolumu() {
  // v2.338: kullanıcının kendi 2FA'sı — kur/onayla, kapat, kurtarma yenile.
  const [durum, setDurum] = useState<{ aktif: boolean; kalan_kurtarma: number } | null>(null);
  const [kurulum, setKurulum] = useState<{ secret: string; qr_svg: string } | null>(null);
  const [kod, setKod] = useState("");
  const [kurtarma, setKurtarma] = useState<string[] | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const [mesaj, setMesaj] = useState<string | null>(null);
  const [kapatKod, setKapatKod] = useState(""); const [kapatAcik, setKapatAcik] = useState(false);
  const yenile = () => api.ikiAdimDurum().then(setDurum).catch(() => {});
  useEffect(() => { yenile(); }, []);
  const dene = async (fn: () => Promise<void>) => {
    setHata(null); setMesaj(null);
    try { await fn(); } catch (e) { setHata(String((e as Error).message ?? e)); }
  };
  return (
    <div className="alt-bolum">
      <div className="etiket-ust">İki adımlı doğrulama{" "}
        {durum && <span className={`rozet ${durum.aktif ? "rozet-ok" : ""}`} style={{ marginLeft: 8, letterSpacing: 0, textTransform: "none", ...(durum.aktif ? {} : { background: "var(--yuzey)", color: "var(--soluk)" }) }}>{durum.aktif ? "açık" : "kapalı"}</span>}</div>
      {hata && <p className="ayar-durum hata" style={{ margin: "0 0 8px" }}>{hata}</p>}
      {mesaj && <p className="ayar-durum ok" style={{ margin: "0 0 8px" }}>{mesaj}</p>}

      {kurtarma ? (
        <div style={{ padding: 12, border: "1px solid var(--kenar)", borderRadius: 8, background: "var(--yuzey2)" }}>
          <p style={{ fontSize: 13.5, margin: "0 0 8px", lineHeight: 1.6 }}>
            <strong>Kurtarma kodları bir daha gösterilmez.</strong> Telefonunuzu
            kaybederseniz her biri bir kez giriş sağlar. Güvenli bir yere kaydedin:</p>
          <div className="mono" style={{ display: "grid", gridTemplateColumns: "1fr 1fr",
            gap: "4px 16px", fontSize: 14, userSelect: "all" }}>
            {kurtarma.map((k) => <span key={k}>{k}</span>)}
          </div>
          <button className="dugme" style={{ marginTop: 10, fontSize: 13 }}
            onClick={() => { setKurtarma(null); setKod(""); yenile(); }}>Kaydettim, kapat</button>
        </div>
      ) : kurulum ? (
        <div>
          <p style={{ fontSize: 13.5, margin: "0 0 10px", lineHeight: 1.6 }}>
            Authenticator uygulamanızla (Google Authenticator, 1Password, Authy…)
            QR'ı okutun ya da anahtarı elle girin, sonra üretilen 6 haneli kodu yazın:</p>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
            <div style={{ width: 160, height: 160, background: "#fff", padding: 8, borderRadius: 8 }}
              dangerouslySetInnerHTML={{ __html: kurulum.qr_svg }} />
            <div>
              <div style={{ fontSize: 13, color: "var(--soluk)" }}>Elle giriş anahtarı</div>
              <code className="mono" style={{ fontSize: 13.5, userSelect: "all", wordBreak: "break-all" }}>{kurulum.secret}</code>
            </div>
          </div>
          <form className="ayar-kontrol" style={{ marginTop: 10 }} onSubmit={(e) => { e.preventDefault();
            dene(async () => { const r = await api.ikiAdimDogrula(kod); setKurtarma(r.kurtarma_kodlari); setKurulum(null); }); }}>
            <label className="girdi-etiket">Uygulamadaki kod
              <input className="girdi" inputMode="numeric" value={kod} onChange={(e) => setKod(e.target.value)} required /></label>
            <button className="dugme" type="submit">Doğrula ve aç</button>
            <button className="dugme" type="button" onClick={() => { setKurulum(null); setKod(""); }}>Vazgeç</button>
          </form>
        </div>
      ) : durum?.aktif ? (
        <div>
          <p style={{ fontSize: 13.5, margin: "0 0 8px" }}>
            Açık. Kalan kurtarma kodu: <strong>{durum.kalan_kurtarma}</strong></p>
          {!kapatAcik ? (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className="dugme" style={{ fontSize: 13 }} onClick={() => setKapatAcik(true)}>Kapat</button>
              <button className="dugme" style={{ fontSize: 13 }}
                onClick={() => dene(async () => { const r = await api.ikiAdimKurtarmaYenile(
                  prompt("Yenilemek için uygulamadaki 6 haneli kodu ya da bir kurtarma kodunu girin:") || "");
                  setKurtarma(r.kurtarma_kodlari); })}>Kurtarma kodlarını yenile</button>
            </div>
          ) : (
            <form className="ayar-kontrol" onSubmit={(e) => { e.preventDefault();
              dene(async () => { await api.ikiAdimKapat(kapatKod); setKapatAcik(false); setKapatKod("");
                setMesaj("İki adımlı doğrulama kapatıldı."); yenile(); }); }}>
              <label className="girdi-etiket">Kapatmak için kod
                <input className="girdi" value={kapatKod} onChange={(e) => setKapatKod(e.target.value)} required /></label>
              <button className="dugme" type="submit">Kapat</button>
              <button className="dugme" type="button" onClick={() => { setKapatAcik(false); setKapatKod(""); }}>Vazgeç</button>
            </form>
          )}
        </div>
      ) : (
        <div>
          <p style={{ fontSize: 13.5, margin: "0 0 8px", color: "var(--ikincil)", lineHeight: 1.6 }}>
            Kapalı. Açtığınızda girişte parolanıza ek olarak authenticator
            uygulamanızdaki 6 haneli kod istenir.</p>
          <button className="dugme" onClick={() => dene(async () => {
            const r = await api.ikiAdimBaslat(); setKurulum({ secret: r.secret, qr_svg: r.qr_svg }); })}>
            İki adımlı doğrulamayı aç</button>
        </div>
      )}
    </div>
  );
}

function HesapVeEkip() {
  const [uyeler, setUyeler] = useState<TakimUyesi[]>([]);
  const [roller, setRoller] = useState<string[]>([]);
  const [eposta, setEposta] = useState(""); const [rol, setRol] = useState("viewer");
  const [gecici, setGecici] = useState<{ email: string; parola: string } | null>(null);
  const [eski, setEski] = useState(""); const [yeni, setYeni] = useState("");
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const yonetici = rolum() === "admin";
  const yenile = () => { if (yonetici) api.takim().then((r) => { setUyeler(r.uyeler); setRoller(r.roller); }).catch(() => {}); };
  useEffect(yenile, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const dene = async (fn: () => Promise<void>) => {
    setHata(null); setMesaj(null);
    try { await fn(); yenile(); } catch (e) { setHata(String((e as Error).message ?? e)); }
  };
  const tarih = (t: string | null) => t ? new Date(t).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  return (
    <Kart baslik="Hesap ve ekip" sag={<span className="cip"><Meta items={["parola herkese", "üye yönetimi yalnız yönetici"]} /></span>}>
      {hata && <p className="ayar-durum hata" style={{ margin: "0 0 8px" }}>{hata}</p>}
      {mesaj && <p className="ayar-durum ok" style={{ margin: "0 0 8px" }}>{mesaj}</p>}
      <div className="etiket-ust">Parolamı değiştir</div>
      <form className="form-izgara" onSubmit={(e) => { e.preventDefault();
              dene(async () => { await api.parolaDegistir(eski, yeni); setEski(""); setYeni(""); setMesaj("Parolanız değiştirildi."); }); }}>
        <label className="girdi-etiket">Mevcut parola
          <input className="girdi" type="password" autoComplete="current-password" value={eski} onChange={(e) => setEski(e.target.value)} required /></label>
        <label className="girdi-etiket">Yeni parola (en az 10 karakter)
          <input className="girdi" type="password" autoComplete="new-password" minLength={10} value={yeni} onChange={(e) => setYeni(e.target.value)} required /></label>
        <button className="dugme" type="submit">Değiştir</button>
      </form>
      <IkiAdimBolumu />
      {yonetici && (
        <div className="alt-bolum">
          <div className="etiket-ust">Ekip</div>
          {uyeler.length > 0 && (
            <div className="grafik-kaydir"><table className="veri sayisal" style={{ fontSize: 14 }}>
              <thead><tr><th>E-posta</th><th>Rol</th><th>Son giriş</th><th>Durum</th><th>2FA</th><th></th></tr></thead>
              <tbody>{uyeler.map((u) => (
                <tr key={u.id} style={{ opacity: u.aktif ? 1 : 0.5 }}>
                  <td>{u.email}</td>
                  <td><select className="girdi kucuk" value={u.rol}
                        onChange={(e) => dene(async () => { await api.takimGuncelle(u.id, { rol: e.target.value }); setMesaj("Rol güncellendi."); })}>
                        {roller.map((r) => <option key={r} value={r}>{r === "admin" ? "yönetici" : r === "editor" ? "editör" : "izleyici"}</option>)}
                      </select></td>
                  <td>{tarih(u.son_giris)}</td>
                  <td>{u.aktif ? <span className="rozet rozet-ok">etkin</span> : <span className="rozet" style={{ background: "var(--yuzey)", color: "var(--soluk)" }}>pasif</span>}</td>
                  {/* v2.339: kilitlenme çıkışı — telefonunu ve kurtarma kodlarını
                      birlikte kaybeden üyenin 2FA'sını yönetici kapatabilir */}
                  <td>{u.iki_adim ? (
                    <span className="islem-onay" style={{ justifyContent: "flex-end" }}>
                      <span className="rozet rozet-ok">açık</span>
                      <button className="dugme kucuk"
                        onClick={() => { if (confirm(`${u.email} için iki adımlı doğrulama kapatılsın mı? Üye girişte yalnız parolasını kullanır ve dilerse yeniden kurar.`))
                          dene(async () => { await api.takimIkiAdimSifirla(u.id); setMesaj("Üyenin iki adımlı doğrulaması kapatıldı."); }); }}>
                        Sıfırla</button>
                    </span>
                  ) : <span className="soluk">kapalı</span>}</td>
                  {/* 23.10: pasifleştirme tehlikeli işlem dilinde (uyarı rengi, dolgu yok); davranış aynı */}
                  <td><button className={`dugme${u.aktif ? " dugme-tehlike" : ""}`} style={{ fontSize: 13 }}
                        onClick={() => dene(async () => { await api.takimGuncelle(u.id, { aktif: !u.aktif }); setMesaj(u.aktif ? "Üye pasifleştirildi; oturum açamaz." : "Üye yeniden etkin."); })}>
                        {u.aktif ? "Pasifleştir" : "Etkinleştir"}</button></td>
                </tr>))}</tbody>
            </table></div>
          )}
          {uyeler.length > 0 && <div className="etiket-ust" style={{ marginTop: 16 }}>Yeni üye</div>}
          <form className="form-izgara" style={{ marginTop: 6 }} onSubmit={(e) => { e.preventDefault();
                  dene(async () => { const r = await api.takimEkle(eposta, rol); setGecici({ email: r.email, parola: r.gecici_parola }); setEposta(""); }); }}>
            <label className="girdi-etiket">E-posta
              <input className="girdi" type="email" value={eposta} onChange={(e) => setEposta(e.target.value)} required /></label>
            <label className="girdi-etiket">Rol
              <select className="girdi" value={rol} onChange={(e) => setRol(e.target.value)}>
                <option value="viewer">izleyici</option><option value="editor">editör</option><option value="admin">yönetici</option>
              </select></label>
            <button className="dugme" type="submit">Üye ekle</button>
          </form>
          {gecici && (
            <div style={{ marginTop: 10, padding: 10, border: "1px solid var(--kenar)", borderRadius: 8, background: "var(--yuzey2)" }}>
              <div style={{ fontSize: 13, marginBottom: 4 }}>
                <span className="mono">{gecici.email}</span> için geçici parola: <strong>bir daha gösterilmez</strong>, güvenli kanaldan iletin; üye girişte kendi parolasını değiştirsin:</div>
              <code className="mono" style={{ fontSize: 14, userSelect: "all" }}>{gecici.parola}</code>
              <div style={{ marginTop: 6 }}><button className="dugme" style={{ fontSize: 13 }} onClick={() => setGecici(null)}>Kapat</button></div>
            </div>)}
          <p className="soluk" style={{ fontSize: 14, margin: "10px 0 0" }}>
            Pasif üye oturum açamaz; kaydı ve geçmiş atamaları silinmez. Son etkin yönetici düşürülemez.
          </p>
        </div>
      )}
    </Kart>
  );
}


/** v2.303 — santral yaşam döngüsünün öbür ucu: arşivle (v2.54 sözleşmesi: SİLMEZ) ve geri al.
 *  Son etkin santral arşivlenemez — sunucu korur, panel dürüstçe iletir. */
function SantralArsivi({ santralYenile }: { santralYenile?: () => void }) {
  const [arsiv, setArsiv] = useState<{ id: string; name: string; capacity_kwp: number }[]>([]);
  const [etkin, setEtkin] = useState<{ id: string; name: string }[]>([]);
  const [onayId, setOnayId] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null); const [mesaj, setMesaj] = useState<string | null>(null);
  const yenile = () => {
    api.santralArsivi().then((r) => setArsiv(r.santraller)).catch(() => {});
    api.santraller().then((l) => setEtkin(l.map((x) => ({ id: x.id, name: x.name })))).catch(() => {});
  };
  useEffect(yenile, []);
  const dene = async (fn: () => Promise<void>) => {
    setHata(null); setMesaj(null);
    try { await fn(); yenile(); santralYenile?.(); } catch (e) { setHata(String((e as Error).message ?? e)); }
  };
  if (etkin.length < 2 && arsiv.length === 0) return null;   // tek santral + boş arşiv: kart gereksiz
  return (
    <Kart baslik="Santral arşivi" sag={<span className="cip"><Meta items={["silmez", "veri denetim için durur"]} /></span>}>
      <p className="soluk" style={{ margin: "0 0 10px", fontSize: 14 }}>
        Arşivlenen santral listelerden ve gece hesaplamalarından çıkarılır; ölçüm, kalibrasyon ve tahmin geçmişi
        yerinde kalır ve geri alınabilir. Son etkin santral arşivlenemez.
      </p>
      {hata && <p className="ayar-durum hata" style={{ margin: "0 0 8px" }}>{hata}</p>}
      {mesaj && <p className="ayar-durum ok" style={{ margin: "0 0 8px" }}>{mesaj}</p>}
      {/* 23.10 sekizinci tur: «Edikli GES — arşivle…» hap düğmeleri → satır listesi: santral adı solda, işlem düğmesi
          sağda; onay aynı satırda tehlikeli işlem dilinde. onClick/api çağrıları aynen. */}
      {etkin.length > 1 && (
        <ul className="islem-listesi">
          {etkin.map((x) => (
            <li key={x.id}>
              <span className="islem-ad">{x.name}</span>
              {onayId === x.id ? (
                <span className="islem-onay">
                  <button className="dugme dugme-tehlike" style={{ fontWeight: 600 }}
                          onClick={() => dene(async () => { await api.santralArsivle(x.id); setOnayId(null); setMesaj(`${x.name} arşive alındı.`); })}>
                    Eminim, arşive al</button>
                </span>
              ) : (
                <button className="dugme kucuk" onClick={() => setOnayId(x.id)}>Arşivle…</button>
              )}
            </li>
          ))}
        </ul>
      )}
      {arsiv.length > 0 && (
        <div className="grafik-kaydir" style={{ marginTop: 10 }}><table className="veri" style={{ fontSize: 13.5 }}>
          <thead><tr><th style={{ textAlign: "left" }}>Arşivdeki santral</th><th>Kurulu güç</th><th></th></tr></thead>
          <tbody>{arsiv.map((x) => (
            <tr key={x.id}>
              <td style={{ textAlign: "left" }}>{x.name}</td>
              <td className="mono">{gucTr(x.capacity_kwp)} kWp</td>
              <td><button className="dugme" style={{ fontSize: 13 }}
                    onClick={() => dene(async () => { await api.santralGeriAl(x.id); setMesaj(`${x.name} geri alındı.`); })}>Geri al</button></td>
            </tr>))}</tbody>
        </table></div>
      )}
    </Kart>
  );
}
