import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { SantralOzeti, TahminSerisi } from "../../api/types";
import { sayiTr } from "../../theme/tokens";
import { FanChart } from "./FanChart";
import { Kpi, Bolum } from "../sayfalar/parcalar";

export function Santralim({ plantId }: { plantId: string }) {
  const [ozet, setOzet] = useState<SantralOzeti | null>(null);
  const [seri, setSeri] = useState<TahminSerisi | null>(null);
  useEffect(() => { api.ozet(plantId).then(setOzet); }, [plantId]);
  useEffect(() => { api.tahmin(plantId, "24h").then(setSeri); }, [plantId]);
  if (!ozet) return <div style={{ color: "var(--soluk)" }}>Yükleniyor…</div>;

  return (
    <>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 4 }}>
        <h1 style={{ fontSize: 21, fontWeight: 600, margin: 0, letterSpacing: "-0.02em" }}>{ozet.ad}</h1>
        <span className="mono" style={{ fontSize: 13, color: "var(--soluk)" }}>
          {sayiTr(ozet.kapasite_kwp)} kWp · {ozet.lat}, {ozet.lon}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 22 }}>
        <span className="rozet rozet-ok">{ozet.model_adi} · Mod {ozet.mod}</span>
        <span style={{ fontSize: 13, color: "var(--ikincil)" }}>
          yıllık enerji sapması %{sayiTr(ozet.sapma_pct ?? 0, 2)} · eğim/azimut {ozet.egim_azimut}
        </span>
      </div>

      <div style={{ display: "grid", gap: 12, marginBottom: 22,
                    gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))" }}>
        <Kpi etiket="Bugün · P50" deger={sayiTr(ozet.bugun_kwh ?? 0)} birim="kWh" />
        <Kpi etiket="Yarın · P50" deger={sayiTr(ozet.yarin_kwh ?? 0)} birim="kWh" />
        <Kpi etiket="7 gün · P50" deger={sayiTr(ozet.hafta_mwh ?? 0, 1)} birim="MWh" />
        <Kpi etiket="AC tavanı" deger={sayiTr(ozet.ac_tavani_kw ?? 0)} birim="kW" />
      </div>

      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "1.6fr 1fr", alignItems: "start" }}>
        <Bolum baslik="Bugün — saatlik üretim">
          {seri && <FanChart seri={seri} />}
        </Bolum>
        <Bolum baslik="7 günlük görünüm">
          <table className="veri">
            <thead><tr><th>Gün</th><th>MWh</th></tr></thead>
            <tbody className="mono">
              {ozet.gunler.map((g) => (
                <tr key={g.etiket}><td>{g.etiket}</td><td>{sayiTr(g.mwh, 1)}</td></tr>
              ))}
            </tbody>
          </table>
        </Bolum>
      </div>

      <div style={{ marginTop: 16 }}>
        <Bolum baslik="Veri sağlığı">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20, fontSize: 13 }}>
            <div><div style={{ color: "var(--soluk)", marginBottom: 4 }}>Son SCADA yüklemesi</div>
              <div className="mono" style={{ color: "var(--uyari)", fontSize: 15 }}>30 Nis 2026</div>
              <div style={{ color: "var(--uyari)", fontSize: 12, marginTop: 3 }}>veri akışı 91 gündür kesik</div></div>
            <div><div style={{ color: "var(--soluk)", marginBottom: 4 }}>İşlenen veri</div>
              <div className="mono" style={{ fontSize: 15 }}>5.781 saat</div></div>
            <div><div style={{ color: "var(--soluk)", marginBottom: 4 }}>Anomali tespiti</div>
              <div className="mono" style={{ fontSize: 15 }}>11.737</div>
              <div style={{ color: "var(--soluk)", fontSize: 12, marginTop: 3 }}>işaretlendi, silinmedi</div></div>
          </div>
        </Bolum>
      </div>
    </>
  );
}
