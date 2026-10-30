import { useEffect, useMemo, useState } from "react";
import { useDamgaSurumu } from "../../shell/damgaOlay";
import { api, bellekten, ayniysaEskisi } from "../../api/client";
import type { KgupRevizyon, SantralOzeti, TahminSerisi, KgupOnizleme, KgupSurum, KgupKiyas, Nowcast } from "../../api/types";
import { Kart, Sayfa, sayiTr, SayfaIskeleti, YerTutucu } from "./parcalar";
import { Meta } from "../../lib/Meta";
import ProductionForecastChart, { type ActualPoint, type ForecastPoint, type Plant } from "./ProductionForecastChart";
import {
  GUNLUK_MOD,
  dilimle,
  gunlukToplamlar,
  simdiDegeri,
  t0Hesapla,
  type Ufuk,
} from "./tahminPencere";

/**
 * v2 (data-correctness pass, D1/D2/D4/D5/D6):
 *  - ONE fetch: the full archive series (ufuk="16d"); every tab is a
 *    client-side slice around ONE anchor t0 (now floored to the hour).
 *  - The now-value is computed once and shared by all views (D2).
 *  - Daily totals derive from the plotted slice, so rows always match the
 *    window; P10–P90 totals populate from the hourly quantiles, and the
 *    column disappears entirely when the run has none (D6).
 *  - "16d" tab renamed "15g": the horizon is 360 h (v2.156 user decision);
 *    the subtitle states the ACTUAL forecast hours in the slice, with the
 *    past context declared separately (D4).
 */

const UFUK = { "24h": "24s", "72h": "72s", "7d": "7g", "16d": "15g" } as const;
// 29.10 (F-05 #4): panelin önerdiği her kantil indirilebilir
const KGUP_KANTILLER = ["p10", "p25", "p50", "p75", "p90"] as const;
type KgupKantil = (typeof KGUP_KANTILLER)[number];
// 24.10: grafik özellikleri sabit nesne — her render'da yeni {} üretilip option'ın yeniden kurulmasını önler
const GRAFIK_OZELLIKLERI = { exportButtons: true } as const;  // v2.228: PNG/CSV — SaaS eylemi

export function Tahminler({ plantId }: { plantId: string }) {
  const ds = useDamgaSurumu();   // 26.10 eşzamanlama
  const [ufuk, setUfuk] = useState<Ufuk>("7d");
  // 24.10 açık tema geçiş turu — BEŞ İSTEK BAĞIMSIZ, BAYAT-ÖNCE (Portföy kalıbı). v2.327'nin tek kapısı grafiği KGÜP
  // önizleme/nowcast/koşu listesine bekletiyordu. Şimdi grafik, tahmin serisi + özet gelir gelmez; program, kısa ufuk ve
  // aralık notu kendi yanıtlarını bekler (yer tutucu). Bellekte son seri/özet varsa sayfa anında çizilir.
  // undefined = yolda, null = yok/alınamadı. ufuk seçici istemci tarafı dilimleme (değişmedi).
  type Durum = "bekliyor" | "tamam" | "hata";
  const [seri, setSeri] = useState<TahminSerisi | null | undefined>(() => bellekten.tahmin(plantId, "16d"));
  const [ozet, setOzet] = useState<SantralOzeti | null | undefined>(() => bellekten.ozet(plantId));
  const [cekD, setCekD] = useState<{ seri: Durum; ozet: Durum }>({ seri: "bekliyor", ozet: "bekliyor" });
  const [kgup, setKgup] = useState<KgupOnizleme | null | undefined>(undefined);   // v2.260
  const [kgupHata, setKgupHata] = useState<string | null>(null);
  const [kgupKantil, setKgupKantil] = useState<KgupKantil>("p50");   // 29.10
  const [surumler, setSurumler] = useState<KgupSurum[] | undefined>(undefined);   // v2.502 (F-06): indirilen dosyaların sürüm geçmişi
  const surumleriYenile = () => { api.kgupSurumler(plantId).then((v) => setSurumler(v)); };
  const [kiyas, setKiyas] = useState<KgupKiyas | null>(null);   // v2.503: bildirilen ↔ öneri
  const [yukleMesaj, setYukleMesaj] = useState<string | null>(null);
  // 29.10 (v2.506): dışa aktarma biçimi müşterinin dosyasından öğrenilebilir; v2.512: varsayılan artık resmî TPYS KGUP.csv ile birebir
  const [sablonMesaj, setSablonMesaj] = useState<string | null>(null);
  const sablonOgren = (dosya: File) => {
    setSablonMesaj(null);
    api.kgupSablonOgren(plantId, dosya).then((r) => {
      setSablonMesaj(`Öğrenildi: ${r.sablon.kolonlar.join(" · ")}; ayraç «${r.sablon.ayrac}», ondalık «${r.sablon.ondalik}».${r.eslesmeyen.length ? ` Yazılmayan kolonlar: ${r.eslesmeyen.join(", ")}.` : ""}${r.uyarilar.length ? ` ${r.uyarilar.join(" ")}` : ""}`);
      api.kgupOnizleme(plantId).then((v) => setKgup(v)).catch(() => {});
    }).catch((e) => setSablonMesaj(String((e as Error).message ?? e)));
  };
  const sablonSifirla = () => {
    setSablonMesaj(null);
    api.kgupSablonSifirla(plantId).then(() => { setSablonMesaj("Varsayılan biçime dönüldü."); api.kgupOnizleme(plantId).then((v) => setKgup(v)).catch(() => {}); })
      .catch((e) => setSablonMesaj(String((e as Error).message ?? e)));
  };
  const bildirilenYukle = (gun: string, dosya: File) => {
    setYukleMesaj(null);
    api.kgupBildirilenYukle(plantId, gun, dosya).then((r) => { setKiyas(r.kiyas); setYukleMesaj(r.kayit.yeni ? `Kaydedildi: bildirilen sürüm ${r.kayit.surum}, ${sayiTr(r.kayit.toplam_mwh, 1)} MWh.` : "Aynı içerik zaten kayıtlı."); surumleriYenile(); })
      .catch((e) => setYukleMesaj(String((e as Error).message ?? e)));
  };
  const [nc, setNc] = useState<Nowcast | null | undefined>(undefined);   // v2.266
  const [rv, setRv] = useState<KgupRevizyon | null | undefined>(undefined);   // v2.507 (F-10)
  // v2.273: son koşunun bant kaynağı (ensemble üyeleri / model) — dip notta dürüstçe söylenir
  const [bantYazisi, setBantYazisi] = useState<string | null>(null);
  useEffect(() => {
    let acik = true;
    setSeri(bellekten.tahmin(plantId, "16d")); setOzet(bellekten.ozet(plantId)); setCekD({ seri: "bekliyor", ozet: "bekliyor" });
    setKgup(undefined); setNc(undefined); setBantYazisi(null);
    api.tahmin(plantId, "16d").then((v) => { if (acik) { setSeri((e) => ayniysaEskisi(e, v)); setCekD((d) => ({ ...d, seri: "tamam" })); } }, () => { if (acik) { setSeri((e) => e ?? null); setCekD((d) => ({ ...d, seri: "hata" })); } });
    api.ozet(plantId).then((v) => { if (acik) { setOzet((e) => ayniysaEskisi(e, v)); setCekD((d) => ({ ...d, ozet: "tamam" })); } }, () => { if (acik) { setOzet((e) => e ?? null); setCekD((d) => ({ ...d, ozet: "hata" })); } });
    api.kgupOnizleme(plantId).then((v) => { if (acik) setKgup(v); }, () => { if (acik) setKgup(null); });
    setRv(undefined); api.kgupRevizyon(plantId).then((v) => { if (acik) setRv(v); }, () => { if (acik) setRv(null); });
    api.kgupSurumler(plantId).then((v) => { if (acik) setSurumler(v); });
    api.nowcast(plantId).then((v) => { if (acik) setNc(v); }, () => { if (acik) setNc(null); });
    api.kosular(plantId).then((k) => {
      if (!acik) return;
      const b = k[0]?.bant;
      const s = k[0]?.sapma;
      const sy = s?.aktif ? `; son ${sayiTr(s.n_gun ?? 0)} günün ölçümüyle %${sayiTr(((s.oran_genel ?? 1) - 1) * 100, 1)} düzeltildi` : "";
      const gi = k[0]?.etiket === "gun_ici" ? "; gün içi güncelleme (güncel bölgesel hava tahmini)" : "";
      setBantYazisi((!b ? "" : b.kaynak === "gefs" ? `${sayiTr(b.uye ?? 0)} üyeli hava tahmini topluluğundan türetilen aralık` : "model aralığı") + sy + gi || null);
    }, () => { if (acik) setBantYazisi(null); });
    return () => { acik = false; };
  }, [plantId, ds]);   // 26.10 eşzamanlama: damga değişince yeniden çekilir
  // sayfa, seri ve özet ikisi de bilinince (bellekten ya da ağdan) çizilir; biri alınamadıysa boş durum
  const hazir = (seri !== undefined || cekD.seri !== "bekliyor") && (ozet !== undefined || cekD.ozet !== "bekliyor");
  const tazeleniyor = hazir && (cekD.seri === "bekliyor" || cekD.ozet === "bekliyor");

  const t0 = useMemo(() => t0Hesapla(Date.now()), []);
  const nowVal = useMemo(
    () => (seri ? simdiDegeri(seri.saatlik, t0) : null),
    [seri, t0],
  );
  const dilim = useMemo(
    () => (seri ? dilimle(seri.saatlik, t0, ufuk) : null),
    [seri, t0, ufuk],
  );
  const gunlukVeri = useMemo(
    () =>
      dilim && ozet ? gunlukToplamlar(dilim.saatlik, ozet.tz) : [],
    [dilim, ozet],
  );
  const bantVar = gunlukVeri.some((g) => g.p10Kwh !== null);
  // 24.10: grafik girdileri dilim/seri/özet değişmeden aynı referans kalır — KGÜP, nowcast, koşu yanıtları ya da
  // tema değişimi geldiğinde ECharts option'ı boşuna yeniden kurulmaz (eski inline map'ler her render'da yeni diziydi)
  const grafikTahmin = useMemo<ForecastPoint[]>(
    () => (dilim ? dilim.saatlik.map((s) => ({ ts: s.ts, p10: s.p10_kw, p50: s.p50_kw, p90: s.p90_kw, p25: s.p25_kw, p75: s.p75_kw })) : []),
    [dilim],
  );
  const grafikGercek = useMemo<ActualPoint[]>(
    () => (dilim ? dilim.saatlik.filter((s) => s.gercek_kw !== null).map((s) => ({ ts: s.ts, kw: s.gercek_kw as number })) : []),
    [dilim],
  );
  const grafikSantral = useMemo<Plant | null>(
    () => (seri && ozet ? { acCapacityKw: seri.ac_tavani_kw ?? ozet.ac_tavani_kw, lat: ozet.lat, lon: ozet.lon, timezone: ozet.tz } : null),
    [seri, ozet],
  );

  if (!hazir) return <SayfaIskeleti kpi={0} kart={2} />;
  return (
    <Sayfa
      baslik="Tahminler"
      alt={
        dilim
          ? `${dilim.tahminSaat} saatlik tahmin, son ${dilim.gecmisSaat} saatin geçmişiyle; en son tahmin.`
          : ""
      }
      sag={
        <>
          {(tazeleniyor || cekD.seri === "hata" || cekD.ozet === "hata") && (
            <span className="cip">{tazeleniyor ? "güncelleniyor" : "güncellenemedi"}</span>
          )}
          <div className="sekme">
            {(Object.keys(UFUK) as Ufuk[]).map((u) => (
              <button
                key={u}
                aria-pressed={u === ufuk}
                onClick={() => setUfuk(u)}
              >
                {UFUK[u]}
              </button>
            ))}
          </div>
        </>
      }
    >
      {/* v2.260 (Dalga 4.13): KGÜP bildirim dosyası — D-1 15:30 öncesi koşudan saatlik program (TPYS CSV) */}
      {/* 23.10 altıncı tur: hiyerarşi — (1) program özeti: büyük değer + seviye/tahmin zamanı + teslim günü ve
          bildirim durumu rozeti; (2) indirme düğmeleri iki etiketli küme (bildirim dosyası · toplayıcı);
          (3) piyasa takvimi kuralı açılır alanda. Düğmelerin onClick'leri ve api çağrıları aynen. */}
      {/* 29.10 (05 §5, 08 #10): KGÜP kartı ilk ekranda, tek birincil eylem (.dugme-ana), kantil seçimi (P10/P25/P50/P75/P90),
          dosya özeti (SHA-256) ve «indirilen dosya teslim sayılmaz» notu; şablon durumu açık */}
      <Kart baslik="Üretim programı (KGÜP) — yarının saatlik programı"
        sag={<span className="cip">{kgup ? <Meta items={[`teslim günü ${new Date(kgup.teslim.hedef_gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}`, `teyit ${kgup.teslim.teyit_saati.slice(0, 5)}`]} /> : kgup === undefined ? "hesaplanıyor" : "tahmin bekleniyor"}</span>}>
        {kgup === undefined ? (
          /* 24.10: yanıt yoldayken «program henüz yok» yazılmaz — yer tutucu (önce boş durum görünüp sonra doluyordu) */
          <YerTutucu yukseklik={140} />
        ) : kgup ? (
          <>
            <div className="program-ozet">
              <span className="sayi-buyuk">{sayiTr(kgup.toplam_mwh, 1)} <small style={{ fontSize: 15, fontWeight: 400, color: "var(--soluk)" }}>MWh</small></span>
              <span className="soluk" style={{ fontSize: 13.5 }}><Meta items={[kgup.kantil.toUpperCase(), `tahmin ${kgup.kosu.run_at ? new Date(kgup.kosu.run_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—"}`]} /></span>
              <span className={`rozet ${kgup.teslim.durum === "pencere_acik" ? "rozet-ok" : "rozet-notr"}`}>
                bildirim saati {kgup.teslim.durum === "pencere_acik" ? "açık" : kgup.teslim.durum === "erken" ? "henüz açılmadı" : "kapandı"} (14:00–15:30)
              </span>
              {kgup.oneri && kgup.oneri.durum === "ok" && kgup.oneri.kantil &&
                <span className="cip" title={kgup.oneri.not ?? ""}>önerilen seviye {kgup.oneri.kantil.toUpperCase()}</span>}
              {kgup.eak && <span className="cip" title="Verilebilecek en yüksek güç (mevzuatta emre amade kapasite, EAK); Santral ayarları › Program sınırları">EAK {sayiTr(kgup.eak.eak_mw, 2)} MW ({({ gecici: "geçici kısıt", eak_alani: "EAK alanı", ac_tavani: "AC sınırı", kurulu_guc: "kurulu güç" } as Record<string, string>)[kgup.eak.kaynak] ?? kgup.eak.kaynak})</span>}
            </div>
            <div className="dugme-grubu">
              <div>
                <div className="etiket-ust">Bildirim dosyası</div>
                <div className="dugme-sira">
                  <select className="girdi" aria-label="Program seviyesi (kantil)" value={kgupKantil} onChange={(e) => setKgupKantil(e.target.value as KgupKantil)}>
                    {KGUP_KANTILLER.map((k) => <option key={k} value={k}>{k.toUpperCase()}{k === "p50" ? " (beklenen)" : k === "p10" ? " (temkinli)" : k === "p90" ? " (iddialı)" : ""}</option>)}
                  </select>
                  <button className="dugme dugme-ana" onClick={() => { setKgupHata(null); api.kgupIndir(plantId, undefined, kgupKantil).then(surumleriYenile).catch((e) => setKgupHata(String(e.message ?? e))); }}>KGÜP (CSV)</button>
                  {/* v2.512: EAK TPYS'de ayrı ekran ve ayrı dosya (EAK.csv; 09:00–15:30); kurulu güç farkı «kaynak yetersizliği» sütununda */}
                  <button className="dugme" title="TPYS «EAK giriş» ekranı için ayrı dosya (EAK.csv biçimi); bildirim saati 09:00–15:30" onClick={() => { setKgupHata(null); api.kgupIndir(plantId, undefined, kgupKantil, "eak").catch((e) => setKgupHata(String(e.message ?? e))); }}>EAK (CSV)</button>
                </div>
              </div>
              {/* v2.275: toplayıcı/DSG çıktısı — bantlı saatlik ve 15 dk (2027 hazırlığı) */}
              <div>
                <div className="etiket-ust">Toplayıcı / DSG</div>
                <div className="dugme-sira">
                  <button className="dugme" onClick={() => { setKgupHata(null); api.toplayiciIndir(plantId, "xlsx", 60).catch((e) => setKgupHata(String(e.message ?? e))); }}>Toplayıcı (Excel, saatlik)</button>
                  <button className="dugme" onClick={() => { setKgupHata(null); api.toplayiciIndir(plantId, "csv", 15).catch((e) => setKgupHata(String(e.message ?? e))); }}>Toplayıcı (CSV, 15 dk)</button>
                </div>
              </div>
            </div>
            {kgupHata && <p style={{ color: "var(--uyari-metin)", fontSize: 13.5, margin: "8px 0 0" }}>{kgupHata}</p>}
            <p className="soluk" style={{ fontSize: 13.5, margin: "8px 0 0" }}>
              {kgup.bildirim ?? "Dosya PVQuant'ta üretildi; TPYS'ye gönderim ve kabul müşterinin sisteminden yapılır — indirilen dosya teslim edilmiş sayılmaz."}
              {kgup.sablon && ` Dosya biçimi: ${kgup.sablon.kaynak ? "müşteri dosyasından öğrenildi" : "TPYS şablonu (KGUP.csv, EAK.csv)"}.`}{kgup.sha256 && ` Dosya özeti (SHA-256): ${kgup.sha256.slice(0, 12)}…`}
            </p>
            {kgup.uyarilar.length > 0 && <ul className="not-listesi uyari">{kgup.uyarilar.map((u) => <li key={u}>{u}</li>)}</ul>}
            {kgup.sicrama_saatleri.length > 0 && <p style={{ fontSize: 13.5, margin: "8px 0 0" }}>≥200 MWh ani değişim: saat {kgup.sicrama_saatleri.join(", ")}; dosyada 15 dakikalık adımlar.</p>}
            {/* v2.502 (F-06): sürüm geçmişi — her indirme değiştirilemez kayıt; aynı içerik yeni sürüm açmaz; dosya bayt bayt geri alınır */}
            <details className="aciklama genis">
              <summary>Sürüm geçmişi{surumler && surumler.length > 0 ? ` (${sayiTr(surumler.length)} kayıt)` : ""}</summary>
              {surumler === undefined ? <p className="soluk">yükleniyor…</p>
               : surumler.length === 0 ? <p className="soluk">Henüz indirilmiş dosya yok. Her «CSV indir» sürüm olarak saklanır; aynı içerik yeniden indirilince yeni sürüm açılmaz.</p>
               : (
                <div className="grafik-kaydir">
                  <table className="veri" style={{ fontSize: 13 }}>
                    <thead><tr><th>Teslim günü</th><th>Kaynak</th><th>Sürüm</th><th>Seviye</th><th>Tahmin</th><th>Toplam (MWh)</th><th>İndiren</th><th>Kayıt</th><th>Özet (SHA-256)</th><th aria-hidden="true" /></tr></thead>
                    <tbody>
                      {surumler.map((v) => (
                        <tr key={v.id}>
                          <td>{new Date(v.teslim_gunu + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}</td>
                          <td>{v.kaynak === "musteri" ? <span className="rozet rozet-notr rozet-kucuk" title="Müşteri beyanı; TPYS kabulü doğrulanmadı">bildirilen</span> : "öneri"}</td>
                          <td>{v.surum}</td><td>{v.kantil === "bildirilen" ? "—" : v.kantil.toUpperCase()}</td>
                          <td>{v.run_at ? new Date(v.run_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—"}</td>
                          <td>{v.toplam_mwh != null ? sayiTr(v.toplam_mwh, 1) : "—"}</td>
                          <td>{v.indiren ?? "API"}</td>
                          <td>{new Date(v.olusturma).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" })}</td>
                          <td title={v.sha256}>{v.sha256.slice(0, 12)}…</td>
                          <td><button className="dugme" onClick={() => { setKgupHata(null); api.kgupSurumIndir(plantId, v.id).catch((e) => setKgupHata(String(e.message ?? e))); }}>İndir</button></td>
                        </tr>))}
                    </tbody>
                  </table>
                </div>
              )}
            </details>
            {/* v2.503 (F-06): müşterinin TPYS'ye bildirdiği dosya — beyan kaydı + öneriyle saat saat kıyas */}
            <details className="aciklama genis" onToggle={(e) => { if ((e.currentTarget as HTMLDetailsElement).open && kiyas === null) api.kgupKiyas(plantId, kgup.gun).then((v) => { if (v) setKiyas(v); }); }}>
              <summary>Bildirilen KGÜP ile kıyas</summary>
              <p className="soluk" style={{ fontSize: 13.5, margin: "0 0 8px" }}>
                TPYS'ye yüklediğiniz dosyayı buraya da yükleyin; beyan olarak değiştirilemez biçimde saklanır ve PVQuant önerisiyle saat saat kıyaslanır. TPYS kabulü burada doğrulanmaz.
              </p>
              <label className="girdi-etiket">Bildirilen dosya ({new Date(kgup.gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" })} için)
                <input className="girdi" type="file" accept=".csv,text/csv" onChange={(e) => { const f = e.target.files?.[0]; if (f) bildirilenYukle(kgup.gun, f); e.target.value = ""; }} /></label>
              {yukleMesaj && <p style={{ fontSize: 13.5, margin: "8px 0 0", color: yukleMesaj.startsWith("Kaydedildi") || yukleMesaj.startsWith("Aynı") ? undefined : "var(--uyari-metin)" }}>{yukleMesaj}</p>}
              {kiyas && kiyas.ozet && (
                <>
                  <p style={{ fontSize: 13.5, margin: "8px 0 6px" }}>
                    {kiyas.ozet.ayni ? "Bildirilen program öneriyle aynı." : <>Bildirilen program öneriden {sayiTr(kiyas.ozet.farkli_saat)} saatte ayrılıyor: toplam fark {sayiTr(kiyas.ozet.fark_toplam_mwh, 3)} MWh, mutlak {sayiTr(kiyas.ozet.fark_mutlak_mwh, 3)} MWh; en büyük fark {String(kiyas.ozet.en_buyuk_fark_saat).padStart(2, "0")}:00 saatinde {sayiTr(kiyas.ozet.en_buyuk_fark_mwh, 3)} MWh.</>}
                    {kiyas.oneri && ` Kıyaslanan: öneri sürüm ${kiyas.oneri.surum}`}{kiyas.bildirilen && `, bildirilen sürüm ${kiyas.bildirilen.surum}.`}
                  </p>
                  {!kiyas.ozet.ayni && (
                    <div className="grafik-kaydir">
                      <table className="veri sayisal" style={{ fontSize: 13 }}>
                        <thead><tr><th>Saat</th><th>Öneri (MWh)</th><th>Bildirilen (MWh)</th><th>Fark (MWh)</th></tr></thead>
                        <tbody>{kiyas.saatler.filter((h) => Math.abs(h.fark_mwh) > 0.0005).map((h) => (
                          <tr key={h.saat}><td>{String(h.saat).padStart(2, "0")}:00</td><td>{sayiTr(h.oneri_mwh, 3)}</td><td>{sayiTr(h.bildirilen_mwh, 3)}</td><td>{sayiTr(h.fark_mwh, 3)}</td></tr>))}</tbody>
                      </table>
                    </div>
                  )}
                </>
              )}
              {kiyas && !kiyas.ozet && <p className="soluk" style={{ fontSize: 13.5, margin: "8px 0 0" }}>{kiyas.bildirilen ? "Bu gün için indirilmiş öneri yok; kıyas yapılamadı." : "Bu gün için bildirilen dosya henüz yüklenmedi."}</p>}
            </details>
            <details className="aciklama genis">
              <summary>Bildirim dosyası biçimi{kgup.sablon?.kaynak ? " · müşteri dosyasından" : " · varsayılan"}</summary>
              <p className="soluk" style={{ fontSize: 13.5, margin: "0 0 8px" }}>
                {kgup.sablon ? <>Şu anki biçim: {kgup.sablon.kolonlar.join(" · ")}; ayraç «{kgup.sablon.ayrac}», ondalık «{kgup.sablon.ondalik}». {kgup.sablon.durum.charAt(0).toLocaleUpperCase("tr-TR") + kgup.sablon.durum.slice(1)}.</> : "Biçim bilgisi yok."}
                {" "}Bir KGÜP dosyası seçin (CSV ya da Excel); kolon adları, sırası, ayraç ve ondalık o dosyadan öğrenilir ve sonraki KGÜP indirmeleri aynı biçimde çıkar. EAK dosyası her zaman TPYS EAK.csv biçimindedir.
              </p>
              <div className="dugme-sira" style={{ alignItems: "flex-end", flexWrap: "wrap", gap: 8 }}>
                <label className="girdi-etiket">Örnek dosya
                  <input className="girdi" type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(e) => { const f = e.target.files?.[0]; if (f) sablonOgren(f); e.target.value = ""; }} /></label>
                {kgup.sablon?.kaynak && <button className="dugme" onClick={sablonSifirla}>Varsayılana dön</button>}
              </div>
              {sablonMesaj && <p style={{ fontSize: 13.5, margin: "8px 0 0", color: sablonMesaj.startsWith("Öğrenildi") || sablonMesaj.startsWith("Varsayılan") ? undefined : "var(--uyari-metin)" }}>{sablonMesaj}</p>}
            </details>
            <details className="aciklama">
              <summary>Piyasa takvimi ve program kuralı</summary>
              <p>
                {kgup.gip && `${kgup.gip.kural} Örnek: ${kgup.gip.ornek_teslimat} teslimatı için kapı ${kgup.gip.ornek_kapi}, revizyon son ${kgup.gip.ornek_revizyon_son}. `}
                Program, teslim saatinden (bir gün önce 15:30) önce verilmiş son tahminin saatlik beklenen (P50) değeridir; program ≤ verilebilecek en yüksek güç (EAK) ≤ kurulu güç
                kuralı uygulanır. KGÜP dosyası TPYS şablonuyla (KGUP.csv) birebirdir, «Bildirim dosyası biçimi» alanından kendi dosyanızla değiştirilebilir; EAK ayrı dosyadır (TPYS EAK.csv, bildirim 09:00–15:30). Dosya bir öneridir, bildirim TPYS'de yapılır.
              </p>
            </details>
          </>
        ) : (
          <div className="bos-durum">
            <div className="bos-bas">Yarın için program henüz yok</div>
            <p>Teslim saatinden önce verilmiş tahmin yok; sabah tahmini üretildiğinde burada görünür.</p>
          </div>
        )}
      </Kart>
      {(!seri || !ozet) && (
        <Kart baslik="Saatlik tahmin ve P10–P90 aralığı">
          <div className="bos-durum">
            <div className="bos-bas">Tahmin gösterilemiyor</div>
            <p>Bu santral için kayıtlı tahmin bulunamadı ya da sunucudan alınamadı; sayfayı yenileyin.</p>
          </div>
        </Kart>
      )}
      {seri && ozet && dilim && grafikSantral && (
        <div
          className="ızgara"
          style={{
            gridTemplateColumns: "minmax(0,1.9fr) minmax(0,1fr)",
            alignItems: "start",
          }}
        >
          <Kart
            baslik={
              GUNLUK_MOD[ufuk]
                ? "Günlük tepe ve P10–P90 aralığı"
                : "Saatlik tahmin ve P10–P90 aralığı"
            }
          >
            <ProductionForecastChart
              forecast={grafikTahmin}
              actual={grafikGercek}
              nowMs={t0}
              nowValue={nowVal}
              gunes={seri.gunes}
              mode={GUNLUK_MOD[ufuk] ? "daily" : "hourly"}
              plant={grafikSantral}
              features={GRAFIK_OZELLIKLERI}
              height={360}
            />
            {/* 23.10 altıncı tur: tahmin kimliği (mod · aralık kaynağı) görünür tek satır; uzun «Ne gösterir»
                açıklaması açılır alanda (details) — metin aynen, bilgi kaybı yok */}
            <p className="soluk" style={{ fontSize: 13.5, margin: "12px 0 0" }}>
              Son tahmin Mod {seri.mod ?? "—"}.{bantYazisi ? ` Aralık: ${bantYazisi}.` : ""}
            </p>
            <details className="aciklama">
              <summary>Ne gösterir</summary>
              <p>
                En son tahminin saatlik üretimi. Mavi çizgi beklenen üretim (P50), mavi aralık
                P10–P90 (saatlerin %80'inin içinde kalması beklenen koridor); soluk mavi bölüm geçmişte kalan
                saatlerin tahminidir; amber çizgi varsa gerçekleşen üretimdir. Tahminler güncellenmez; her yeni tahmin
                ayrıca kaydedilir.
              </p>
            </details>
          </Kart>
          <Kart baslik="Günlük toplamlar">
            {/* 23.10 altıncı tur: grafikle aynı dil — gövde ailesi + tabular (.veri.sayisal), mono kalktı */}
            <div className="grafik-kaydir">
            <table className="veri sayisal">
              <thead>
                <tr>
                  <th>Tarih</th>
                  <th>Beklenen (P50) kWh</th>
                  {bantVar && <th>P10–P90 kWh</th>}
                </tr>
              </thead>
              <tbody>
                {gunlukVeri.map((g) => (
                  <tr key={g.etiket}>
                    <td>{g.etiket}{g.kismi ? " *" : ""}</td>
                    <td>{sayiTr(g.p50Kwh)}</td>
                    {bantVar && (
                      <td style={{ color: "var(--ikincil)" }}>
                        {g.p10Kwh !== null && g.p90Kwh !== null
                          ? `${sayiTr(g.p10Kwh)} – ${sayiTr(g.p90Kwh)}`
                          : "—"}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            {gunlukVeri.some((g) => g.kismi) && (
              <p className="soluk" style={{ fontSize: 13.5, margin: "10px 0 0" }}>
                * dönemin yalnız bir bölümü kapsanan gün
              </p>
            )}
          </Kart>
        </div>
      )}
      {/* v2.507 (F-10): bugünün programı ↔ güncel beklenti — eşik üstü ve revize edilebilir saatler; yol gösterici, kayıt yazmaz */}
      <Kart baslik="Bugünün programı — revizyon önerisi"
        sag={<span className="cip">{rv === undefined ? "hesaplanıyor" : rv?.durum === "ok" ? <Meta items={[rv.oneri_saatleri.length ? `${sayiTr(rv.oneri_saatleri.length)} saat öneri` : "öneri yok", `eşik %${sayiTr(rv.esik_oran * 100, 0)}`, rv.program_kaynagi ?? ""]} /> : rv?.durum === "gun_bitti" ? "gün bitti" : rv?.durum === "program_yok" ? "bugün için program yok" : "tahmin yok"}</span>}>
        {rv === undefined ? <YerTutucu yukseklik={160} />
         : !rv || rv.durum !== "ok" ? (
          <div className="bos-durum">
            <div className="bos-bas">{rv?.durum === "gun_bitti" ? "Bugünün revizyon pencereleri kapandı." : rv?.durum === "program_yok" ? "Bugün için bildirilmiş ya da indirilmiş program bulunamadı." : "Güncel tahmin olmadığından kıyas yapılamadı."}</div>
            <p>Program kaynağı sırasıyla: panele yüklenen bildirilen dosya, indirilen son öneri, 15:30 kesimi öncesi tahmin. Her saatin revizyon son anı GİP kapı kapanışı + 30 dakikadır.</p>
          </div>
        ) : (
          <>
            {rv.oneri_saatleri.length > 0
              ? <p style={{ fontSize: 14, margin: "0 0 8px" }}><b>Öneri:</b> saat {rv.oneri_saatleri.map((h) => `${String(h).padStart(2, "0")}:00`).join(", ")} için program güncel beklentiden eşik üstü sapıyor; bu saatlerde fark {sayiTr(rv.saatler.filter((u) => u.oneri).reduce((a, u) => a + (u.fark_mwh ?? 0), 0), 1)} MWh.{rv.ilk_revizyon_son && <> İlk saat için revizyon son anı <b>{new Date(rv.ilk_revizyon_son).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}</b>.</>}</p>
              : <p className="soluk" style={{ fontSize: 14, margin: "0 0 8px" }}>Kalan saatlerde program ile güncel beklenti arasındaki fark eşiğin altında; revizyon gerekmiyor.</p>}
            <div className="grafik-kaydir">
              <table className="veri" style={{ fontSize: 13.5 }}>
                <thead><tr><th>Saat</th><th>Program (MWh)</th><th>Güncel beklenti (MWh)</th><th>Fark (MWh)</th><th>Eşik (MWh)</th><th>Revizyon son anı</th><th></th></tr></thead>
                <tbody className="mono">
                  {rv.saatler.map((u) => (
                    <tr key={u.saat}><td>{String(u.saat).padStart(2, "0")}:00</td><td>{sayiTr(u.program_mwh, 3)}</td><td>{u.beklenen_mwh != null ? sayiTr(u.beklenen_mwh, 3) : "—"}</td>
                      <td>{u.fark_mwh != null ? sayiTr(u.fark_mwh, 3) : "—"}</td><td>{sayiTr(u.esik_mwh, 3)}</td>
                      <td>{new Date(u.revizyon_son).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}{!u.revize_mumkun && <span className="soluk"> (geçti)</span>}</td>
                      <td>{u.oneri ? <span className="rozet rozet-uyari rozet-kucuk">revize et</span> : u.revize_mumkun && (u.program_mwh > 0 || (u.beklenen_mwh ?? 0) > 0) ? <span className="rozet rozet-ok rozet-kucuk">uygun</span> : ""}</td></tr>))}
                </tbody>
              </table>
            </div>
            <p className="soluk" style={{ fontSize: 13.5, margin: "8px 0 0" }}>Program: {rv.program_kaynagi}. Güncel beklenti: {rv.beklenen_kaynagi}. {rv.not}</p>
          </>
        )}
      </Kart>
      {/* v2.266 (Dalga 5.18): kısa ufuk — ölçüm persistansı; uydu değil. Canlı SCADA yoksa dürüstçe tire. */}
      <Kart baslik="Önümüzdeki 6 saat — son ölçümlere göre düzeltme"
        sag={<span className="cip">{nc === undefined ? "hesaplanıyor" : nc?.durum === "ok" ? <Meta items={[`düzeltme oranı ${sayiTr(nc.oran ?? 0, 2)}`, `son ${sayiTr(nc.n_saat)} saat`]} /> : nc?.durum === "gece" ? "gece: beklenen (P50)" : "canlı ölçüm gerektirir"}</span>}>
        {nc === undefined ? <YerTutucu yukseklik={322} />
         : !nc || nc.durum === "scada_bayat" || nc.durum === "olcum_yok" || nc.durum === "tahmin_yok" ? (
          /* 23.10 altıncı tur: boş durum iki kademe — API'nin nedeni başlık, ne yaptığı açıklama */
          <div className="bos-durum">
            <div className="bos-bas">
              {nc?.not ?? "Hesaplanamadı"}{nc?.tazelik_saat != null && <span className="soluk" style={{ fontWeight: 400 }}> (son ölçüm {nc.tazelik_saat >= 48 ? `${sayiTr(nc.tazelik_saat / 24, 0)} gün` : `${sayiTr(nc.tazelik_saat, 0)} saat`} önce)</span>}
            </div>
            <p>Bu düzeltme, son 3 saatte ölçülen üretimin tahmine oranını ileriye taşır; yalnız canlı SCADA bağlantısı olan santrallerde çalışır.</p>
          </div>
        ) : (
          <>
            <div className="grafik-kaydir">
              <table className="veri" style={{ fontSize: 13.5 }}>
                <thead><tr><th>Saat</th><th>Beklenen (P50)</th><th>Düzeltilmiş</th><th>Düzeltme ağırlığı</th></tr></thead>
                <tbody className="mono">
                  {nc.ufuk.map((u) => (
                    <tr key={u.ts}><td>{new Date(u.ts).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}</td>
                      <td>{sayiTr(u.p50_kw)} kW</td><td>{sayiTr(u.nowcast_kw)} kW</td><td>%{sayiTr(u.agirlik * 100, 0)}</td></tr>))}
                </tbody>
              </table>
            </div>
            <p className="soluk" style={{ fontSize: 14, margin: "10px 0 0" }}>
              Son {sayiTr(nc.n_saat)} saatin ölçüm/tahmin oranı ({sayiTr(nc.oran ?? 0, 2)}) ileriye doğru azalan ağırlıkla beklenen değere (P50)
              karıştırılır; 6 saat sonrası beklenen değerdir. Gün içi program güncellemesi için yol göstericidir; kayıt yazmaz.
            </p>
          </>
        )}
      </Kart>
    </Sayfa>
  );
}
