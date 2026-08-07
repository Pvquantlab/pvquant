from pvq import *

CSS = """
.cards{display:flex;flex-wrap:wrap;gap:4mm;margin-top:7mm}
.card{width:40.5mm;border-top:1.8pt solid #9AA5A0;padding-top:2.6mm}
.card.ok{border-top-color:OK}
.card.watch{border-top-color:AMBER}
.card .lb{font-size:7.8pt;font-weight:600;letter-spacing:.075em;text-transform:uppercase;
  color:INK;line-height:1.35;min-height:7.5mm}
.card .val{font-family:SourceSerif,Georgia,serif;font-weight:600;line-height:1.02;
  letter-spacing:-.012em;margin-top:1.6mm}
.card .val u{text-decoration:none;font-family:PlexSans;font-size:8.6pt;font-weight:500;
  color:SEC;padding-left:1.1mm}
.card .nt{font-size:7.8pt;color:SEC;line-height:1.42;margin-top:1.6mm}

.thr{display:flex;align-items:center;gap:7mm;margin-top:5mm;padding-top:3mm;
  border-top:.6pt solid RULE;font-size:8pt;color:INK}
.thr span{display:inline-flex;align-items:center}
.thr i{display:inline-block;width:3.4mm;height:2.2mm;margin-right:1.6mm}
.thr .g{background:OK}.thr .a{background:AMBER}.thr .r{background:RED}
.thr .sp{margin-left:auto}

h2{font-size:11pt;font-weight:600;margin-top:8mm;padding-bottom:2mm;
  border-bottom:.9pt solid BRAND}
.two{display:flex;gap:11mm;margin-top:4mm}
.two > div{flex:1}
.two p{font-size:9pt;line-height:1.56;margin-top:0}
.two p + p{margin-top:3.5mm}

.watchbox{background:#F4F5F6;border-left:1.8pt solid AMBER;padding:4mm 4.5mm;margin-top:6mm}
.watchbox h3{font-size:9.2pt;font-weight:600;color:AMBER;margin-bottom:1.6mm}
.watchbox p{font-size:8.6pt;line-height:1.52;margin:0}
""".replace("OK", OK).replace("BRAND2", BRAND2).replace("BRAND", BRAND).replace("AMBER", AMBER) \
   .replace("RED", RED).replace("RULE", RULE).replace("SEC", SEC).replace("INK", INK)

# (etiket, değer, birim, not, durum, punto)
KPI = [
    ("16 günlük toplam beklenti", "1.036,4", "MWh", "Aşılma olasılığı %50 olan değer", "", 17),
    ("%80 olasılık bandı", "1.005–1.068", "MWh", "Gerçekleşenin bu aralıkta kalma olasılığı %80", "ok", 14),
    ("Kapasite faktörü", "%27,0", "", "Şebeke gücünün dönem boyunca kullanılan oranı", "ok", 17),
    ("Gün-öncesi ortalama hata", "%9,4", "WMAPE", "Son 120 günün ortalaması · hedef %10 altı", "ok", 17),
    ("Basit referansa üstünlük", "%38", "skill", "Basit referans yönteme göre kazanılan isabet",
     "ok", 17),
    ("Bağımsız testte hata", "%8,9", "MAPE", "Modelin eğitimde görmediği veride · hedef %10 altı",
     "ok", 17),
    ("Kesintisiz doğrulama", "87", "gün", "Ara vermeden doğrulanan gün sayısı", "ok", 17),
    ("Santral verisi kapsaması", "%71", "", "Kalite süzgecini geçen saatlerin oranı · hedef %80 üstü", "watch", 17),
]

cards = "".join(
    '<div class="card %s"><div class="lb">%s</div>'
    '<div class="val" style="font-size:%spt">%s%s</div><div class="nt">%s</div></div>'
    % (st, lb, sz, val, ('<u>%s</u>' % unit if unit else ""), nt)
    for lb, val, unit, nt, st, sz in KPI)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Yönetici özeti</div>
  <h1>Bu dönemin bulguları</h1>
  <p class="lead" style="max-width:158mm">Önümüzdeki 16 gün için toplam üretim beklentisi
  <b>1.036,4 MWh</b>'tir ve %80 olasılıkla 1.005–1.068 MWh aralığında gerçekleşecektir.
  Gün-öncesi tahminler son 120 günde ortalama %9,4 hatayla çalışmış, basit bir referans yönteme
  göre %38 daha isabetli olmuştur. Takip edilmesi gereken tek kalem santral verisinin
  kapsamasıdır.</p>

  <div class="cards">""" + cards + """</div>

  <div class="thr">
    <span><i class="g"></i>hedefte</span>
    <span><i class="a"></i>izlemede</span>
    <span><i class="r"></i>eşik dışı</span>
  </div>

  <h2>Değerlendirme</h2>
  <div class="two">
    <div>
      <p><b>Belirsizlik dar.</b> Bant genişliği dönem genelinde günlük ±%6–8 düzeyindedir;
      yalnızca 11–13 Ağustos'ta beklenen cephe geçişi bandı genişletmektedir. 12 Ağustos'ta
      beklenti 53,6 MWh'e gerilemekte, belirsizlik ±9,7 MWh'e çıkmaktadır. Cephe sonrasında
      üretim mevsim normaline dönmektedir.</p>
      <p><b>İyileşme bağımsız veride doğrulandı.</b> Model, santralin kendi üretim verisiyle
      kalibre edildikten sonra hatayı %13,6'dan %8,9'a indirmiştir — %34,6 iyileşme. Bu ölçüm,
      modelin eğitimde hiç görmediği son dönem verisi üzerinde yapılmıştır.</p>
    </div>
    <div>
      <p><b>Doğrulama 87 gündür kesintisiz.</b> 120 günlük karne penceresinde yalnızca dört gün
      (21 ve 29 Nisan, 7–8 Mayıs) ölçüm eksikliği nedeniyle karne dışında kalmıştır. Bu günler
      hiçbir ortalamaya katılmamış, boş bırakılmıştır.</p>
      <p><b>Taahhüt için önerilen değer.</b> İşletme planlamasında bandın alt sınırı (P10)
      güvenli taahhüt seviyesi olarak kullanılabilir: 16 günlük dönem için 1.005 MWh. Günler
      kısmen bağımsız olduğundan dönem toplamındaki bant, günlük banttan dardır.</p>
    </div>
  </div>

  <div class="watchbox">
    <h3>İzleme kalemi · santral verisi kapsaması %71</h3>
    <p>Kalite süzgecini geçen saat oranı tüm arşivde %71'dir; hedef en az %80. Düşüşün
    tamamına yakını Mart–Mayıs döneminde kaynak dosyadaki bozuk bir yıl bloğundan
    kaynaklanmaktadır. Bu blok düzeltilip yeniden yüklendiğinde kapsama hedefin üzerine çıkar;
    Haziran'dan itibaren oran zaten %88–92 seviyesindedir. Ayrıntı ve aylık kırılım
    Bağımsız test ve veri kalitesi bölümündedir (sayfa 10).</p>
  </div>
""" + foot(3) + """
</div></div>"""

build("PVQuant_Konya_GES_s03_yonetici_ozeti", CSS, BODY,
      "PVQuant — Konya GES · Yönetici özeti")
