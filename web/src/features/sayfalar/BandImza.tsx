/** v2.290 — "Çift Yüz" imza motifi: gün boyu P10–P90 bandı + P50 çizgisi (mavi = tahmin
 *  ailesi) ve güne kadar gelen gerçekleşen (amber). Grafik anayasasının kendisi marka
 *  görseli olur: giriş ekranı, boş durumlar, rapor kapakları hep aynı çizim.
 *  Renkler CSS değişkenlerinden gelir → iki yüzde de doğru mürekkep. */
export function BandImza({ yukseklik = 96, etiketli = false }: { yukseklik?: number; etiketli?: boolean }) {
  return (
    <div>
      <svg viewBox="0 0 420 100" preserveAspectRatio="none" aria-hidden="true"
           style={{ width: "100%", height: yukseklik, display: "block" }}>
        <defs>
          <linearGradient id="bandimza-dolgu" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-band-future-edge, #2D6FB5)" stopOpacity=".30" />
            <stop offset="100%" stopColor="var(--chart-band-future-edge, #2D6FB5)" stopOpacity=".03" />
          </linearGradient>
        </defs>
        {/* P90 üst kenar → P10 alt kenar (kapalı bant) */}
        <path d="M8,92 C70,88 105,18 160,10 C215,2 250,4 300,16 C348,27 385,86 412,92
                 L412,92 C384,88 350,42 300,32 C252,23 214,20 160,27 C108,34 72,90 8,92 Z"
              fill="url(#bandimza-dolgu)" />
        <path d="M8,92 C70,88 105,18 160,10 C215,2 250,4 300,16 C348,27 385,86 412,92"
              fill="none" stroke="var(--chart-band-future-edge, #2D6FB5)" strokeWidth="1" opacity=".55" />
        <path d="M8,92 C72,90 108,34 160,27 C214,20 252,23 300,32 C350,42 384,88 412,92"
              fill="none" stroke="var(--chart-band-future-edge, #2D6FB5)" strokeWidth="1" opacity=".55" />
        {/* P50 */}
        <path d="M8,92 C71,89 106,26 160,18 C214,11 251,13 300,24 C349,34 384,86 412,92"
              fill="none" stroke="var(--chart-p50-future, #2D6FB5)" strokeWidth="2" />
        {/* gerçekleşen: güne kadar (x≈232'de biter), P50'ye yakın ama kendi hâlinde */}
        <path d="M8,92 C70,90 108,30 160,21 C196,15 216,14 232,16"
              fill="none" stroke="var(--chart-actual, #E8940A)" strokeWidth="2" strokeLinecap="round" />
        <circle cx="232" cy="16" r="3" fill="var(--chart-actual, #E8940A)" />
        <line x1="232" y1="24" x2="232" y2="94" stroke="var(--chart-actual, #E8940A)"
              strokeWidth="1" strokeDasharray="2 4" opacity=".5" />
      </svg>
      {etiketli && (
        <div className="mono" style={{ fontSize: 10.5, letterSpacing: ".05em", color: "var(--soluk)",
                                       display: "flex", gap: 14, marginTop: 6 }}>
          <span><i style={{ display: "inline-block", width: 14, height: 3, borderRadius: 2, verticalAlign: 2,
                            background: "var(--chart-p50-future, #2D6FB5)", marginRight: 5 }} />P10–P90 aralığıyla tahmin</span>
          <span><i style={{ display: "inline-block", width: 14, height: 3, borderRadius: 2, verticalAlign: 2,
                            background: "var(--chart-actual, #E8940A)", marginRight: 5 }} />şu ana dek gerçekleşen</span>
        </div>
      )}
    </div>
  );
}
