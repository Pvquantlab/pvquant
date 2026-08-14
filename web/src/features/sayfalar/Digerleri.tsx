import { useEffect, useMemo, useRef, useState } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "../../lib/EChart";
import { useTema } from "../../lib/useTema";
import { api, EslemeHatasi, type EslemeVerisi,
         type ScadaOnizleme, type ScadaKayit,
         type KosuSatiri } from "../../api/client";
import type { KalibrasyonOzeti } from "../../api/types";
import { Kart, Sayfa, Kpi, sayiTr } from "./parcalar";

export function VeriYukleme({ plantId, santralimeGit, tahminlereGit }:
  { plantId: string; santralimeGit?: () => void;
    tahminlereGit?: () => void }) {
  // v2.88: "Kalibre tahmine gec" canlandi — dosya sec -> /scada/preview ->
  // onizleme (format + esleme + ham satirlar). Onay dugmesi v2.89'a kadar
  // bilerek pasif (olu dugme degil: sirasi acikca yazili).
  const dosyaRef = useRef<HTMLInputElement>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [dosyaAdi, setDosyaAdi] = useState<string | null>(null);
  const [on, setOn] = useState<ScadaOnizleme | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  // v2.89: onay zinciri — dosya elde tutulur (API durumsuz, kayda yeniden gider)
  const [dosya, setDosya] = useState<File | null>(null);
  const [kayitta, setKayitta] = useState(false);
  const [kayitHata, setKayitHata] = useState<string | null>(null);
  const [karne, setKarne] = useState<ScadaKayit | null>(null);
  // v2.91: sihirbaz — otomatik esleme dusunce kullanici karar verir
  const [sihirbaz, setSihirbaz] = useState<EslemeVerisi | null>(null);
  const [secimler, setSecimler] = useState<Record<string, string>>({});
  // v2.93: hizli yol — kosu tetikleme durumu
  const [kosuyor, setKosuyor] = useState(false);
  const [kosuHata, setKosuHata] = useState<string | null>(null);

  const sec = async (d: File) => {
    setYukleniyor(true); setHata(null); setOn(null); setDosyaAdi(d.name);
    setKarne(null); setKayitHata(null); setDosya(d);
    setSihirbaz(null); setSecimler({});
    try { setOn(await api.scadaOnizleme(plantId, d)); }
    catch (e) {
      if (e instanceof EslemeHatasi) setSihirbaz(e.veri);   // v2.91
      else setHata(e instanceof Error ? e.message : String(e));
    }
    finally { setYukleniyor(false); }
  };

  const ALAN_ADI: Record<string, string> = {
    timestamp: "Zaman damgası", power: "Güç", energy: "Enerji",
    poa_irradiance: "POA ışınımı", temp_ambient: "Ortam sıcaklığı",
    temp_module: "Modül sıcaklığı", wind_speed: "Rüzgâr hızı", ghi: "GHI",
  };
  const onayla = async () => {
    if (!dosya || !on) return;
    setKayitta(true); setKayitHata(null);
    try {
      setKarne(await api.scadaYukle(plantId, dosya, on.onerilen_tz));
      setOn(null);   // onizleme gorevini tamamladi — yerini karne alir
    } catch (e) { setKayitHata(e instanceof Error ? e.message : String(e)); }
    finally { setKayitta(false); }
  };

  const sihirbazYukle = async () => {
    if (!dosya) return;
    setKayitta(true); setKayitHata(null);
    try {
      // tz null: santral kaydi sunucuda konusur (onizleme yok ki onersin)
      setKarne(await api.scadaYukle(plantId, dosya, null, secimler));
      setSihirbaz(null);
    } catch (e) { setKayitHata(e instanceof Error ? e.message : String(e)); }
    finally { setKayitta(false); }
  };
  const sihirbazGecerli = !!secimler.timestamp &&
    (!!secimler.power || !!secimler.energy);

  const hizliKos = async () => {
    // v2.93: Streamlit'teki tek satirin SPA hali — kosu biter bitmez
    // Tahminler'e gecilir (sonuc orada, soz degil kanit).
    setKosuyor(true); setKosuHata(null);
    try { await api.tahminKos(plantId); tahminlereGit?.(); }
    catch (e) { setKosuHata(e instanceof Error ? e.message : String(e)); }
    finally { setKosuyor(false); }
  };

  const BAYRAK_ADI: Record<string, string> = {
    valid: "Geçerli", negative_power: "Negatif güç",
    night_production: "Gece üretimi", over_capacity: "Kapasite üstü",
    frozen_value: "Donmuş değer", duplicate_time: "Tekrarlanan zaman",
    dst_ambiguous: "Yaz saati belirsizliği", unparseable: "Okunamayan",
  };

  const eslemeler = on
    ? Object.keys(ALAN_ADI)
        .map((k) => ({ k,
          kolon: (on.mapping as unknown as Record<string, string | null>)[k],
          guven: on.mapping.confidence[k] }))
        .filter((x) => x.kolon)
    : [];

  const yol = (ad: string, bant: string, alt: string, maddeler: string[], onerilen = false) => (
    <Kart baslik={ad} sag={onerilen ? <span className="rozet rozet-ok">Önerilen</span> : undefined}>
      <div className="mono" style={{ fontSize: 30, letterSpacing: "-0.03em",
        color: onerilen ? "var(--marka)" : "var(--metin)" }}>{bant}</div>
      <div style={{ fontSize: 12.5, color: "var(--soluk)", marginBottom: 16 }}>{alt}</div>
      <ul style={{ fontSize: 13, color: "var(--ikincil)", paddingLeft: 17,
                   margin: 0, lineHeight: 2 }}>
        {maddeler.map((m) => <li key={m}>{m}</li>)}
      </ul>
      {onerilen ? (
        <button className="dugme dugme-ana" disabled={yukleniyor}
          onClick={() => dosyaRef.current?.click()}
          style={{ width: "100%", marginTop: 18 }}>
          {yukleniyor ? "Dosya okunuyor…" : "Kalibre tahmine geç"}
        </button>
      ) : (
        /* v2.93: hizli yol canlandi — uret_ve_kaydet HTTP'den. */
        <button className="dugme" disabled={kosuyor || yukleniyor}
          onClick={hizliKos}
          style={{ width: "100%", marginTop: 18 }}>
          {kosuyor ? "Tahmin üretiliyor… 10-20 sn" : "Hızlı tahminle devam et"}
        </button>
      )}
    </Kart>
  );

  const sr = (a: string, b: string) =>
    <tr key={a}><td>{a}</td><td className="mono">{b}</td></tr>;

  return (
    <Sayfa baslik="Veri yükleme"
      alt="Tahmin yolunuzu seçin — SCADA veriniz varsa kalibre tahmine geçin.">
      <input ref={dosyaRef} type="file" hidden
        accept=".csv,.tsv,.txt,.xlsx,.xls"
        onChange={(e) => { const d = e.target.files?.[0];
                           if (d) sec(d); e.target.value = ""; }} />
      <div className="ızgara" style={{ gridTemplateColumns: "repeat(2, minmax(0,1fr))",
                                       maxWidth: 900 }}>
        {yol("Hızlı tahmin", "%5–10", "beklenen yıllık enerji sapması",
          ["Veri yüklemeden, saniyeler içinde sonuç",
           "Profesyonel meteoroloji verisiyle",
           "Kalibreli santralda aktif modla koşar — yoksa fizik"])}
        {yol("Kalibre tahmin", "%1–3", "beklenen yıllık enerji sapması",
          ["Model geçmiş üretiminize uyarlanır",
           "Panel yönü bilinmiyorsa varsayılan kullanılır",
           "En az 3 ay SCADA — önerilen 12 ay"], true)}
      </div>

      {kosuHata && (
        <p style={{ fontSize: 13, color: "var(--ikincil)", maxWidth: 900,
                    margin: "14px 0 0", lineHeight: 1.65 }}>{kosuHata}</p>
      )}

      {hata && (
        <div style={{ maxWidth: 900, marginTop: 14 }}>
          <Kart baslik="Dosya okunamadı">
            <p style={{ fontSize: 13, color: "var(--ikincil)", margin: 0,
                        lineHeight: 1.65 }}>{hata}</p>
            <button className="dugme" style={{ marginTop: 14 }}
              onClick={() => { setHata(null); setDosyaAdi(null); }}>
              Başka dosya dene
            </button>
          </Kart>
        </div>
      )}

      {sihirbaz && (
        <div style={{ maxWidth: 900, marginTop: 14, display: "grid", gap: 14 }}>
          <Kart baslik="Kolonları elle eşleyin"
            sag={<span className="rozet mono">{dosyaAdi}</span>}>
            <p style={{ fontSize: 13, color: "var(--ikincil)",
                        margin: "0 0 14px", lineHeight: 1.65 }}>
              Otomatik eşleme bu dosyada tutmadı — hangi kolonun hangi alana
              denk geldiğini siz söyleyin. Zorunlu: Zaman damgası ve Güç
              (ya da Enerji); gerisi isteğe bağlı.
            </p>
            <table className="veri">
              <thead><tr><th>Alan</th><th>Dosyadaki kolon</th></tr></thead>
              <tbody>
                {Object.entries(ALAN_ADI).map(([k, ad]) => (
                  <tr key={k}>
                    <td>{ad}</td>
                    <td>
                      <select value={secimler[k] ?? ""}
                        style={{ width: "100%", padding: "6px 8px",
                                 font: "inherit" }}
                        onChange={(e) => setSecimler((s) => {
                          const y = { ...s };
                          if (e.target.value) y[k] = e.target.value;
                          else delete y[k];
                          return y;
                        })}>
                        <option value="">—</option>
                        {sihirbaz.columns.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Kart>
          <Kart baslik="Örnek satırlar — ham görünüm">
            <div style={{ overflowX: "auto" }}>
              <table className="veri">
                <thead><tr>
                  {sihirbaz.sample_rows.columns.map((c) => <th key={c}>{c}</th>)}
                </tr></thead>
                <tbody className="mono">
                  {sihirbaz.sample_rows.rows.map((r, i) => (
                    <tr key={i}>{r.map((h, j) => <td key={j}>{h ?? "—"}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Kart>
          <Kart baslik="Onay">
            <p style={{ fontSize: 13, color: "var(--ikincil)", margin: 0,
                        lineHeight: 1.65 }}>
              Saat dilimi santral kaydından alınacak. Şüpheli satırlar
              silinmez, bayraklanır.
            </p>
            <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
              <button className="dugme dugme-ana"
                disabled={kayitta || !sihirbazGecerli}
                title={sihirbazGecerli ? undefined
                  : "Zaman damgası + Güç (veya Enerji) seçilmeli"}
                onClick={sihirbazYukle}>
                {kayitta ? "Yükleniyor…" : "Bu eşlemeyle yükle"}
              </button>
              <button className="dugme" disabled={kayitta}
                onClick={() => { setSihirbaz(null); setDosyaAdi(null);
                                 setDosya(null); }}>
                Vazgeç
              </button>
            </div>
            {kayitHata && (
              <p style={{ fontSize: 13, color: "var(--ikincil)",
                          margin: "12px 0 0", lineHeight: 1.65 }}>{kayitHata}</p>
            )}
          </Kart>
        </div>
      )}

      {on && (
        <div style={{ maxWidth: 900, marginTop: 14, display: "grid", gap: 14 }}>
          <Kart baslik="Dosya nasıl okundu"
            sag={<span className="rozet mono">{dosyaAdi}</span>}>
            <table className="veri"><tbody>
              {sr("Başlık satırı", (on.file_format.header_row + 1) + ". satır")}
              {sr("Ayraç", on.file_format.delimiter === ";" ? "; (noktalı virgül)"
                  : on.file_format.delimiter === "," ? ", (virgül)"
                  : on.file_format.delimiter)}
              {sr("Ondalık işareti", on.file_format.decimal)}
              {sr("Kodlama", on.file_format.encoding)}
              {sr("Algılama güveni", "%" + Math.round(on.file_format.confidence * 100))}
              {on.matched_template ? sr("Eşleşen şablon", on.matched_template) : null}
            </tbody></table>
            {on.notes.length > 0 && (
              <p style={{ fontSize: 12.5, color: "var(--soluk)", margin: "12px 0 0" }}>
                {on.notes.join(" · ")}
              </p>
            )}
          </Kart>

          <Kart baslik="Kolon eşlemesi">
            <table className="veri">
              <thead><tr><th>Alan</th><th>Dosyadaki kolon</th><th>Güven</th></tr></thead>
              <tbody>
                {eslemeler.map((x) => (
                  <tr key={x.k}>
                    <td>{ALAN_ADI[x.k]}</td>
                    <td className="mono">{x.kolon}</td>
                    <td className="mono">
                      {x.guven !== undefined ? "%" + Math.round(x.guven * 100) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {on.unmapped_columns.length > 0 && (
              <p style={{ fontSize: 12.5, color: "var(--soluk)", margin: "12px 0 0" }}>
                Eşlenmeyen kolonlar (yok sayılacak):{" "}
                <span className="mono">{on.unmapped_columns.join(", ")}</span>
              </p>
            )}
          </Kart>

          <Kart baslik="Örnek satırlar — ham görünüm">
            <div style={{ overflowX: "auto" }}>
              <table className="veri">
                <thead><tr>
                  {on.sample_rows.columns.map((c) => <th key={c}>{c}</th>)}
                </tr></thead>
                <tbody className="mono">
                  {on.sample_rows.rows.map((r, i) => (
                    <tr key={i}>{r.map((h, j) =>
                      <td key={j}>{h ?? "—"}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: 12.5, color: "var(--soluk)", margin: "12px 0 0" }}>
              Değerler dosyadan olduğu gibi — dönüştürme onaydan sonra yapılır.
            </p>
          </Kart>

          <Kart baslik="Onay">
            <p style={{ fontSize: 13, color: "var(--ikincil)", margin: 0,
                        lineHeight: 1.65 }}>
              Saat dilimi <span className="mono">{on.onerilen_tz}</span> (santral
              kaydından) ile yüklenecek. Şüpheli satırlar silinmez, bayraklanır.
            </p>
            <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
              <button className="dugme dugme-ana" disabled={kayitta}
                onClick={onayla}>
                {kayitta ? "Yükleniyor…" : "Onayla ve yükle"}
              </button>
              <button className="dugme" disabled={kayitta}
                onClick={() => { setOn(null); setDosyaAdi(null); setDosya(null); }}>
                Vazgeç
              </button>
            </div>
            {kayitHata && (
              <p style={{ fontSize: 13, color: "var(--ikincil)",
                          margin: "12px 0 0", lineHeight: 1.65 }}>{kayitHata}</p>
            )}
          </Kart>
        </div>
      )}

      {karne && (
        <div style={{ maxWidth: 900, marginTop: 14, display: "grid", gap: 14 }}>
          <Kart baslik="Yükleme tamamlandı — kalite karnesi"
            sag={<span className="rozet rozet-ok">
              {sayiTr(karne.n_satir)} satır kaydedildi</span>}>
            <table className="veri"><tbody>
              {sr("Okunan satır", sayiTr(karne.report.n_rows_read))}
              {sr("Geçerli satır", sayiTr(karne.report.n_rows_valid))}
              {sr("Kapsam (UTC)",
                (karne.report.coverage_start?.slice(0, 16) ?? "—") + "  →  " +
                (karne.report.coverage_end?.slice(0, 16) ?? "—"))}
              {sr("Boşluk", sayiTr(karne.report.gap_hours) + " saat")}
            </tbody></table>
            {Object.keys(karne.report.flag_counts).some((k) => k !== "valid") && (
              <>
                <table className="veri" style={{ marginTop: 14 }}>
                  <thead><tr><th>Bayrak</th><th>Satır</th></tr></thead>
                  <tbody>
                    {Object.entries(karne.report.flag_counts)
                      .filter(([k]) => k !== "valid")
                      .map(([k, v]) => (
                        <tr key={k}>
                          <td>{BAYRAK_ADI[k] ?? k}</td>
                          <td className="mono">{sayiTr(v)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
                <p style={{ fontSize: 12.5, color: "var(--soluk)",
                            margin: "12px 0 0" }}>
                  Bayraklı satırlar eğitime girmez ama silinmez — izleri kayıtta.
                </p>
              </>
            )}
            {karne.report.warnings.length > 0 && (
              <p style={{ fontSize: 12.5, color: "var(--soluk)",
                          margin: "12px 0 0" }}>
                {karne.report.warnings.join(" · ")}
              </p>
            )}
          </Kart>
          <Kart baslik="Sırada ne var">
            <p style={{ fontSize: 13, color: "var(--ikincil)", margin: 0,
                        lineHeight: 1.65 }}>
              Model, gece koşusunda bu veriyle kendini yeniden sınar — karneniz
              oradan büyür. Santralim'de "Son veri yüklemesi" şimdi tazelendi.
            </p>
            <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
              {santralimeGit && (
                <button className="dugme dugme-ana" onClick={santralimeGit}>
                  Santralim'e git
                </button>
              )}
              <button className="dugme"
                onClick={() => { setKarne(null); setDosyaAdi(null); setDosya(null); }}>
                Yeni dosya yükle
              </button>
            </div>
          </Kart>
        </div>
      )}

      <p style={{ fontSize: 12.5, color: "var(--soluk)", marginTop: 16, maxWidth: 900 }}>
        Veriniz azsa endişelenmeyin: 3 aydan kısa veri bulursak sizi engellemeyiz,
        hızlı tahminle başlatıp sonra yükseltmenizi öneririz.
      </p>
    </Sayfa>
  );
}

export function Kalibrasyon({ plantId }: { plantId: string }) {
  const [k, setK] = useState<KalibrasyonOzeti | null>(null);
  const [yuklendi, setYuklendi] = useState(false);
  useEffect(() => {
    api.kalibrasyon(plantId).then((v) => { setK(v); setYuklendi(true); });
  }, [plantId]);
  const sr = (a: string, b: string) => <tr key={a}><td>{a}</td><td className="mono">{b}</td></tr>;
  const yzd = (v: number | null) => v === null ? "\u2014" : `%${sayiTr(v, 1)}`;
  const iyilesme = k && k.mape_once && k.mape_sonra
    ? Math.round((1 - k.mape_sonra / k.mape_once) * 100) : null;
  const AY = ["Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara"];
  const { n, oku } = useTema();
  const selale = useMemo(() => {
    const yap = (once: number | null, sonra: number | null, birim: string): EChartsOption | null => {
      if (once === null || sonra === null) return null;
      const o = Math.abs(once), so = Math.abs(sonra);
      const d = so - o;
      const iyi = d < 0;
      const soluk = oku("--soluk"), mono = oku("--mono"), izgara = oku("--izgara");
      const marka = oku("--marka");
      const et = (v: number) => `%${sayiTr(v, 1)}`;
      return {
        grid: { left: 44, right: 10, top: 30, bottom: 26 }, animation: false,
        xAxis: { type: "category", data: ["Fizik", "Kalibrasyon", "Kalibre"],
          axisTick: { show: false }, axisLine: { show: false },
          axisLabel: { color: oku("--ikincil"), fontFamily: mono, fontSize: 12.5 } },
        yAxis: { type: "value", splitLine: { lineStyle: { color: izgara } },
          axisLine: { show: false },
          min: +(Math.min(o, so) * 0.9).toFixed(1),
          max: +(Math.max(o, so) * 1.12).toFixed(1),
          axisLabel: { color: soluk, fontFamily: mono, fontSize: 11,
                       formatter: (v: number) => `%${sayiTr(v, 1)}` } },
        series: [
          { type: "bar", stack: "s", barMaxWidth: 44, silent: true,
            itemStyle: { color: "transparent" },
            data: [0, Math.min(o, so), 0] },
          { type: "bar", stack: "s", barMaxWidth: 44,
            label: { show: true, position: "top", fontFamily: mono,
              fontSize: 13, fontWeight: 600, color: oku("--metin"),
              formatter: (pr: { dataIndex: number }) =>
                [et(o), `${d >= 0 ? "+" : ""}${sayiTr(d, 1)} puan`, et(so)][pr.dataIndex] },
            itemStyle: { borderRadius: [2, 2, 0, 0] },
            data: [
              { value: o, itemStyle: { color: marka } },
              { value: Math.abs(d), itemStyle: { color: iyi ? "#2B7B9B" : "#E8940A" } },
              { value: so, itemStyle: { color: marka } },
            ] },
        ],
      };
    };
    return {
      mape: yap(k?.mape_once ?? null, k?.mape_sonra ?? null, "MAPE"),
      sapma: yap(k?.sapma_once ?? null, k?.sapma_sonra ?? null, "sapma"),
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [k, n]);
  const trTarih = (iso: string | null) => {
    if (!iso) return "\u2014";
    const d = new Date(iso);
    return `${d.getDate()} ${AY[d.getMonth()]} ${d.getFullYear()}`;
  };
  return (
    <Sayfa baslik="Kalibrasyon"
      alt="Model, santralinizin kendi verisiyle uyarlanır — kanıtı bu sayfada görürsünüz."
      sag={<button className="dugme" disabled
        title="Bu akış şimdilik Streamlit panelinde — SPA'ya sırası gelince taşınacak"
        style={{ opacity: 0.55, cursor: "not-allowed" }}>Yeniden kalibre et</button>}>
      {yuklendi && !k && (
        <Kart baslik="Aktif kalibrasyon yok">
          <p style={{ fontSize: 13.5, color: "var(--soluk)", margin: 0 }}>
            Bu santral için aktif bir kalibrasyon kaydı bulunmuyor — SCADA verisi
            yükleyip kalibre tahmine geçtiğinizde bu sayfa kendiliğinden dolar.
          </p>
        </Kart>
      )}
      {k && (<>
      {k.uyarilar.length > 0 && (
        <div style={{ background: "var(--amber-zemin)", border: "1px solid var(--amber)",
                      borderRadius: "var(--rk)", padding: "12px 16px", marginBottom: 14,
                      fontSize: 13, color: "var(--metin)" }}>
          <b>Kalibrasyon uyarısı:</b> {k.uyarilar.join(" · ")}
        </div>
      )}
      <div className="ızgara satir-3" style={{ marginBottom: 14 }}>
        <Kpi etiket={`Kalibre MAPE · Mod ${k.mode}`} deger={yzd(k.mape_sonra)}
             alt="kalibrasyon dönemi, saatlik" />
        <Kpi etiket="Fizik · aynı sınav" deger={yzd(k.mape_once)}
             alt="karşılaştırma tabanı" />
        <Kpi etiket="İyileşme" deger={iyilesme === null ? "\u2014" : `%${iyilesme}`}
             ton={iyilesme !== null && iyilesme < 0 ? "amber" : undefined}
             alt={iyilesme === null ? "\u2014"
               : iyilesme > 0 ? "kalibrasyon kazancı"
               : "MAPE kazancı yok — sapma düzeltmesi için Mod C aktif"} />
      </div>
      <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)" }}>
        <Kart baslik="Bulduklarımız">
          <table className="veri"><tbody>
            {sr("η_BoS", k.eta_bos === null ? "\u2014" : sayiTr(k.eta_bos, 3))}
            {sr("BG (bifasyal kazanç)", k.bg === null ? "\u2014" : sayiTr(k.bg, 3))}
            {sr("Geçerli saat", k.gecerli_saat === null ? "\u2014" : sayiTr(k.gecerli_saat))}
            {sr("Kalibrasyon tarihi", trTarih(k.tarih))}
          </tbody></table>
        </Kart>
        <Kart baslik="Yıllık enerji sapması">
          <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
            <span className="mono" style={{ fontSize: 22, color: "var(--soluk)" }}>{yzd(k.sapma_once)}</span>
            <span style={{ color: "var(--soluk)" }}>{"\u2192"}</span>
            <span className="mono" style={{ fontSize: 30, letterSpacing: "-0.03em" }}>{yzd(k.sapma_sonra)}</span>
          </div>
          <p style={{ fontSize: 12.5, color: "var(--soluk)", margin: "14px 0 0" }}>
            Fizik → kalibre model. Bu sayı kalibrasyon dönemindeki sistematik sapmadır;
            saatlik tahmin isabeti Doğruluk sayfasında ölçülür.
          </p>
        </Kart>
      </div>
      {(selale.mape || selale.sapma) && (
        <Kart baslik="Kalibrasyonun etkisi — fizikten kalibre modele"
          sag={<span className="cip">mavi: iyileşme · amber: bedel</span>}>
          <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)" }}>
            {selale.mape && (
              <div>
                <p style={{ fontSize: 12.5, fontWeight: 600, color: "var(--metin)",
                            margin: "0 0 4px" }}>Saatlik isabet — MAPE</p>
                <EChart option={selale.mape} height={210}
                  ariaLabel="Fizikten kalibre modele MAPE değişimi şelalesi" />
              </div>
            )}
            {selale.sapma && (
              <div>
                <p style={{ fontSize: 12.5, fontWeight: 600, color: "var(--metin)",
                            margin: "0 0 4px" }}>Enerji sapması — mutlak %</p>
                <EChart option={selale.sapma} height={210}
                  ariaLabel="Fizikten kalibre modele mutlak enerji sapması şelalesi" />
              </div>
            )}
          </div>
          <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
            Orta basamak kalibrasyonun katkısıdır — aşağı inen mavi basamak iyileşmeyi,
            yukarı çıkan amber basamak bedeli gösterir.
          </p>
        </Kart>
      )}
      </>)}
    </Sayfa>
  );
}

export function Raporlar({ plantId }: { plantId: string }) {
  // v2.94: Hazirla canlandi — tek uretim kapisi HTTP'den; gecmis kosular
  // sabit ornek degil, forecast_runs'tan gercek liste.
  const [kosular, setKosular] = useState<KosuSatiri[]>([]);
  const [uretilen, setUretilen] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null);

  useEffect(() => {
    api.kosular(plantId).then(setKosular).catch(() => {});
  }, [plantId]);

  const MODEL_AD: Record<string, string> = {
    hybrid_residual: "Hibrit", barhdadi_bennis: "Fizik",
    backtest: "Geriye dönük",
  };
  const tarihTr = (iso: string) => {
    const d = new Date(iso);
    const iki = (x: number) => String(x).padStart(2, "0");
    return iki(d.getDate()) + "." + iki(d.getMonth() + 1) + "." +
           d.getFullYear() + " " + iki(d.getHours()) + ":" + iki(d.getMinutes());
  };

  const hazirla = async (fmt: "pdf" | "pdf16" | "xlsx" | "json") => {
    setUretilen(fmt); setHata(null);
    try { await api.raporIndir(plantId, fmt); }
    catch (e) { setHata(e instanceof Error ? e.message : String(e)); }
    finally { setUretilen(null); }
  };

  const kartlar: [string, "pdf" | "xlsx" | "json", string][] = [
    ["PDF", "pdf", "Yönetici özeti — logo, KPI'lar, holdout kutusu"],
    ["Excel", "xlsx", "Tam veri — saatlik tablo, özet ve metadata"],
    ["JSON", "json", "API formatı — şema 1.1.0, entegrasyona hazır"],
  ];
  return (
    <Sayfa baslik="Raporlar"
      alt="Hepsi tahmin arşivinden üretilir — koşular güncellenmez, yenisi eklenir.">
      <Kart baslik="16 sayfalık müşteri raporu">
        <div style={{ fontSize: 13, color: "var(--ikincil)", lineHeight: 1.6 }}>
          Kapaktan eklere tam rapor — doğruluk karnesi, hata dağılımı,
          kalibrasyon, veri kalitesi, iklim zarfı ve model zinciri. Tek A4,
          16 sayfa, PDF.
        </div>
        <button className="dugme" disabled={uretilen !== null}
          onClick={() => hazirla("pdf16")}
          style={{ width: "100%", marginTop: 14 }}>
          {uretilen === "pdf16" ? "Hazırlanıyor…" : "Hazırla"}
        </button>
      </Kart>
      <div className="ızgara satir-3" style={{ margin: "14px 0 14px" }}>
        {kartlar.map(([ad, fmt, alt]) => (
          <Kart key={ad} baslik={ad}>
            <div style={{ fontSize: 13, color: "var(--ikincil)", minHeight: 38 }}>{alt}</div>
            <button className="dugme" disabled={uretilen !== null}
              onClick={() => hazirla(fmt)}
              style={{ width: "100%", marginTop: 14 }}>
              {uretilen === fmt ? "Hazırlanıyor…" : "Hazırla"}
            </button>
          </Kart>
        ))}
      </div>
      {hata && (
        <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "0 0 14px",
                    lineHeight: 1.65 }}>{hata}</p>
      )}
      <Kart baslik="Geçmiş koşular">
        {kosular.length === 0 ? (
          <p style={{ fontSize: 12.5, color: "var(--soluk)", margin: 0,
                      lineHeight: 1.65 }}>
            Henüz koşu yok — ilk tahmin koşusuyla bu tablo dolar.
          </p>
        ) : (
          <table className="veri">
            <thead><tr><th>Tarih</th><th>Mod</th><th>Model</th></tr></thead>
            <tbody className="mono">
              {kosular.map((r) => (
                <tr key={r.run_at}>
                  <td>{tarihTr(r.run_at)}</td>
                  <td>{r.mode}</td>
                  <td>{MODEL_AD[r.model] ?? r.model}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Kart>
    </Sayfa>
  );
}
