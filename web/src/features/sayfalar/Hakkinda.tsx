import { useEffect, useState } from "react";
import { api, bellektenOku, ayniysaEskisi } from "../../api/client";
import type { Hakkinda as HakkindaT, KuralTablosu } from "../../api/types";
import { Kart, Sayfa, sayiTr, YerTutucu } from "./parcalar";

/** v2.270 (Dalga 0) — Hakkında › Veri kaynakları ve lisanslar.
 *  Gizlilik Anayasası v2.245 istisnası: kaynak adı + lisans bağlantısı YALNIZ burada (ve rapor künyesi, README).
 *  Liste sunucunun gerçek kullanımından gelir; kullanılmayan kaynağa atıf yazılmaz. */
export function Hakkinda() {
  // 24.10 açık tema geçiş turu: bayat-önce — bellekte son liste varsa dönüşte anında; yoldayken yer tutucu (metin yerine)
  const [h, setH] = useState<HakkindaT | null | undefined>(() => bellektenOku<HakkindaT>("/v1/hakkinda"));
  useEffect(() => { api.hakkinda().then((v) => setH((e) => (v ? ayniysaEskisi(e, v) : v))).catch(() => setH(null)); }, []);
  // v2.528 (P10, ENV-F04): uzlaştırma kuralı sürüm tablosu — API'de vardı (GET /v1/kurallar), panelde yoktu
  const [kurallar, setKurallar] = useState<KuralTablosu | null | undefined>(() => bellektenOku<KuralTablosu>("/v1/kurallar"));
  useEffect(() => { api.kurallar().then((v) => setKurallar((e) => (v ? ayniysaEskisi(e, v) : v))).catch(() => setKurallar(null)); }, []);
  const gunTr = (s: string | null) => s ? new Date(s + "T12:00:00").toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" }) : "—";
  const sayiMi = (v: number | null | undefined, nd = 2) => typeof v === "number" ? sayiTr(v, nd) : "—";
  const yonlu = (k: Record<string, number> | null) => k ? `${sayiMi(k.acik)} / ${sayiMi(k.fazla)}` : "—";   // sistem açığı / sistem fazlası (dengede ipucunda)
  const tarih = (s: string | null | undefined) => s ? new Date(s).toLocaleString("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—";
  const sol = { textAlign: "left" as const };
  const bag = { color: "var(--ikincil)", textDecoration: "underline", textUnderlineOffset: 2 };
  return (
    <Sayfa baslik="Hakkında" alt="Veri kaynakları, lisanslar ve işleme notu.">
      <Kart baslik="Veri kaynakları ve lisanslar">
        {h === undefined ? <YerTutucu yukseklik={120} />
         : !h ? <p className="soluk" style={{ margin: 0 }}>Örnek kip; kaynak listesi sunucudan gelir.</p> : (
          <>
            {h.uyarilar.length > 0 && <ul className="not-listesi uyari" style={{ margin: "0 0 10px" }}>{h.uyarilar.map((u) => <li key={u}>{u}</li>)}</ul>}
            <div className="grafik-kaydir">
              <table className="veri" style={{ fontSize: 13.5 }}>
                <thead><tr><th style={sol}>Kaynak</th><th style={sol}>Kurum</th><th style={sol}>Lisans</th><th style={sol}>Ne için</th></tr></thead>
                <tbody>
                  {h.kaynaklar.map((k) => (
                    <tr key={k.kimlik}>
                      <td style={{ ...sol, fontWeight: 600 }}><a href={k.veri_url} target="_blank" rel="noreferrer" style={bag}>{k.ad}</a></td>
                      <td style={sol}>{k.kurum}</td>
                      <td style={sol}><a href={k.lisans_url} target="_blank" rel="noreferrer" style={bag}>{k.lisans}</a></td>
                      <td className="soluk" style={sol}>{k.not}</td>
                    </tr>))}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: 13.5, margin: "12px 0 0", lineHeight: 1.55 }}>{h.yontem}</p>
          </>
        )}
      </Kart>
      {h && (h.mevzuat?.length ?? 0) > 0 && (
        <Kart baslik="Mevzuat ve standart dayanağı" sag={<span className="cip">katsayılar ayarlardan değişir</span>}>
          <div className="grafik-kaydir">
            <table className="veri" style={{ fontSize: 13.5 }}>
              <thead><tr><th style={sol}>Dayanak</th><th style={sol}>Kapsam</th><th style={sol}>Not</th></tr></thead>
              <tbody>
                {h.mevzuat!.map((m) => (
                  <tr key={m.ad}>
                    <td style={{ ...sol, fontWeight: 600, whiteSpace: "nowrap" }}>{m.ad}</td>
                    <td style={sol}>{m.kapsam}</td>
                    <td className="soluk" style={sol}>{m.not}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
          <p className="soluk" style={{ fontSize: 14, margin: "10px 0 0" }}>
            Ürün bu çerçevenin tanımlarını uygular; madde numaraları yürürlükteki metne işaret eder.
            Mevzuat değişirse katsayılar koda gömülü olmadığından santral ayarından güncellenir.
          </p>
        </Kart>
      )}
      {kurallar && kurallar.satirlar.length > 0 && (
        <Kart baslik="Uzlaştırma kuralı sürüm tablosu" alt="Dengesizlik ve KGÜP sapma hesabında kullanılan katsayı ve parametrelerin geçerlilik dönemleri (lisanslı serbest piyasa); yeniden hesap bu tabloyla yapılır, EPİAŞ sonucu esastır"
          sag={<span className="cip">salt okunur · kaynak: kural motoru</span>}>
          <div className="grafik-kaydir">
            <table className="veri" style={{ fontSize: 13 }}>
              <thead><tr><th style={sol}>Geçerlilik</th><th style={sol}>Kural sürümü</th><th style={sol}>Rejim</th><th title="Dengesizlik katsayıları sistem yönüne göre (Karar 14030): sistem açığı / sistem fazlası; dengede ipucunda">k (açık / fazla)</th><th title="Sistem açığı / sistem fazlası">l (açık / fazla)</th><th title="Düşük fiyat eşiği (TL/MWh)">V</th><th title="KÜPST tolerans oranı (m) ve fiyat katsayısı (n; arıza eşiğinde n arıza)">KÜPST m / n</th><th title="DSG netleşme eşiği">DSG eşiği</th><th style={sol}>Dayanak</th></tr></thead>
              <tbody>
                {kurallar.satirlar.map((r) => (
                  <tr key={r.gecerlilik_bas}>
                    <td style={{ ...sol, whiteSpace: "nowrap" }}>{gunTr(r.gecerlilik_bas)} – {r.gecerlilik_bitis ? gunTr(r.gecerlilik_bitis) : "…"}{r.belirsiz_2027 ? <span className="rozet rozet-kucuk rozet-uyari" style={{ marginLeft: 6 }} title="1.1.2027 sonrası uygulama ayrıntıları henüz belirsiz (DUY m.110)">belirsiz</span> : null}</td>
                    <td style={sol}>{r.kural_surumu}</td>
                    <td style={sol}>{r.rejim}</td>
                    <td className="mono" title={r.k ? `dengede ${sayiMi(r.k.dengede)}` : undefined}>{yonlu(r.k)}</td>
                    <td className="mono" title={r.l ? `dengede ${sayiMi(r.l.dengede)}` : undefined}>{yonlu(r.l)}</td>
                    <td className="mono">{sayiMi(r.V, 0)}</td>
                    <td className="mono">{sayiMi(r.kupst.m, 2)} / {sayiMi(r.kupst.n, 2)}{r.kupst.n_ariza != null ? ` (${sayiTr(r.kupst.n_ariza, 2)})` : ""}</td>
                    <td className="mono">{sayiMi(r.dsg_esik, 2)}</td>
                    <td className="soluk" style={sol}>{r.edt_dayanak}{r.kupst.dayanak ? `; ${r.kupst.dayanak}` : ""}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
          <p className="soluk" style={{ fontSize: 14, margin: "10px 0 0" }}>Katsayılar Santralim › Santral ayarları'ndan değiştirilebilir; bu tablo yürürlükteki varsayılanları gösterir. Dış API: GET /v1/kurallar.</p>
        </Kart>
      )}
      {h && Object.keys(h.arsiv).length > 0 && (
        <Kart baslik="Meteoroloji arşivi" sag={<span className="cip">tahmin başına nokta serileri</span>}>
          <div className="grafik-kaydir">
            <table className="veri" style={{ fontSize: 13.5 }}>
              <thead><tr><th style={sol}>Kaynak</th><th style={sol}>Son indirme</th><th>Nokta</th><th>Satır</th><th style={sol}>Kapsam</th></tr></thead>
              <tbody>
                {Object.entries(h.arsiv).map(([k, v]) => (
                  <tr key={k}><td style={sol}>{k}</td><td className="mono" style={sol}>{tarih(v.son)}</td><td className="mono">{sayiTr(v.nokta)}</td><td className="mono">{sayiTr(v.satir)}</td>
                    <td className="mono" style={sol}>{tarih(v.ilk)} → {tarih(v.son_ts)}</td></tr>))}
              </tbody>
            </table>
          </div>
          <p className="soluk" style={{ fontSize: 14, margin: "10px 0 0" }}>
            Her gece hava tahmini verisi indirilir, santral noktaları çıkarılır ve saklanır; tahmin, kalibrasyon ve hava verisi
            tutarlılık denetimi aynı arşivden beslenir. Ham ızgara dosyaları tutulmaz.
          </p>
        </Kart>
      )}
    </Sayfa>
  );
}
