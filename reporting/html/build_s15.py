from pvq import *

METRIK = [
    ("Özgül üretim", "yıllık üretim ÷ kurulu DC güç", "kWh/kWp", "IEC 61724-1", "sayfa 11"),
    ("Kapasite faktörü", "üretim ÷ (şebeke gücü × takvim saati)", "%", "—", "sayfa 3"),
    ("Ortalama mutlak hata (MAE)", "|tahmin − gerçekleşen| değerlerinin ortalaması", "MW",
     "—", "sayfa 8"),
    ("Ağırlıklı hata (WMAPE)", "Σ|tahmin − gerçekleşen| ÷ Σ gerçekleşen", "%",
     "IEA-PVPS T13", "sayfa 3, 7"),
    ("Ortalama yüzde hata (MAPE)", "hata oranlarının ortalaması", "%", "—", "sayfa 9, 10"),
    ("Kazanç (skill)", "1 − (tahmin hatası ÷ naif referans hatası)", "%",
     "EPRI Forecast Arbiter", "sayfa 7"),
    ("Aşılma olasılığı (Pxx)", "P90 = P50 − 1,28 × standart sapma", "MWh",
     "IEA-PVPS T13", "sayfa 11"),
    ("Kapsama", "kalite süzgecini geçen saat ÷ toplam saat", "%", "IEC 61724-1", "sayfa 10"),
    ("Değişkenlik katsayısı (CV)", "standart sapma ÷ ortalama", "%", "—", "sayfa 11"),
]

BUTCE = [
    ("Hava belirsizliği", "Olasılık aralıkları kantil yöntemiyle üretilir; dağılım varsayımı "
     "kullanılmaz.", "Sayfa 4, 5"),
    ("Model katsayıları", "Bağımsız test (holdout) ile ölçülür; katsayılar fiziksel aralık "
     "denetiminden geçer.", "Sayfa 9, 10"),
    ("Ölçüm belirsizliği", "Kalite bayraklı saatler hiçbir hesaba girmez; kapsama oranı "
     "raporlanır.", "Sayfa 10"),
    ("İklimsel değişkenlik", "19 tam yılın değişkenlik katsayısı (%5,5) yıllık Pxx eğrisine "
     "girdi olur.", "Sayfa 11"),
]

KISALTMA = [
    ("CV", "Değişkenlik katsayısı"),
    ("DC / AC", "Doğru akım (panel) / alternatif akım (şebeke)"),
    ("EPRI", "Electric Power Research Institute"),
    ("GES", "Güneş enerjisi santrali"),
    ("IEA-PVPS", "Uluslararası Enerji Ajansı PV programı"),
    ("IEC 61724-1", "Fotovoltaik performans izleme standardı"),
    ("MAE", "Ortalama mutlak hata"),
    ("MAPE", "Ortalama mutlak yüzde hata"),
    ("MWp / MWe", "Panel tepe gücü / şebeke gücü"),
    ("P10 · P50 · P90", "%10 / %50 / %90 aşılma olasılığı"),
    ("SCADA", "Santral telemetrisi; gerçekleşen üretim kaynağı"),
    ("WMAPE", "Üretimle ağırlıklandırılmış yüzde hata"),
]

met = "".join('<tr><td class="ad">%s</td><td class="fm">%s</td><td class="br">%s</td>'
              '<td>%s</td><td class="sy">%s</td></tr>' % m for m in METRIK)
but = "".join('<tr><td class="ad">%s</td><td>%s</td><td class="sy">%s</td></tr>' % b
              for b in BUTCE)
yarim = len(KISALTMA) // 2
kis = "".join('<tr><td class="kk">%s</td><td class="kv">%s</td>'
              '<td class="kk">%s</td><td class="kv">%s</td></tr>'
              % (KISALTMA[i] + KISALTMA[i + yarim]) for i in range(yarim))

CSS = """
h2{font-size:10.5pt;font-weight:600;padding-bottom:1.8mm;border-bottom:.9pt solid BRAND;
  margin-top:5.5mm}
table{margin-top:3mm}
th{font-size:7.8pt;padding:1.6mm 2.5mm}
td{font-size:8.2pt;padding:1.25mm 2.5mm;vertical-align:top}
td.ad{font-weight:600;width:46mm}
td.fm{width:62mm;color:#2B3532}
td.br{width:14mm;text-align:center}
td.sy{width:24mm;color:SEC}
.kls{margin-top:3mm}
.kls td{font-size:8.2pt;line-height:1.4;padding:1.25mm 2mm 1.25mm 0;
  border-bottom:.6pt solid #E8EDEA;vertical-align:top}
.kls td.kk{font-weight:600;width:26mm}
.kls td.kv{color:#2B3532;width:61mm;padding-right:8mm}
.kls tr:nth-child(even) td{background:none}
""".replace("BRAND", BRAND).replace("SEC", SEC)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">EK-A</div>
  <h1>Metrikler, belirsizlik ve kısaltmalar</h1>
  <p class="lead" style="max-width:162mm">Raporda geçen her ölçütün nasıl hesaplandığı, hangi
  çerçeveden geldiği ve hangi sayfada kullanıldığı. Formüller değişmez.</p>

  <h2>Ölçütler</h2>
  <table>
    <tr><th>Ölçüt</th><th>Nasıl hesaplanır</th><th>Birim</th><th>Çerçeve</th><th>Nerede</th></tr>
    """ + met + """
  </table>

  <h2>Belirsizlik bütçesi</h2>
  <table>
    <tr><th>Kaynak</th><th>Nasıl ölçülür ve sınırlanır</th><th>Nerede</th></tr>
    """ + but + """
  </table>

  <h2>Kısaltmalar</h2>
  <table class="kls">""" + kis + """</table>
""" + foot(15) + """
</div></div>"""

build("PVQuant_Konya_GES_s15_ek_a", CSS, BODY,
      "PVQuant — Konya GES · EK-A Metrikler")
