import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { TahminSerisi } from "../../api/types";
import { Kart, Sayfa, Lejant, sayiTr } from "./parcalar";
import { FanChart } from "../santralim/FanChart";

const UFUK = { "24h": "24s", "72h": "72s", "7d": "7g", "16d": "16g" } as const;
type U = keyof typeof UFUK;

export function Tahminler({ plantId }: { plantId: string }) {
  const [ufuk, setUfuk] = useState<U>("7d");
  const [seri, setSeri] = useState<TahminSerisi | null>(null);
  useEffect(() => { api.tahmin(plantId, ufuk).then(setSeri); }, [plantId, ufuk]);

  return (
    <Sayfa baslik="Tahminler"
      alt={seri ? `${seri.ufuk_saat} saatlik kalibre üretim tahmini — arşivden, son koşu.` : ""}
      sag={<div className="sekme">
        {(Object.keys(UFUK) as U[]).map((u) => (
          <button key={u} aria-pressed={u === ufuk} onClick={() => setUfuk(u)}>{UFUK[u]}</button>
        ))}
      </div>}>
      {seri && (
        <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1.9fr) minmax(0,1fr)" }}>
          <Kart baslik="Saatlik tahmin ve P10–P90 aralığı"
            sag={<Lejant ogeler={[{ renk: "var(--marka)", ad: "P50" },
                                  { renk: "var(--marka-acik)", ad: "P10–P90" }]} />}>
            <FanChart seri={seri} yukseklik={360} />
            <p style={{ fontSize: 12, color: "var(--soluk)", margin: "12px 0 0" }}>
              Son koşu Mod {seri.mod ?? "—"} · kaynak: tahmin arşivi — koşular güncellenmez, yenisi eklenir.
            </p>
          </Kart>
          <Kart baslik="Günlük toplamlar">
            <table className="veri">
              <thead><tr><th>Tarih</th><th>P50 kWh</th><th>P10–P90</th></tr></thead>
              <tbody className="mono">
                {seri.gunluk.map((g) => (
                  <tr key={g.tarih}>
                    <td>{new Date(g.tarih).toLocaleDateString("tr-TR",
                        { day: "numeric", month: "short" })}</td>
                    <td>{sayiTr(g.p50_kwh)}</td>
                    <td style={{ color: "var(--ikincil)" }}>
                      {sayiTr(g.p10_kwh ?? 0)}–{sayiTr(g.p90_kwh ?? 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Kart>
        </div>
      )}
    </Sayfa>
  );
}
