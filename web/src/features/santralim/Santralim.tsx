import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { SantralOzeti, TahminSerisi } from "../../api/types";
import { Kpi, Kart, Sayfa, Lejant, sayiTr } from "../sayfalar/parcalar";
import { FanChart } from "./FanChart";
import { Cubuklar } from "./Cubuklar";

export function Santralim({ plantId }: { plantId: string }) {
  const [o, setO] = useState<SantralOzeti | null>(null);
  const [seri, setSeri] = useState<TahminSerisi | null>(null);
  useEffect(() => { api.ozet(plantId).then(setO); }, [plantId]);
  useEffect(() => { api.tahmin(plantId, "24h").then(setSeri); }, [plantId]);
  if (!o) return <div style={{ color: "var(--soluk)" }}>Yükleniyor…</div>;

  const s = o.saglik;
  return (
    <Sayfa baslik={o.ad}
      alt={o.anlati}
      sag={<div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span className="rozet rozet-ok">{o.model_adi} · Mod {o.mod}</span>
        <span className="mono" style={{ fontSize: 12.5, color: "var(--soluk)" }}>
          {sayiTr(o.kapasite_kwp)} kWp · {o.lat}, {o.lon}
        </span>
      </div>}>

      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket="Bugün · P50" deger={sayiTr(o.bugun_kwh ?? 0)} birim="kWh"
             alt="gün sonu itibarıyla" />
        <Kpi etiket="Yarın · P50" deger={sayiTr(o.yarin_kwh ?? 0)} birim="kWh"
             alt={o.hava[1]
               ? `${sayiTr(o.hava[1].isinim, 1)} kWh/m² ışınım`
               : "—"} />  {/* v2.90: veri yokken 0,0 uydurma — tire ilkesi */}
        <Kpi etiket="7 gün · P50" deger={sayiTr(o.hafta_mwh ?? 0, 1)} birim="MWh"
             alt="kayan 7 gün" />
        <Kpi etiket="Model durumu" deger={o.model_adi}
             alt={`yıllık sapma %${sayiTr(o.sapma_pct ?? 0, 2)} · son kalibrasyon ${o.son_kalibrasyon}`} />
      </div>

      <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,2.1fr) minmax(0,1fr)",
                                       marginBottom: 14 }}>
        <Kart baslik="Bugün — saatlik üretim"
          sag={<Lejant ogeler={[{ renk: "var(--marka)", ad: "Tahmin P50" },
                                ...(seri && seri.saatlik.some((s) =>
                                    s.p10_kw !== null && s.p90_kw !== null)
                                  ? [{ renk: "var(--marka-acik)", ad: "P10–P90" }]
                                  : [])]} />}>
          {seri && <FanChart seri={seri} yukseklik={300} />}
          <p style={{ fontSize: 12, color: "var(--soluk)", margin: "10px 0 0" }}>
            Gerçekleşen üretimi görmek için bugünün SCADA verisini yükleyin.
          </p>
        </Kart>

        <div style={{ display: "grid", gap: 14, alignContent: "start" }}>
          <Kart baslik="Hava">
            {o.hava.length === 0 && (
              /* v2.90: bos kart sessiz kalmasin — neden bos, soyle */
              <p style={{ fontSize: 12.5, color: "var(--soluk)", margin: 0,
                          lineHeight: 1.65 }}>
                Hava özeti son tahmin koşusundan gelir — bugünü kapsayan
                koşu yok. Yeni koşuyla bu kart kendiliğinden dolar.
              </p>
            )}
            <div className="hava">
              {o.hava.map((h) => (
                <div key={h.etiket} className="hava-kart">
                  <div className="hava-gun">{h.etiket}</div>
                  <div className="hava-sic mono">{sayiTr(h.sicaklik, 1)}°</div>
                  <div className="hava-isin mono">{sayiTr(h.isinim, 1)} kWh/m²</div>
                </div>
              ))}
            </div>
          </Kart>
          <Kart baslik="Santral künyesi">
            <table className="veri">
              <tbody className="mono">
                <tr><td>DC gücü</td><td>{sayiTr(o.kapasite_kwp)} kWp</td></tr>
                <tr><td>AC tavanı</td><td>{sayiTr(o.ac_tavani_kw ?? 0)} kW</td></tr>
                <tr><td>Eğim / azimut</td><td>{o.egim_azimut}</td></tr>
                <tr><td>Saat dilimi</td><td>{o.tz}</td></tr>
              </tbody>
            </table>
          </Kart>
        </div>
      </div>

      <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)",
                                       marginBottom: 14 }}>
        <Kart baslik="7 günlük görünüm" sag={<span className="cip mono">
          {sayiTr(o.hafta_mwh ?? 0, 1)} MWh toplam</span>}>
          <Cubuklar etiketler={o.gunler.map((g) => g.etiket)}
            degerler={o.gunler.map((g) => g.mwh)} birim="MWh" vurguIdx={0} yukseklik={230} />
        </Kart>
        <Kart baslik="Veri sağlığı">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
            <div>
              <div className="kpi-et">Son veri yüklemesi</div>
              <div className="mono" style={{ fontSize: 17, color: "var(--uyari)" }}>{s.son_scada}</div>
              <div style={{ fontSize: 12, color: "var(--uyari)", marginTop: 3, fontWeight: 500 }}>
                {s.kesinti_gun} gündür yeni veri yok</div>
            </div>
            <div>
              <div className="kpi-et">İşlenen veri</div>
              <div className="mono" style={{ fontSize: 17 }}>{sayiTr(s.islenen_saat)}</div>
              <div style={{ fontSize: 12, color: "var(--soluk)", marginTop: 3 }}>
                saatlik ölçüm, temiz ve hazır</div>
            </div>
            <div>
              <div className="kpi-et">Anomali tespiti</div>
              <div className="mono" style={{ fontSize: 17 }}>{sayiTr(s.anomali)}</div>
              <div style={{ fontSize: 12, color: "var(--soluk)", marginTop: 3 }}>
                işaretlendi — tek satır silinmedi</div>
            </div>
          </div>
          <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "16px 0 0",
                      lineHeight: 1.55 }}>
            Model, en taze verinizle en güçlü hâlindedir. Yeni SCADA dosyanızı
            yükleyin — tahmin o gece kendini yeniden sınar, karneniz büyür.
          </p>
        </Kart>
      </div>

      <Kart baslik="Aylık üretim — gerçekleşen"
        sag={<span className="cip">son 12 ay</span>}>
        <Cubuklar etiketler={o.aylik.map((a) => a.ay)} degerler={o.aylik.map((a) => a.mwh)}
          birim="MWh" vurguIdx={o.aylik.length - 1} yukseklik={250} />
        <table className="veri" style={{ marginTop: 18 }}>
          <thead><tr><th>Ay</th><th>Üretim MWh</th><th>Sağlam saat</th><th>Kapsam %</th></tr></thead>
          <tbody className="mono">
            {[...o.aylik].reverse().slice(0, 6).map((a) => (
              <tr key={a.ay}>
                <td>{a.ay}</td><td>{sayiTr(a.mwh, 1)}</td>
                <td>{sayiTr(a.saglam_saat)}</td>
                <td style={{ color: "var(--ikincil)" }}>{sayiTr(a.kapsam_pct, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Kart>
    </Sayfa>
  );
}
