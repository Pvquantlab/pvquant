import { useEffect, useState } from "react";
import { api, rolum, bellektenOku } from "../../api/client";
import type { PaylasimListesi, PaylasilanVeri, TakimUyesi, Portfoy as PortfoyT, PortfoyDsg, PortfoyTahmin, ApiAnahtar, Webhook } from "../../api/types";
import { Kart, Kpi, Sayfa, sayiTr, gucTr, enerjiTr, SayfaIskeleti, YerTutucu } from "./parcalar";
import { Meta } from "../../lib/Meta";

/** 23.10 sekizinci tur — «76,3 MWh» gibi birimli dizgiyi sayı + soluk birim olarak basar; dizgi aynen (enerjiTr). */
function DegerBirim({ metin }: { metin: string }) {
  const i = metin.lastIndexOf(" ");
  if (i < 0) return <>{metin}</>;
  return <>{metin.slice(0, i)} <span className="birim">{metin.slice(i + 1)}</span></>;
}
/** 23.10 sekizinci tur — kapsam tanımlayıcısının kullanıcı dili (değer ve yetki anlamı aynı; bilinmeyen kapsam kodla kalır). */
const KAPSAM_AD: Record<string, string> = { "tahmin:oku": "Tahmin okuma", "kgup:oku": "KGÜP programı okuma" };
/** API ucu çipi — tıklanınca yolu panoya kopyalar (yalnız istemci); geri bildirim çipin içinde ve aria-live ile. */
function UcKopyala({ yol }: { yol: string }) {
  const [durum, setDurum] = useState<"" | "kopyalandı" | "kopyalanamadı">("");
  const bildir = (d: "kopyalandı" | "kopyalanamadı") => { setDurum(d); setTimeout(() => setDurum(""), 1600); };
  // pano API'si reddederse (izin/iframe) eski yol: geçici textarea + execCommand; ikisi de olmazsa dürüst geri bildirim
  const kopyala = async () => {
    try { await navigator.clipboard.writeText(yol); bildir("kopyalandı"); return; } catch { /* aşağıya düş */ }
    try {
      const ta = document.createElement("textarea"); ta.value = yol; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select(); const ok = document.execCommand("copy"); ta.remove(); bildir(ok ? "kopyalandı" : "kopyalanamadı");
    } catch { bildir("kopyalanamadı"); }
  };
  return (
    <button type="button" className={`cip cip-kod uc-kopyala${durum === "kopyalandı" ? " kopyalandi" : ""}`} title="Yolu kopyala" onClick={kopyala}>
      <span>{yol}</span>
      <svg aria-hidden="true" width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4.5" y="4.5" width="7.5" height="7.5" rx="1.5" /><path d="M9.5 4.5V3a1.5 1.5 0 0 0-1.5-1.5H3A1.5 1.5 0 0 0 1.5 3v5A1.5 1.5 0 0 0 3 9.5h1.5" />
      </svg>
      <span className="uc-geri" aria-live="polite">{durum}</span>
    </button>
  );
}
/** «22.10.2026 23:00» → tarih ve saat ayrı parçalar; dar sütunda yalnız ikisinin arasında kırılır. */
function TarihSaat({ metin }: { metin: string }) {
  const i = metin.lastIndexOf(" ");
  if (i < 0) return <>{metin}</>;
  return <><span className="parca">{metin.slice(0, i)}</span> <span className="parca">{metin.slice(i + 1)}</span></>;
}

/** v2.263 (Dalga 5.15) — Portföy: kiracının tüm santralleri tek tabloda; toplamlar dürüst
 *  (bir santralin beklentisi yoksa toplam da yok). Satıra tıklayınca o santrala geçilir. */
export function Portfoy({ onSec, santralYenile }: { onSec: (id: string) => void;
  /** v2.303: arşivleme/geri alma sonrası üst listeyi tazele */ santralYenile?: () => void }) {
  // 24.10 Portföy geçiş turu — üç istek BAĞIMSIZ ve BAYAT-ÖNCE. Canlıda (Deneme Lab, konteyner içi sıcak) ölçüldü:
  // /v1/portfoy ≈ 0,25–0,27 s, /portfoy/tahmin ≈ 0,4 s (sonra 500), /portfoy/dsg ≈ 0,85–1,1 s. v2.324'ün «tek kapı»sı
  // KPI'ları ve santral tablosunu en yavaş olan DSG'ye bekletiyordu; 60 sn bellek dolunca her dönüş iskeletten başlıyordu.
  // Şimdi: (1) bellekte son yanıt varsa sayfa onunla ANINDA çizilir, başlık çipi «güncelleniyor» der, taze yanıt gelince
  // değerler yenilenir (SWR; tarih/tazelik alanları verinin kendisinden gelir, uydurulmaz); (2) KPI + tablo /portfoy
  // gelir gelmez, tahmin ve DSG kartları kendi yanıtlarıyla dolar — yerleri boyutlu tutulur (kayma yok); (3) üç istek
  // useState başlatıcısında yola çıkar: çocuk bölümlerin (dış erişim, paylaşım, ekip, arşiv) effect'leri ebeveynden önce
  // koştuğundan eskiden 8 ikincil istek çekirdek üçünün ÖNÜNE geçiyordu; (4) sunucu hatası «veri yok»tan ayrı söylenir.
  // API sözleşmesi, hesaplar ve yetkiler değişmedi. undefined = henüz bilinmiyor, null = yok.
  type Durum = "bekliyor" | "tamam" | "hata";
  const [p, setP] = useState<PortfoyT | null | undefined>(() => bellektenOku<PortfoyT>("/v1/portfoy"));
  const [dsg, setDsg] = useState<PortfoyDsg | null | undefined>(() => bellektenOku<PortfoyDsg>("/v1/portfoy/dsg?gun=30"));   // v2.276
  const [pt, setPt] = useState<PortfoyTahmin | null | undefined>(() => bellektenOku<PortfoyTahmin>("/v1/portfoy/tahmin?gun=7"));   // v2.280
  const [pD, setPD] = useState<Durum>("bekliyor");
  const [ptD, setPtD] = useState<Durum>("bekliyor");
  const [dsgD, setDsgD] = useState<Durum>("bekliyor");
  const [istekler] = useState(() => ({ p: hatirlayarak("/v1/portfoy", api.portfoy), pt: hatirlayarak("/v1/portfoy/tahmin?gun=7", api.portfoyTahmin), dsg: hatirlayarak("/v1/portfoy/dsg?gun=30", api.portfoyDsg) }));
  useEffect(() => {
    let acik = true;
    // hata: bayat değer varsa yerinde kalır (çip «güncellenemedi» der), yoksa null + «sunucu hatası» metni
    istekler.p.then((v) => { if (acik) { setP(v); setPD("tamam"); } }, () => { if (acik) { setP((e) => e ?? null); setPD("hata"); } });
    istekler.pt.then((v) => { if (acik) { setPt(v); setPtD("tamam"); } }, () => { if (acik) { setPt((e) => e ?? null); setPtD("hata"); } });
    istekler.dsg.then((v) => { if (acik) { setDsg(v); setDsgD("tamam"); } }, () => { if (acik) { setDsg((e) => e ?? null); setDsgD("hata"); } });
    return () => { acik = false; };
  }, [istekler]);
  const hazir = p !== undefined || pD !== "bekliyor";
  const tazeleniyor = hazir && (pD === "bekliyor" || ptD === "bekliyor" || dsgD === "bekliyor");
  const t = p?.toplam ?? null;
  // v2.362: santraller listesi de ölçekle konuşur (bulgu 14 — 0,0 MWh kalıntısı)
  const kwhYaz = (v: number | null | undefined) => v == null ? "—" : enerjiTr(v);
  // v2.360: KPI'da birim değerin yanında ölçekle gelir (küçükte kWh, büyükte MWh)
  const enj = (v: number | null | undefined) => v == null ? "—" : enerjiTr(v);
  const tarih = (s: string | null) => s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  if (!hazir) return (
    <Sayfa baslik="Portföy" alt="Tüm santraller bir bakışta; sayılar kurulu güçle ağırlıklıdır, hesaplanamayan değerler — ile gösterilir.">
      <SayfaIskeleti kpi={4} kart={2} />
    </Sayfa>
  );
  return (
    <Sayfa baslik="Portföy" alt="Tüm santraller bir bakışta; sayılar kurulu güçle ağırlıklıdır, hesaplanamayan değerler — ile gösterilir."
      sag={<span className="cip">{p ? <Meta items={[`${sayiTr(p.santraller.length)} santral`, new Date(p.gun + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short" }), tazeleniyor && "güncelleniyor", pD === "hata" && "güncellenemedi"]} /> : "—"}</span>}>
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
      {/* 23.10 sekizinci tur — kurumsal veri tablosu: veri sütunları içerik genişliğinde (width:1%) ve 28 px oluklu, ad
          sütunu kalan alanı alır; birimler soluk küçük (.birim); ölçüm tarihi üstte, «N gün eski» rozeti altta (eşik aynı:
          kesinti_gun > 2); alarm sayısı >0 rozet; «satıra tıkla» çipi kalktı — tıklanabilirlik hover/odak zemini,
          imleç ve satır sonundaki ok ile; ilk sütun dar ekranda yapışkan; dipnot üç tanım satırı. onClick/onKeyDown ve
          onSec aynen; veri/eşik/biçim değişmedi. */}
      <Kart baslik="Santraller" alt={p && p.santraller.length > 0 ? `${sayiTr(p.santraller.length)} santral, satır santral sayfasını açar` : undefined}>
        {!p && pD === "hata" ? <p className="soluk" style={{ margin: 0 }}>Portföy özeti şu anda alınamadı (sunucu hatası); sayfayı yenileyin.</p>
         : !p || p.santraller.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu hesapta santral yok.</p>
         : (
          <div className="grafik-kaydir santral-tablo">
            <table className="veri sayisal santral">
              <thead><tr>
                <th>Santral</th><th>Kurulu güç <span className="birim">kWp</span></th><th>Segment</th><th className="tarih-saat">Son ölçüm</th>
                <th>Hata 30 g <span className="birim">WMAPE</span></th><th>Bugün</th><th>Yarın</th><th>Alarm</th><th className="tarih-saat">Son tahmin</th><th aria-hidden="true" />
              </tr></thead>
              <tbody>
                {p.santraller.map((r) => {
                  const eski = r.kesinti_gun != null && r.kesinti_gun > 2;
                  return (
                  <tr key={r.id} className="satir-tikla" onClick={() => onSec(r.id)} tabIndex={0}
                      aria-label={`${r.ad}, santral sayfasını aç`}
                      onKeyDown={(e) => { if (e.key === "Enter") onSec(r.id); }}>
                    <td className="ad">{r.ad}</td>
                    <td>{sayiTr(r.kapasite_kwp)}</td>
                    <td>{r.segment ?? <span className="bos" title="Piyasa segmenti seçilmedi">—</span>}</td>
                    <td>
                      <div className="tarih-saat"><TarihSaat metin={tarih(r.son_olcum)} /></div>
                      {eski && <div className="hucre-alt"><span className="rozet rozet-uyari rozet-kucuk" title="Son ölçüm 2 günden eski">{sayiTr(r.kesinti_gun!)} gün eski</span></div>}
                    </td>
                    <td>{r.wmape_30g != null ? `%${sayiTr(r.wmape_30g, 1)}` : <span className="bos" title="Son 30 günde karşılaştırılmış gün yok">—</span>}</td>
                    <td><DegerBirim metin={kwhYaz(r.bugun_kwh)} /></td>
                    <td><DegerBirim metin={kwhYaz(r.yarin_kwh)} /></td>
                    <td>{r.acik_alarm > 0
                      ? <span className="rozet rozet-uyari rozet-kucuk" title="Son 7 günde okunmamış kayıt">{sayiTr(r.acik_alarm)}</span>
                      : <span className="bos">0</span>}</td>
                    <td className="tarih-saat"><TarihSaat metin={tarih(r.son_kosu)} /></td>
                    <td className="satir-ok" aria-hidden="true">
                      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="m5 3 4 4-4 4" /></svg>
                    </td>
                  </tr>);
                })}
              </tbody>
            </table>
          </div>
        )}
        <ul className="tanim-listesi">
          <li><b>Bugün, yarın</b>son tahminin yerel gün toplamı (beklenen, P50); 20 saatten az kapsanan gün gösterilmez.</li>
          <li><b>Hata 30 g</b>son 30 günün 0–24 saat tahmin hatası (WMAPE).</li>
          <li><b>Alarm</b>son 7 günde okunmamış kayıt.</li>
        </ul>
      </Kart>
      {/* v2.280 (Tablo 3.2 satır 11): hiyerarşik uzlaştırılmış portföy tahmini — toplam santral tahminleriyle tutarlı */}
      <Kart baslik="Portföyün günlük üretim tahmini" sag={<span className="cip">{pt?.durum === "ok" ? <Meta items={[pt.yontem, pt.tutarli === false && "tutarsız", ptD === "bekliyor" && "güncelleniyor", ptD === "hata" && "güncellenemedi"]} /> : "—"}</span>}>
        {/* 23.10 yedinci tur: cümle başı tire kalktı — tire yalnız değer yerinde (tablo/KPI hücresi) */}
        {/* 24.10: bekliyor → boyutlu yer tutucu; sunucu hatası → açıkça söylenir (eskiden «Henüz tahmin yok» ile karışıyordu) */}
        {pt === undefined && ptD === "bekliyor" ? <YerTutucu yukseklik={168} />
         : ptD === "hata" && (!pt || pt.durum !== "ok") ? <p className="soluk" style={{ margin: 0 }}>Portföy tahmini şu anda alınamadı (sunucu hatası); santral tahminleri Tahminler sayfasında.</p>
         : !pt || pt.durum !== "ok" ? <p className="soluk" style={{ margin: 0 }}>Henüz tahmin yok.</p> : (
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
      <Kart baslik="Dengeden sorumlu grup (DSG) netleştirmesi — portföy dengesizliği" sag={<span className="cip">{dsg ? <Meta items={[`${sayiTr(dsg.pencere_gun)} gün`, dsg.fiyat.senaryo_saat > 0 ? "senaryo fiyatı" : "piyasa fiyatı (EPİAŞ)", dsgD === "bekliyor" && "güncelleniyor", dsgD === "hata" && "güncellenemedi"]} /> : "—"}</span>}>
        {dsg === undefined && dsgD === "bekliyor" ? <YerTutucu yukseklik={124} />
         : !dsg && dsgD === "hata" ? <p className="soluk" style={{ margin: 0 }}>DSG hesabı şu anda alınamadı (sunucu hatası).</p>
         : !dsg ? <p className="soluk" style={{ margin: 0 }}>Veri yok.</p> : dsg.ayri_tl == null ? (
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
      {rolum() === "admin" && <DisErisim santraller={p?.santraller.map((s) => ({ id: s.id, ad: s.ad })) ?? []} />}
      {rolum() === "admin" && <SantralArsivi santralYenile={santralYenile} />}
      <Paylasimlar santraller={p?.santraller.map((s) => ({ id: s.id, ad: s.ad })) ?? []} />
      <HesapVeEkip />
    </Sayfa>
  );
}

/** 24.10 — başarısız GET'in KISA hafızası (15 sn, yalnız Portföy'ün üç çekirdek isteği): getir 500'ü belleğe almaz, bu
 *  yüzden canlıda 500 dönen /portfoy/tahmin her Portföy açılışında (hızlı ardışık geçişlerde de) yeniden gidiyordu.
 *  Yakın zamanda başarısız olduysa kart hemen «sunucu hatası» der; 15 sn sonra yeniden denenir. Başarı kaydı siler. */
const sonHata = new Map<string, number>();
function hatirlayarak<T>(yol: string, fn: () => Promise<T>): Promise<T> {
  const t = sonHata.get(yol);
  const soz = t !== undefined && Date.now() - t < 15_000
    ? Promise.reject(new Error(`yakın zamanda başarısız: ${yol}`))
    : fn().then((v) => { sonHata.delete(yol); return v; }, (e: unknown) => { sonHata.set(yol, Date.now()); throw e; });
  // işleyiciler effect'te (bir mikro görev sonra) bağlanır; atılan render'da hiç bağlanmaz → «işlenmemiş ret» olmasın
  soz.catch(() => {});
  return soz;
}

/* 24.10 Faz 2: GelenTalepler (vitrin başvuruları) PLATFORM yüzüne taşındı (/yonetim → Başvurular); müşteri panelinde yeri yok. */

/** v2.264 (Dalga 5.16) — Dış erişim: API anahtarları + webhook alıcıları. Yalnız admin görür.
 *  Anahtar ve webhook sırrı YALNIZ üretildiği anda gösterilir; sunucu sırrı geri veremez. */
function DisErisim({ santraller }: { santraller: { id: string; ad: string }[] }) {
  // 24.10: dönüşte bellekteki son listeyle başlar — «Henüz anahtar yok» yanıp sönmesi biter; yenile() tazeler
  const [anahtarlar, setAnahtarlar] = useState<ApiAnahtar[]>(() => bellektenOku<{ anahtarlar: ApiAnahtar[] }>("/v1/api-anahtarlari")?.anahtarlar ?? []);
  const [kapsamlar, setKapsamlar] = useState<string[]>(() => bellektenOku<{ kapsamlar: string[] }>("/v1/api-anahtarlari")?.kapsamlar ?? []);
  const [webhooklar, setWebhooklar] = useState<Webhook[]>(() => bellektenOku<{ webhooklar: Webhook[] }>("/v1/webhooklar")?.webhooklar ?? []);
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
      {/* 23.10 sekizinci tur: iki sütun 28 px oluk; formlar açık ızgara şablonlu (.form-anahtar / .form-webhook): etiketler
          aynı hizada, düğme son sütunda; ≤700 px tek sütun. Kapsam onayları insan diliyle etiket + küçük kod (değer aynı). */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(340px, 100%), 1fr))", gap: "20px 28px" }}>
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
          <form className="form-izgara form-anahtar"
                onSubmit={(e) => { e.preventDefault(); dene(async () => { const r = await api.apiAnahtarUret(ad, secili, null); setYeniAnahtar(r.anahtar); setAd(""); }); }}>
            <label className="girdi-etiket">Anahtar adı
              <input className="girdi" value={ad} onChange={(e) => setAd(e.target.value)} placeholder="ör. ticaret masası" /></label>
            <div className="girdi-etiket">Kapsam
              <div className="onay-grubu">
                {kapsamlar.map((k) => (
                  <label key={k} className="ayar-onay onay-kapsam">
                    <input type="checkbox" checked={secili.includes(k)} onChange={(e) => setSecili(e.target.checked ? [...secili, k] : secili.filter((x) => x !== k))} />
                    <span className="onay-metin"><span className="onay-ad">{KAPSAM_AD[k] ?? k}</span><span className="kod">{k}</span></span>
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
          <form className="form-izgara form-webhook"
                onSubmit={(e) => { e.preventDefault(); dene(async () => { const r = await api.webhookEkle(url, whSantral || null); setYeniSir(r.secret); setUrl(""); }); }}>
            <label className="girdi-etiket">Alıcı adresi
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
        <div className="uc-sira">
          <UcKopyala yol="/v1/dis/santraller" />
          <UcKopyala yol="/v1/dis/santral/{id}/tahmin" />
          <UcKopyala yol="/v1/dis/santral/{id}/kgup" />
        </div>
        <ul className="tanim-listesi">
          <li><b>Önbellek</b>tahmin ucu ETag ile 304 döner.</li>
          <li><b>Oran sınırı</b>dakikada 120 istek.</li>
          <li><b>Belge</b><span className="kod">docs/api/dis-api.md</span></li>
        </ul>
      </div>
    </Kart>
  );
}


/** v2.289: kuruluşlar arası paylaşım — verdiklerimiz (kurmak yalnız yönetici) + aldıklarımız (herkes görür). */
function Paylasimlar({ santraller }: { santraller: { id: string; ad: string }[] }) {
  const [liste, setListe] = useState<PaylasimListesi | null>(() => bellektenOku<PaylasimListesi>("/v1/paylasimlar") ?? null);   // 24.10: bayat-önce
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
  const [durum, setDurum] = useState<{ aktif: boolean; kalan_kurtarma: number } | null>(() => bellektenOku<{ aktif: boolean; kalan_kurtarma: number }>("/v1/iki-adim") ?? null);   // 24.10: bayat-önce
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
  const [uyeler, setUyeler] = useState<TakimUyesi[]>(() => bellektenOku<{ uyeler: TakimUyesi[] }>("/v1/takim")?.uyeler ?? []);   // 24.10: bayat-önce
  const [roller, setRoller] = useState<string[]>(() => bellektenOku<{ roller: string[] }>("/v1/takim")?.roller ?? []);
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
  const [arsiv, setArsiv] = useState<{ id: string; name: string; capacity_kwp: number }[]>(() => bellektenOku<{ santraller: { id: string; name: string; capacity_kwp: number }[] }>("/v1/plants-arsiv")?.santraller ?? []);   // 24.10: bayat-önce
  const [etkin, setEtkin] = useState<{ id: string; name: string }[]>(() => (bellektenOku<{ id: string; name: string }[]>("/v1/plants") ?? []).map((x) => ({ id: x.id, name: x.name })));
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
      {/* «Arşivle…» üç noktası kırpma değil onay adımı imasıydı; düğme «Arşivle», onay satır içinde (mekanizma aynı) +
          «Vazgeç» yalnız yerel onay durumunu kapatır. Liste geniş kartta iki sütun (.islem-listesi.cift). */}
      {etkin.length > 1 && (
        <ul className="islem-listesi cift">
          {etkin.map((x) => (
            <li key={x.id}>
              <span className="islem-ad">{x.name}</span>
              {onayId === x.id ? (
                <span className="islem-onay">
                  <button className="dugme kucuk dugme-tehlike" style={{ fontWeight: 600 }}
                          onClick={() => dene(async () => { await api.santralArsivle(x.id); setOnayId(null); setMesaj(`${x.name} arşive alındı.`); })}>
                    Eminim, arşive al</button>
                  <button className="dugme kucuk" onClick={() => setOnayId(null)}>Vazgeç</button>
                </span>
              ) : (
                <button className="dugme kucuk" onClick={() => setOnayId(x.id)}>Arşivle</button>
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
