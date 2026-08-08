from pvq import *

SOZLUK = [
    ("P50 · P10 · P90",
     "Sırasıyla %50, %10 ve %90 olasılıkla aşılan üretim değerleri. P50 en olası senaryodur; "
     "P10–P90 aralığı %80'lik güven aralığıdır."),
    ("Naif referans",
     "Hiç model kullanmadan elde edilebilecek tahmin: güneşin açısına göre ölçeklenmiş “dün ne "
     "olduysa bugün de o olur” yöntemi. Kazanç bu referansa göre ölçülür."),
    ("Kalibrasyon",
     "Fizik modelinin santralin kendi geçmiş üretimiyle ayarlanması. Sistem verimi ve bifacial "
     "kazanç bu adımda bulunur."),
    ("Bağımsız test (holdout)",
     "Kalibrasyonda hiç kullanılmayan son dönem verisi. Modelin ezberleyip ezberlemediği "
     "burada ölçülür."),
    ("Bifacial kazanç",
     "Çift yüzeyli panellerde arka yüzeyin zeminden yansıyan ışıkla ürettiği ek enerji."),
    ("Kapsama",
     "Kalite süzgecini geçen saatlerin toplam saate oranı. Düşük kapsama, ölçümün değil "
     "veri akışının sorunudur."),
    ("Kalite bayrağı",
     "Santral verisindeki şüpheli kayıtlara konan işaret. Bayraklı saatler hiçbir hesaba "
     "katılmaz."),
    ("İklim zarfı",
     "Bir ayın geçmiş yıllardaki dağılımı. Bir ayın iyi mi kötü mü geçtiği ancak bu zarfa "
     "göre söylenebilir."),
]

REFERANS = [
    ("IEC 61724-1", "Fotovoltaik sistem performansının izlenmesi — ölçüm ve raporlama "
     "standardı."),
    ("IEA-PVPS Task 13", "Fotovoltaik sistemlerde performans, güvenilirlik ve belirsizlik "
     "raporlama kılavuzları."),
    ("EPRI Solar Forecast Arbiter", "Güneş üretim tahminlerinin doğrulanması ve kazanç "
     "puanının tanımı."),
    ("pvlib", "Fotovoltaik sistem modellemesi için açık kaynaklı hesap kütüphanesi."),
    ("open-meteo", "Saatlik hava tahmini kaynağı."),
]

soz = "".join('<tr><td class="tr">%s</td><td>%s</td></tr>' % s for s in SOZLUK)
ref = "".join('<tr><td class="tr">%s</td><td>%s</td></tr>' % r for r in REFERANS)

CSS = """
h2{font-size:10.5pt;font-weight:600;padding-bottom:1.8mm;border-bottom:.9pt solid BRAND;
  margin-top:4mm}
table{margin-top:2.5mm}
td{font-size:8.2pt;padding:.9mm 2.5mm .9mm 0;vertical-align:top;line-height:1.45;
  border-bottom:.6pt solid #E8EDEA}
td.tr{font-weight:600;width:42mm}
tr:nth-child(even) td{background:none}
.yasal{margin-top:3mm}
.yasal h3{font-size:8.8pt;font-weight:600;margin-top:3mm}
.yasal h3:first-child{margin-top:0}
.yasal p{font-size:8.1pt;line-height:1.45;color:#2B3532;margin-top:1.2mm}
.kunye{display:flex;margin-top:6mm;border-top:1pt solid BRAND;border-bottom:.6pt solid RULE}
.kunye div{flex:1;padding:2.8mm 0 2.8mm 5mm;border-left:.6pt solid RULE}
.kunye div:first-child{padding-left:0;border-left:0}
.kunye b{display:block;font-size:7.4pt;letter-spacing:.09em;text-transform:uppercase;color:SEC}
.kunye span{display:block;font-size:8.6pt;font-weight:600;margin-top:1.2mm}
""".replace("BRAND", BRAND).replace("RULE", RULE).replace("SEC", SEC)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">EK-B</div>
  <h1>Sözlük, referanslar ve yasal bilgi</h1>

  <h2>Sözlük</h2>
  <table>""" + soz + """</table>

  <h2>Referanslar ve kaynaklar</h2>
  <table>""" + ref + """</table>

  <h2>Yasal bilgi</h2>
  <div class="yasal">
    <h3>Kullanım</h3>
    <p>Bu rapor, adına düzenlendiği müşteri tarafından serbestçe kullanılabilir; üretim ve atıf
    bilgileri korunmak kaydıyla üçüncü taraflarla paylaşılabilir.</p>

    <h3>Feragat</h3>
    <p>Tahminler olasılıksaldır: gerçekleşen üretimin P10–P90 aralığının dışına çıkma olasılığı
    tanım gereği %20'dir. İklim değişkenliği ile model ve ölçüm belirsizlikleri nedeniyle
    verilerin doğruluğu konusunda garanti verilemez. Kısa pencereli doğruluk karneleri mevsimsel
    yanlılık taşıyabilir. Bu rapor yatırım tavsiyesi değildir; finansman kararlarında bağımsız
    teknik değerlendirme esastır.</p>

    <h3>Atıf</h3>
    <p>Kaynak şu biçimde anılmalıdır: “PVQuant © 2026 — Üretim Tahmini ve Doğruluk Raporu”.</p>
  </div>

  <div class="kunye">
    <div><b>Rapor kimliği</b><span>{{RAPOR_ID}}</span></div>
    <div><b>Hazırlanma</b><span>4 Ağustos 2026 · 08:00</span></div>
    <div><b>Model</b><span>MOD C · Hibrit</span></div>
    <div><b>İletişim</b><span>{{EPOSTA}}</span></div>
  </div>
""" + foot(16) + """
</div></div>"""

build("PVQuant_Konya_GES_s16_ek_b", CSS, BODY,
      "PVQuant — Konya GES · EK-B Sözlük ve yasal bilgi")
