from pvq import *

tr = lambda x, d=1: ("%.*f" % (d, x)).replace(".", ",").replace("-", "\u2212")

from veri import EGITIM_SERIT
from veri import (KALITE_AYLAR as AYLAR, KALITE_GECERLI as GECERLI,
                  KALITE_HATALI as HATALI, KALITE_DIGER as DIGER, BAYRAK)


def kapsama(W=1000, H=290, ml=58, mb=52, fs=14):
    MR, MT = 14, 26
    PW, PH = W - ml - MR, H - MT - mb
    n = len(AYLAR)
    slot = PW / n
    bw = slot * .5
    cx = lambda i: ml + slot * (i + .5)
    y = lambda v: MT + PH * (100 - v) / 100
    o = []
    for t in range(0, 101, 25):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (ml, y(t), W - MR, y(t), GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%%%d</text>' % (ml - 9, y(t) + fs * .34, fs, t))
    for i in range(n):
        x0 = cx(i) - bw / 2
        if GECERLI[i] is None:               # c5/3: verisiz ay yutulmaz, dürüstçe söylenir
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-style="italic" fill="#8A949A">veri yok</text>'
                     % (cx(i), y(50) + fs * .34, fs))
            continue
        alt = 0
        for deger, renk in ((GECERLI[i], "#5A6A73"), (HATALI[i], AMBER), (DIGER[i], "#C9D1D5")):
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x0, y(alt + deger), bw, y(alt) - y(alt + deger), renk))
            alt += deger
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="600" fill="#fff">%%%d</text>'
                 % (cx(i), y(GECERLI[i] / 2) + fs * .34, fs, GECERLI[i]))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.8" '
             'stroke-dasharray="7 5"/>' % (ml, y(80), W - MR, y(80), "#2B3439"))
    lx = ml + slot * 4                      # Mayıs ile Haziran sütunları arasındaki boşluk
    o.append('<rect x="%.1f" y="%.1f" width="62" height="19" fill="#fff"/>'
             % (lx - 31, y(80) - 21))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="#2B3439">hedef %%80</text>' % (lx, y(80) - 7, fs))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.5"/>'
             % (ml, y(0), W - MR, y(0)))
    for i, ad in enumerate(AYLAR):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                 % (cx(i), y(0) + fs * 1.5, fs, ad))
    o.append('<text transform="translate(13,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">Saatlerin '
             'payı [%%]</text>' % (MT + PH / 2, fs + 1, INK))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Aylik gecerli saat payi">%s</svg>' % (W, H, "".join(o)))


rows = "".join('<tr><td class="ad">%s</td><td class="num">%s</td><td class="num">%s</td>'
               '<td class="ak">%s</td></tr>' % b for b in BAYRAK)

CSS = """
.fig{margin-top:5mm}
.split{display:flex;margin-top:5mm;border:.6pt solid RULE}
.split div{padding:3.2mm 4mm}
.split .egitim{flex:80;background:#E7F2F6}
.split .test{flex:20;background:BRAND;color:#fff}
.split b{display:block;font-size:8.6pt;font-weight:600;letter-spacing:.06em}
.split span{display:block;font-size:8.2pt;margin-top:.8mm}
.split .egitim span{color:SEC}
.split .test span{opacity:.85}
.tarih{display:flex;justify-content:space-between;font-size:8pt;color:SEC;margin-top:1.5mm}
.tarih i{font-style:normal}
.two{display:flex;gap:11mm;margin-top:6mm}
.two > div{flex:1}
.two h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-bottom:3mm}
.two p{font-size:9pt;line-height:1.55;margin-top:0}
.tcap{font-size:8pt;font-weight:600;margin-top:6mm}
.tcap span{font-weight:500;color:INK}
table{margin-top:2.5mm}
th{font-size:7.9pt;padding:1.8mm 2.5mm}
th.num, td.num{text-align:right}
td{font-size:8.4pt;padding:1.6mm 2.5mm}
td.ad{font-weight:600;width:38mm}
td.num{font-variant-numeric:tabular-nums;width:16mm}
td.ak{color:#2B3532}
.legend i.g{display:inline-block;width:4mm;height:2.8mm;background:#5A6A73;margin-right:1.6mm;
  vertical-align:-.4mm}
.legend i.h{display:inline-block;width:4mm;height:2.8mm;background:AMBER;margin-right:1.6mm;
  vertical-align:-.4mm}
.legend i.d{display:inline-block;width:4mm;height:2.8mm;background:#C9D1D5;margin-right:1.6mm;
  vertical-align:-.4mm}
""".replace("BRAND", BRAND).replace("AMBER", AMBER).replace("RULE", RULE) \
   .replace("SEC", SEC).replace("INK", INK)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Kalibrasyon · devam</div>
  <h1>Bağımsız test ve veri kalitesi</h1>
  <p class="lead" style="max-width:162mm">Bir modelin başarımı, kendisini eğittiği veriyle
  ölçülemez. Bu bölüm iki soruyu yanıtlar: model hiç görmediği veride ne yaptı, ve bu ölçümü
  besleyen santral verisi ne kadar sağlam?</p>

  <div class="split">
    <div class="egitim"><b>EĞİTİM — ilk %80</b>
      <span>96 gün · katsayılar bu dönemden bulundu</span></div>
    <div class="test"><b>TEST — son %20</b>
      <span>24 gün · modelin hiç görmediği</span></div>
  </div>
  <div class="tarih">""" + EGITIM_SERIT + """</div>
  <div class="figcap" style="margin-top:2.5mm"><b>Şekil 10.1</b>&nbsp;&nbsp;120 günlük pencere
    kronolojik olarak bölünür. Rastgele bölme bilinçli olarak kullanılmaz: rastgelelik, test
    dönemine eğitim dönemiyle aynı hava koşullarını sızdırır ve başarımı yapay biçimde şişirir.
    Kronolojik bölmede test dönemi gerçek bir gelecektir. {{NARR_S10_SEKIL1}}</div>

  """ + kapsama() + """
    <div class="legend"><span><i class="g"></i>Kalite süzgecini geçen saatler</span>
      <span><i class="h"></i>{{LEJANT_HATALI}}</span>
      <span><i class="d"></i>Diğer bayraklar</span></div>
    <div class="figcap"><b>Şekil 10.2</b>&nbsp;&nbsp;{{NARR_S10_SEKIL}}</div>

  <div class="tcap">Çizelge 10.1 <span>Kalite bayrakları — tüm arşiv: {{ARSIV_ETIKET}}</span></div>
  <table>
    <tr><th>Bayrak</th><th class="num">Saat</th><th class="num">Pay</th><th>Ne yapılmalı</th></tr>
    """ + rows + """
  </table>
""" + foot(10) + """
</div></div>"""

build("PVQuant_Konya_GES_s10_veri_kalitesi", CSS, BODY,
      "PVQuant — Konya GES · Bağımsız test ve veri kalitesi")
