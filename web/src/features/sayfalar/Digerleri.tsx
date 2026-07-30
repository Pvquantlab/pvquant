import { Kart, Sayfa, Kpi, sayiTr } from "./parcalar";

export function VeriYukleme() {
  const yol = (ad: string, bant: string, alt: string, maddeler: string[], onerilen = false) => (
    <Kart baslik={ad} sag={onerilen ? <span className="rozet rozet-ok">Önerilen</span> : undefined}>
      <div className="mono" style={{ fontSize: 30, letterSpacing: "-0.03em",
        color: onerilen ? "var(--marka)" : "var(--metin)" }}>{bant}</div>
      <div style={{ fontSize: 12.5, color: "var(--soluk)", marginBottom: 16 }}>{alt}</div>
      <ul style={{ fontSize: 13, color: "var(--ikincil)", paddingLeft: 17,
                   margin: 0, lineHeight: 2 }}>
        {maddeler.map((m) => <li key={m}>{m}</li>)}
      </ul>
      <button className={onerilen ? "dugme dugme-ana" : "dugme"}
        style={{ width: "100%", marginTop: 18 }}>
        {onerilen ? "Kalibre tahmine geç" : "Hızlı tahminle devam et"}
      </button>
    </Kart>
  );
  return (
    <Sayfa baslik="Veri yükleme"
      alt="Tahmin yolunuzu seçin — SCADA veriniz varsa kalibre tahmine geçin.">
      <div className="ızgara" style={{ gridTemplateColumns: "repeat(2, minmax(0,1fr))",
                                       maxWidth: 900 }}>
        {yol("Hızlı tahmin", "%5–10", "beklenen yıllık enerji sapması",
          ["Veri yüklemeden, saniyeler içinde sonuç",
           "Profesyonel meteoroloji verisiyle",
           "Dilediğiniz an kalibre tahmine yükseltin"])}
        {yol("Kalibre tahmin", "%1–3", "beklenen yıllık enerji sapması",
          ["Model geçmiş üretiminize uyarlanır",
           "Panel yönü bilinmiyorsa varsayılan kullanılır",
           "En az 3 ay SCADA — önerilen 12 ay"], true)}
      </div>
      <p style={{ fontSize: 12.5, color: "var(--soluk)", marginTop: 16, maxWidth: 900 }}>
        Veriniz azsa endişelenmeyin: 3 aydan kısa veri bulursak sizi engellemeyiz,
        hızlı tahminle başlatıp sonra yükseltmenizi öneririz.
      </p>
    </Sayfa>
  );
}

export function Kalibrasyon() {
  const sr = (a: string, b: string) => <tr key={a}><td>{a}</td><td className="mono">{b}</td></tr>;
  return (
    <Sayfa baslik="Kalibrasyon"
      alt="Model, santralinizin kendi verisiyle uyarlanır — kanıtı bu sayfada görürsünüz."
      sag={<button className="dugme">Yeniden kalibre et</button>}>
      <div className="ızgara satir-3" style={{ marginBottom: 14 }}>
        <Kpi etiket="Holdout WMAPE · hibrit" deger="%30,1" alt="kronolojik son %20 sınavı" />
        <Kpi etiket="Fizik · aynı sınav" deger="%38,7" alt="karşılaştırma tabanı" />
        <Kpi etiket="İyileşme" deger="%22" alt="hibrit kapıyı geçti" />
      </div>
      <div className="ızgara" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)" }}>
        <Kart baslik="Bulduklarımız">
          <table className="veri"><tbody>
            {sr("η_BoS", "0,927")}
            {sr("BG (bifasyal kazanç)", "0,186")}
            {sr("Eğim / azimut", "20° / 180° (varsayılan)")}
            {sr("Geçerli saat", sayiTr(4272))}
            {sr("Kalibrasyon tarihi", "29 Tem 2026")}
          </tbody></table>
        </Kart>
        <Kart baslik="Yıllık enerji sapması">
          <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
            <span className="mono" style={{ fontSize: 22, color: "var(--soluk)" }}>%0,35</span>
            <span style={{ color: "var(--soluk)" }}>→</span>
            <span className="mono" style={{ fontSize: 30, letterSpacing: "-0.03em" }}>%1,65</span>
          </div>
          <p style={{ fontSize: 12.5, color: "var(--soluk)", margin: "14px 0 0" }}>
            Fizik → hibrit. Bu sayı kalibrasyon dönemindeki sistematik sapmadır;
            saatlik tahmin isabeti Doğruluk sayfasında ölçülür.
          </p>
        </Kart>
      </div>
    </Sayfa>
  );
}

export function Raporlar() {
  const kartlar = [
    ["PDF", "Yönetici özeti — logo, KPI'lar, holdout kutusu"],
    ["Excel", "Tam veri — saatlik tablo, özet ve metadata"],
    ["JSON", "API formatı — şema 1.1.0, entegrasyona hazır"],
  ];
  const kosular = [["30.07.2026 12:58","C","Hibrit"],["30.07.2026 00:42","C","Hibrit"],
    ["30.07.2026 00:30","C","Hibrit"],["29.07.2026 20:27","C","Hibrit"],
    ["28.07.2026 21:49","B","Fizik"]];
  return (
    <Sayfa baslik="Raporlar"
      alt="Hepsi tahmin arşivinden üretilir — koşular güncellenmez, yenisi eklenir.">
      <div className="ızgara satir-3" style={{ marginBottom: 14 }}>
        {kartlar.map(([ad, alt]) => (
          <Kart key={ad} baslik={ad}>
            <div style={{ fontSize: 13, color: "var(--ikincil)", minHeight: 38 }}>{alt}</div>
            <button className="dugme" style={{ width: "100%", marginTop: 14 }}>Hazırla</button>
          </Kart>
        ))}
      </div>
      <Kart baslik="Geçmiş koşular">
        <table className="veri">
          <thead><tr><th>Tarih</th><th>Mod</th><th>Model</th></tr></thead>
          <tbody className="mono">
            {kosular.map((r) => (
              <tr key={r[0]}><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>
            ))}
          </tbody>
        </table>
      </Kart>
    </Sayfa>
  );
}
