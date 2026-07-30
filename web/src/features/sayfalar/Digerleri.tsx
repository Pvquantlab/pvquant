import { Bolum, BosDurum } from "./parcalar";

export function VeriYukleme() {
  return (
    <>
      <h1 style={{ fontSize: 21, fontWeight: 600, margin: "0 0 4px", letterSpacing: "-0.02em" }}>Veri yükleme</h1>
      <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "0 0 22px" }}>
        Tahmin yolunuzu seçin — SCADA veriniz varsa kalibre tahmine geçin.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Bolum baslik="Hızlı tahmin">
          <div className="kpi-dg mono" style={{ marginBottom: 6 }}>%5–10</div>
          <div style={{ fontSize: 13, color: "var(--ikincil)", marginBottom: 14 }}>beklenen yıllık enerji sapması</div>
          <ul style={{ fontSize: 13, color: "var(--ikincil)", paddingLeft: 18, margin: 0, lineHeight: 1.8 }}>
            <li>Veri yüklemeden, saniyeler içinde</li>
            <li>Profesyonel meteoroloji verisiyle</li>
            <li>Dilediğiniz an yükseltin</li>
          </ul>
        </Bolum>
        <Bolum baslik="Kalibre tahmin" sag={<span className="rozet rozet-ok">Önerilen</span>}>
          <div className="kpi-dg mono" style={{ marginBottom: 6, color: "var(--marka)" }}>%1–3</div>
          <div style={{ fontSize: 13, color: "var(--ikincil)", marginBottom: 14 }}>beklenen yıllık enerji sapması</div>
          <ul style={{ fontSize: 13, color: "var(--ikincil)", paddingLeft: 18, margin: 0, lineHeight: 1.8 }}>
            <li>Model geçmiş üretiminize uyarlanır</li>
            <li>Panel yönü bilinmiyorsa varsayılan kullanılır</li>
            <li>En az 3 ay SCADA — önerilen 12 ay</li>
          </ul>
        </Bolum>
      </div>
    </>
  );
}

export function Kalibrasyon() {
  const satir = (a: string, b: string) => (
    <tr><td>{a}</td><td className="mono">{b}</td></tr>
  );
  return (
    <>
      <h1 style={{ fontSize: 21, fontWeight: 600, margin: "0 0 4px", letterSpacing: "-0.02em" }}>Kalibrasyon</h1>
      <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "0 0 22px" }}>
        Model, santralinizin kendi verisiyle uyarlanır — kanıtı bu sayfada görürsünüz.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Bolum baslik="Bulduklarımız">
          <table className="veri">
            <tbody>
              {satir("η_BoS", "0,927")}
              {satir("BG (bifasyal kazanç)", "0,186")}
              {satir("Eğim / azimut", "20° / 180° (varsayılan)")}
              {satir("Geçerli saat", "4.272")}
              {satir("Kalibrasyon tarihi", "29 Tem 2026")}
            </tbody>
          </table>
        </Bolum>
        <div style={{ display: "grid", gap: 16, alignContent: "start" }}>
          <Bolum baslik="Hibrit devrede">
            <table className="veri">
              <tbody>
                {satir("Holdout WMAPE", "%30,1")}
                {satir("Fizik (aynı sınav)", "%38,7")}
                {satir("İyileşme", "%22")}
              </tbody>
            </table>
          </Bolum>
          <Bolum baslik="Yıllık enerji sapması">
            <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
              <span className="mono" style={{ fontSize: 20, color: "var(--soluk)" }}>%0,35</span>
              <span style={{ color: "var(--soluk)" }}>→</span>
              <span className="mono" style={{ fontSize: 26, letterSpacing: "-0.02em" }}>%1,65</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--soluk)", marginTop: 8 }}>
              fizik → hibrit · saatlik isabet Doğruluk sayfasında ölçülür
            </div>
          </Bolum>
        </div>
      </div>
    </>
  );
}

export function Raporlar() {
  const kartlar = [
    { ad: "PDF", alt: "Yönetici özeti — logo, KPI'lar, holdout kutusu" },
    { ad: "Excel", alt: "Tam veri — saatlik tablo, özet ve metadata" },
    { ad: "JSON", alt: "API formatı — şema 1.1.0, entegrasyona hazır" },
  ];
  return (
    <>
      <h1 style={{ fontSize: 21, fontWeight: 600, margin: "0 0 4px", letterSpacing: "-0.02em" }}>Raporlar</h1>
      <p style={{ fontSize: 13, color: "var(--ikincil)", margin: "0 0 22px" }}>
        Hepsi tahmin arşivinden üretilir — koşular güncellenmez, yenisi eklenir.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 16 }}>
        {kartlar.map((k) => (
          <Bolum key={k.ad} baslik={k.ad}>
            <div style={{ fontSize: 13, color: "var(--ikincil)", minHeight: 40 }}>{k.alt}</div>
            <button className="tema-btn" style={{ width: "100%", marginTop: 12 }}>Hazırla</button>
          </Bolum>
        ))}
      </div>
      <Bolum baslik="Geçmiş koşular">
        <table className="veri">
          <thead><tr><th>Tarih</th><th>Mod</th><th>Model</th></tr></thead>
          <tbody className="mono">
            {[["30.07.2026 12:58", "C", "Hibrit"], ["30.07.2026 00:42", "C", "Hibrit"],
              ["30.07.2026 00:30", "C", "Hibrit"], ["29.07.2026 20:27", "C", "Hibrit"],
              ["28.07.2026 21:49", "B", "Fizik"]].map((r) => (
              <tr key={r[0]}><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>
            ))}
          </tbody>
        </table>
      </Bolum>
    </>
  );
}

export function Bekliyor({ ad }: { ad: string }) {
  return <BosDurum baslik={`${ad} henüz taşınmadı`}
    metin="Bu ekran Streamlit tarafında çalışıyor; React'e taşınması sırada." />;
}
