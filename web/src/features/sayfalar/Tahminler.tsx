import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { SantralOzeti, TahminSerisi, KgupOnizleme, Nowcast } from "../../api/types";
import { Kart, Sayfa, sayiTr } from "./parcalar";
import ProductionForecastChart from "./ProductionForecastChart";
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

export function Tahminler({ plantId }: { plantId: string }) {
  const [ufuk, setUfuk] = useState<Ufuk>("7d");
  const [seri, setSeri] = useState<TahminSerisi | null>(null);
  const [ozet, setOzet] = useState<SantralOzeti | null>(null);
  const [kgup, setKgup] = useState<KgupOnizleme | null>(null);   // v2.260
  const [kgupHata, setKgupHata] = useState<string | null>(null);
  useEffect(() => { api.kgupOnizleme(plantId).then(setKgup).catch(() => setKgup(null)); }, [plantId]);
  const [nc, setNc] = useState<Nowcast | null | undefined>(undefined);   // v2.266
  // v2.273: son koşunun bant kaynağı (ensemble üyeleri / model) — dip notta dürüstçe söylenir
  const [bantYazisi, setBantYazisi] = useState<string | null>(null);
  useEffect(() => {
    api.kosular(plantId).then((k) => {
      const b = k[0]?.bant;
      const s = k[0]?.sapma;
      const sy = s?.aktif ? ` · son ${sayiTr(s.n_gun ?? 0)} günün ölçümüyle %${sayiTr(((s.oran_genel ?? 1) - 1) * 100, 1)} düzeltildi` : "";
      setBantYazisi((!b ? "" : b.kaynak === "gefs" ? `${sayiTr(b.uye ?? 0)} üyeli hava topluluğundan ampirik kantil` : "model bandı") + sy || null);
    }).catch(() => setBantYazisi(null));
  }, [plantId]);
  useEffect(() => { api.nowcast(plantId).then(setNc).catch(() => setNc(null)); }, [plantId]);
  useEffect(() => {
    api.tahmin(plantId, "16d").then(setSeri); // single fetch — D1/D2
  }, [plantId]);
  useEffect(() => {
    api.ozet(plantId).then(setOzet);
  }, [plantId]);

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

  return (
    <Sayfa
      baslik="Tahminler"
      alt={
        dilim
          ? `${dilim.tahminSaat} saatlik tahmin · ${dilim.gecmisSaat} sa arşiv bağlamı — son koşu.`
          : ""
      }
      sag={
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
      }
    >
      {seri && ozet && dilim && (
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
              forecast={dilim.saatlik.map((s) => ({
                ts: s.ts,
                p10: s.p10_kw,
                p50: s.p50_kw,
                p90: s.p90_kw,
                p25: s.p25_kw,
                p75: s.p75_kw,
              }))}
              actual={dilim.saatlik
                .filter((s) => s.gercek_kw !== null)
                .map((s) => ({ ts: s.ts, kw: s.gercek_kw as number }))}
              nowMs={t0}
              nowValue={nowVal}
              gunes={seri.gunes}
              mode={GUNLUK_MOD[ufuk] ? "daily" : "hourly"}
              plant={{
                acCapacityKw: seri.ac_tavani_kw ?? ozet.ac_tavani_kw,
                lat: ozet.lat,
                lon: ozet.lon,
                timezone: ozet.tz,
              }}
              features={{ exportButtons: true }}  // v2.228: PNG/CSV — SaaS eylemi
              height={360}
            />
            <p
              style={{
                fontSize: 12,
                color: "var(--soluk)",
                margin: "12px 0 0",
              }}
            >
              <b style={{ color: "var(--ikincil)" }}>Bu grafik son koşunun
              saatlik üretim tahminidir:</b> mavi çizgi P50 (medyan senaryo),
              bant P10–P90 aralığı — saatlerin %80'inin içinde kalması beklenen
              koridor; amber çizgi varsa gerçekleşen üretimdir. Son koşu Mod{" "}
              {seri.mod ?? "—"}{bantYazisi ? ` · bant: ${bantYazisi}` : ""} · kaynak: tahmin arşivi — koşular güncellenmez,
              yenisi eklenir.
            </p>
          </Kart>
          <Kart baslik="Günlük toplamlar">
            <table className="veri">
              <thead>
                <tr>
                  <th>Tarih</th>
                  <th>P50 kWh</th>
                  {bantVar && <th>P10–P90</th>}
                </tr>
              </thead>
              <tbody className="mono">
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
            {gunlukVeri.some((g) => g.kismi) && (
              <p style={{ color: "var(--ikincil)", fontSize: 12, marginTop: 8 }}>
                * pencereye kısmen giren gün
              </p>
            )}
          </Kart>
        </div>
      )}
      {/* v2.260 (Dalga 4.13): KGÜP bildirim dosyası — D-1 15:30 öncesi koşudan saatlik program (TPYS CSV) */}
      <Kart baslik="KGÜP bildirimi — yarının saatlik programı"
        sag={<span className="cip">{kgup ? `${kgup.teslim.hedef_gun} · pencere ${kgup.teslim.durum === "pencere_acik" ? "açık" : kgup.teslim.durum === "erken" ? "henüz açılmadı" : "kapandı"} (14:00–15:30) · teyit ${kgup.teslim.teyit_saati.slice(0, 5)}` : "koşu bekleniyor"}</span>}>
        {kgup ? (
          <>
            <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
              <span className="mono">{sayiTr(kgup.toplam_mwh, 1)} MWh · {kgup.kantil.toUpperCase()} · koşu {kgup.kosu.run_at ? new Date(kgup.kosu.run_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—"}</span>
              <button className="dugme" onClick={() => { setKgupHata(null); api.kgupIndir(plantId).catch((e) => setKgupHata(String(e.message ?? e))); }}>CSV indir (TPYS)</button>
              <button className="dugme" onClick={() => { setKgupHata(null); api.kgupIndir(plantId, undefined, "p10").catch((e) => setKgupHata(String(e.message ?? e))); }}>Temkinli (P10) indir</button>
              {kgupHata && <span style={{ color: "var(--uyari)", fontSize: 12.5 }}>{kgupHata}</span>}
            </div>
            {kgup.uyarilar.length > 0 && <p style={{ color: "var(--uyari)", fontSize: 12.5, margin: "8px 0 0" }}>{kgup.uyarilar.join(" · ")}</p>}
            {kgup.sicrama_saatleri.length > 0 && <p style={{ fontSize: 12.5, margin: "8px 0 0" }}>≥200 MWh sıçrama: saat {kgup.sicrama_saatleri.join(", ")} — dosyada 15 dakikalık dilimler.</p>}
            <p className="soluk" style={{ fontSize: 12.5, margin: "10px 0 0" }}>
              Program, teslim kesiminden (D-1 15:30) önce verilmiş son koşunun saatlik P50'sidir; KGÜP ≤ emre amade kapasite ≤ kurulu güç
              kuralı uygulanır. CSV kolon adları TPYS şablonuyla eşlenmelidir (resmi şablon teyit edilemedi); dosya bir öneridir, bildirim TPYS'de yapılır.
            </p>
          </>
        ) : <p className="soluk" style={{ margin: 0 }}>Yarın için teslim kesiminden önce verilmiş koşu yok — sabah koşusu geldiğinde burada görünür.</p>}
      </Kart>
      {/* v2.266 (Dalga 5.18): kısa ufuk — ölçüm persistansı; uydu değil. Canlı SCADA yoksa dürüstçe tire. */}
      <Kart baslik="Kısa ufuk (0–6 saat) — ölçüm persistansı"
        sag={<span className="cip">{nc?.durum === "ok" ? `oran ${sayiTr(nc.oran ?? 0, 2)} · ${sayiTr(nc.n_saat)} saatten` : nc?.durum === "gece" ? "gece · P50" : "uydu değil"}</span>}>
        {nc === undefined ? <p className="soluk" style={{ margin: 0 }}>Yükleniyor…</p>
         : !nc || nc.durum === "scada_bayat" || nc.durum === "olcum_yok" || nc.durum === "tahmin_yok" ? (
          <p className="soluk" style={{ margin: 0 }}>
            — {nc?.not ?? "hesaplanamadı"}{nc?.tazelik_saat != null ? ` (son ölçüm ${nc.tazelik_saat >= 48 ? `${sayiTr(nc.tazelik_saat / 24, 0)} gün` : `${sayiTr(nc.tazelik_saat, 0)} saat`} önce)` : ""}.
            Bu katman son 3 saatin ölçüm/tahmin oranını ileri taşır; dosya yüklemeli santralde çalışmaz.
          </p>
        ) : (
          <>
            <div className="grafik-kaydir">
              <table className="veri" style={{ fontSize: 12.5 }}>
                <thead><tr><th>Saat</th><th>P50</th><th>Kısa ufuk</th><th>Persistans ağırlığı</th></tr></thead>
                <tbody className="mono">
                  {nc.ufuk.map((u) => (
                    <tr key={u.ts}><td>{new Date(u.ts).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}</td>
                      <td>{sayiTr(u.p50_kw)} kW</td><td>{sayiTr(u.nowcast_kw)} kW</td><td>%{sayiTr(u.agirlik * 100, 0)}</td></tr>))}
                </tbody>
              </table>
            </div>
            <p className="soluk" style={{ fontSize: 12.5, margin: "10px 0 0" }}>
              Uydu bulut-hareket tahmini değil: son {sayiTr(nc.n_saat)} saatin ölçüm/tahmin oranı ({sayiTr(nc.oran ?? 0, 2)}) ufuk boyunca üstel sönümle
              (τ = 2 saat) P50'ye harmanlanır; 6 saat sonrası P50'dir. Gün içi KGÜP güncellemesi (GİP kapanış + 30 dk) için yol göstericidir, kayıt yazmaz.
            </p>
          </>
        )}
      </Kart>
    </Sayfa>
  );
}
