import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Hakkinda as HakkindaT } from "../../api/types";
import { Kart, Sayfa, sayiTr } from "./parcalar";

/** v2.270 (Dalga 0) — Hakkında › Veri kaynakları ve lisanslar.
 *  Gizlilik Anayasası v2.245 istisnası: kaynak adı + lisans bağlantısı YALNIZ burada (ve rapor künyesi, README).
 *  Liste sunucunun gerçek kullanımından gelir; kullanılmayan kaynağa atıf yazılmaz. */
export function Hakkinda() {
  const [h, setH] = useState<HakkindaT | null | undefined>(undefined);
  useEffect(() => { api.hakkinda().then(setH).catch(() => setH(null)); }, []);
  const tarih = (s: string | null | undefined) => s ? new Date(s).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";
  return (
    <Sayfa baslik="Hakkında" alt="Veri kaynakları, lisanslar ve işleme notu.">
      <Kart baslik="Veri kaynakları ve lisanslar">
        {h === undefined ? <p className="soluk" style={{ margin: 0 }}>Yükleniyor…</p>
         : !h ? <p className="soluk" style={{ margin: 0 }}>Örnek kip — kaynak listesi sunucudan gelir.</p> : (
          <>
            {h.uyarilar.length > 0 && <p style={{ color: "var(--uyari)", fontSize: 12.5, margin: "0 0 10px" }}>{h.uyarilar.join(" · ")}</p>}
            <div className="grafik-kaydir">
              <table className="veri" style={{ fontSize: 12.5 }}>
                <thead><tr><th>Kaynak</th><th>Kurum</th><th>Lisans</th><th>Not</th></tr></thead>
                <tbody>
                  {h.kaynaklar.map((k) => (
                    <tr key={k.kimlik}>
                      <td style={{ fontWeight: 600 }}><a href={k.veri_url} target="_blank" rel="noreferrer">{k.ad}</a></td>
                      <td>{k.kurum}</td>
                      <td><a href={k.lisans_url} target="_blank" rel="noreferrer">{k.lisans}</a></td>
                      <td className="soluk">{k.not}</td>
                    </tr>))}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: 12.5, margin: "12px 0 0", lineHeight: 1.55 }}>{h.yontem}</p>
          </>
        )}
      </Kart>
      {h && Object.keys(h.arsiv).length > 0 && (
        <Kart baslik="Meteoroloji arşivi" sag={<span className="cip">koşu başına nokta serileri</span>}>
          <div className="grafik-kaydir">
            <table className="veri" style={{ fontSize: 12.5 }}>
              <thead><tr><th>Kaynak</th><th>Son koşu</th><th>Nokta</th><th>Satır</th><th>Kapsam</th></tr></thead>
              <tbody className="mono">
                {Object.entries(h.arsiv).map(([k, v]) => (
                  <tr key={k}><td>{k}</td><td>{tarih(v.son)}</td><td>{sayiTr(v.nokta)}</td><td>{sayiTr(v.satir)}</td>
                    <td>{tarih(v.ilk)} → {tarih(v.son_ts)}</td></tr>))}
              </tbody>
            </table>
          </div>
          <p className="soluk" style={{ fontSize: 12.5, margin: "10px 0 0" }}>
            Her gece açık koşular indirilir, santral noktaları çıkarılır ve saklanır; tahmin, kalibrasyon ve eğitim/servis
            kayma denetimi aynı arşivden beslenir. Ham ızgara dosyaları tutulmaz.
          </p>
        </Kart>
      )}
    </Sayfa>
  );
}
