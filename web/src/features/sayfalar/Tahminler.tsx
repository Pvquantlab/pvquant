import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { TahminSerisi } from "../../api/types";
import { sayiTr } from "../../theme/tokens";
import { FanChart } from "../santralim/FanChart";
import { Bolum } from "./parcalar";

const UFUK = { "24h": "24s", "72h": "72s", "7d": "7g", "16d": "16g" } as const;
type U = keyof typeof UFUK;

export function Tahminler({ plantId }: { plantId: string }) {
  const [ufuk, setUfuk] = useState<U>("7d");
  const [seri, setSeri] = useState<TahminSerisi | null>(null);
  useEffect(() => { api.tahmin(plantId, ufuk).then(setSeri); }, [plantId, ufuk]);

  return (
    <>
      <h1 style={{ fontSize: 21, fontWeight: 600, margin: "0 0 4px", letterSpacing: "-0.02em" }}>Tahminler</h1>
      <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "0 0 18px" }}>
        {seri ? `${seri.ufuk_saat} saatlik kalibre üretim tahmini` : "…"} — arşivden, son koşu.
      </p>
      <div className="sekme" style={{ marginBottom: 16 }}>
        {(Object.keys(UFUK) as U[]).map((u) => (
          <button key={u} aria-pressed={u === ufuk} onClick={() => setUfuk(u)}>{UFUK[u]}</button>
        ))}
      </div>
      {seri && (
        <>
          <Bolum baslik="Saatlik tahmin ve P10–P90 bandı">
            <FanChart seri={seri} />
          </Bolum>
          <div style={{ marginTop: 16 }}>
            <Bolum baslik="Günlük toplamlar">
              <table className="veri">
                <thead><tr><th>Tarih</th><th>P50 kWh</th><th>P10–P90 kWh</th></tr></thead>
                <tbody className="mono">
                  {seri.gunluk.map((g) => (
                    <tr key={g.tarih}>
                      <td>{new Date(g.tarih).toLocaleDateString("tr-TR", { day: "numeric", month: "short" })}</td>
                      <td>{sayiTr(g.p50_kwh)}</td>
                      <td style={{ color: "var(--ikincil)" }}>
                        {sayiTr(g.p10_kwh ?? 0)} – {sayiTr(g.p90_kwh ?? 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Bolum>
          </div>
        </>
      )}
    </>
  );
}
