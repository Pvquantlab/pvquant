import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Portfoy as PortfoyT } from "../../api/types";
import { Kart, Kpi, Sayfa, sayiTr } from "./parcalar";

/** v2.263 (Dalga 5.15) — Portföy: kiracının tüm santralleri tek tabloda; toplamlar dürüst
 *  (bir santralin beklentisi yoksa toplam da yok). Satıra tıklayınca o santrala geçilir. */
export function Portfoy({ onSec }: { onSec: (id: string) => void }) {
  const [p, setP] = useState<PortfoyT | null | undefined>(undefined);
  useEffect(() => { api.portfoy().then(setP).catch(() => setP(null)); }, []);
  const t = p?.toplam ?? null;
  const kwhYaz = (v: number | null | undefined) => v == null ? "—" : `${sayiTr(v / 1000, 1)} MWh`;
  const tarih = (s: string | null) => s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  return (
    <Sayfa baslik="Portföy" alt="Tüm santraller bir bakışta — sayılar kapasite ile ağırlıklı, eksikler tire."
      sag={<span className="cip">{p ? `${sayiTr(p.santraller.length)} santral · ${p.gun}` : "yükleniyor"}</span>}>
      <div className="ızgara satir-4" style={{ marginBottom: 14 }}>
        <Kpi etiket="Toplam kurulu güç" deger={t ? sayiTr(t.kapasite_kwp / 1000, 2) : "—"} birim="MWp" alt={t ? `${sayiTr(t.santral)} santral` : ""} />
        <Kpi etiket="Bugün beklenen · yarın" deger={t ? `${kwhYaz(t.bugun_kwh)} · ${kwhYaz(t.yarin_kwh)}` : "—"}
             alt={t && (t.bugun_kwh == null || t.yarin_kwh == null) ? "bir santralde beklenti yok → toplam yazılmaz" : "tüm santrallerin P50 toplamı"} />
        <Kpi etiket="30 günlük WMAPE (ağırlıklı)" deger={t?.wmape_agirlikli != null ? `%${sayiTr(t.wmape_agirlikli, 1)}` : "—"}
             alt={t ? `${sayiTr(t.wmape_kapsanan_kwp / 1000, 2)} MWp karneli` : ""} />
        <Kpi etiket="Açık alarm · veri gecikmiş" deger={t ? `${sayiTr(t.acik_alarm)} · ${sayiTr(t.veri_gecikmis)}` : "—"}
             alt="son 7 gün okunmamış · 2 günden eski ölçüm" ton={t && (t.acik_alarm > 0 || t.veri_gecikmis > 0) ? "amber" : undefined} />
      </div>
      <Kart baslik="Santraller" sag={<span className="cip">satıra tıkla → santral</span>}>
        {p === undefined ? <p className="soluk" style={{ margin: 0 }}>Yükleniyor…</p>
         : !p || p.santraller.length === 0 ? <p className="soluk" style={{ margin: 0 }}>Bu hesapta santral yok.</p>
         : (
          <div className="grafik-kaydir">
            <table className="veri" style={{ fontSize: 12.5 }}>
              <thead><tr><th>Santral</th><th>kWp</th><th>Segment</th><th>Son ölçüm</th><th>WMAPE 30g</th><th>Bugün</th><th>Yarın</th><th>Alarm</th><th>Son koşu</th></tr></thead>
              <tbody className="mono">
                {p.santraller.map((r) => (
                  <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => onSec(r.id)} tabIndex={0}
                      onKeyDown={(e) => { if (e.key === "Enter") onSec(r.id); }}>
                    <td style={{ fontWeight: 600 }}>{r.ad}</td><td>{sayiTr(r.kapasite_kwp)}</td><td>{r.segment ?? "—"}</td>
                    <td style={{ color: r.kesinti_gun != null && r.kesinti_gun > 2 ? "var(--uyari)" : undefined }}>{tarih(r.son_olcum)}{r.kesinti_gun != null && r.kesinti_gun > 2 ? ` (${sayiTr(r.kesinti_gun)} g)` : ""}</td>
                    <td>{r.wmape_30g != null ? `%${sayiTr(r.wmape_30g, 1)}` : "—"}</td><td>{kwhYaz(r.bugun_kwh)}</td><td>{kwhYaz(r.yarin_kwh)}</td>
                    <td style={{ color: r.acik_alarm > 0 ? "var(--uyari)" : undefined }}>{sayiTr(r.acik_alarm)}</td><td>{tarih(r.son_kosu)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="soluk" style={{ fontSize: 12.5, margin: "10px 0 0" }}>
          Bugün/yarın = gün başlamadan verilmiş koşunun günlük P50 toplamı (forecast_daily); WMAPE = son 30 günün 0–24 saat karnesi;
          alarm = son 7 günde okunmamış kayıt. Hiyerarşik uzlaştırma (portföy toplamının santral tahminleriyle tutarlı hale getirilmesi) sonraki dalga.
        </p>
      </Kart>
    </Sayfa>
  );
}
