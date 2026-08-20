import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { SantralOzeti, TahminSerisi } from "../../api/types";
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
              }))}
              actual={dilim.saatlik
                .filter((s) => s.gercek_kw !== null)
                .map((s) => ({ ts: s.ts, kw: s.gercek_kw as number }))}
              nowMs={t0}
              nowValue={nowVal}
              mode={GUNLUK_MOD[ufuk] ? "daily" : "hourly"}
              plant={{
                acCapacityKw: seri.ac_tavani_kw ?? ozet.ac_tavani_kw,
                lat: ozet.lat,
                lon: ozet.lon,
                timezone: ozet.tz,
              }}
              height={360}
            />
            <p
              style={{
                fontSize: 12,
                color: "var(--soluk)",
                margin: "12px 0 0",
              }}
            >
              Son koşu Mod {seri.mod ?? "—"} · kaynak: tahmin arşivi — koşular
              güncellenmez, yenisi eklenir.
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
    </Sayfa>
  );
}
