from pvq import *

tr = lambda x, d=1: ("%.*f" % (d, x)).replace(".", ",").replace("-", "\u2212")

# (etiket, değişim, tür)  tür: bas = başlangıç/bitiş, iyi = iyileştirme, kotu = bedel
from veri import SELALE_ADIM as ADIM, SELALE_BAS as BAS, SELALE_BIT as BIT


def selale(W=1000, H=352, ml=64, mb=88, fs=14):
    MR, MT = 14, 46
    PW, PH = W - ml - MR, H - MT - mb
    n = len(ADIM)
    # c1b (v2.105): eksen şelale seviyelerinden — kanonikte (BAS=13,6) 16'yı üretir
    _lvl, _run = [BAS, BIT], BAS
    for _a in ADIM:
        if _a[1] is None:                    # "Ham fizik" başlangıç sütunu
            continue
        _run += _a[1]
        _lvl.append(_run)
    ymax = int(-(-max(_lvl) // 4)) * 4          # ceil(max/4)*4
    adim_t = ymax // 4
    slot = PW / n
    bw = slot * .46
    cx = lambda i: ml + slot * (i + .5)
    y = lambda v: MT + PH * (ymax - v) / ymax
    o = []
    for t in range(0, ymax + 1, adim_t):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (ml, y(t), W - MR, y(t), GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%%%d</text>' % (ml - 9, y(t) + fs * .34, fs, t))

    kum = BAS
    seviye = []                       # her sütundan sonra kalan hata
    onceki = None
    for i, (ad, d, tip) in enumerate(ADIM):
        x0 = cx(i) - bw / 2
        if tip == "bas":
            v = BAS if i == 0 else BIT
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x0, y(v), bw, y(0) - y(v), BRAND))
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-weight="600" fill="%s">%%%s</text>'
                     % (cx(i), y(v) - 8, fs + 2, INK, tr(v)))
            ust = v
        else:
            hi, lo = max(kum, kum + d), min(kum, kum + d)
            renk = "#2B7B9B" if tip == "iyi" else AMBER
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="%s" '
                     'stroke-width="1"/>' % (x0, y(hi), bw, max(2.5, y(lo) - y(hi)), renk, renk))
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-weight="600" fill="%s">%s%s puan</text>'
                     % (cx(i), y(hi) - 8, fs, renk if tip == "kotu" else INK,
                        "+" if d > 0 else "", tr(d)))
            kum += d
            ust = kum
        seviye.append(ust)
        if onceki is not None:
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#9AA5AB" '
                     'stroke-width="1.4" stroke-dasharray="5 4"/>'
                     % (cx(i - 1) + bw / 2, y(onceki), x0, y(onceki)))
        onceki = ust

    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.5"/>'
             % (ml, y(0), W - MR, y(0)))
    for i, (ad, d, tip) in enumerate(ADIM):
        parts = ad.split(" ")
        if len(ad) > 13 and len(parts) > 1:
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                     % (cx(i), y(0) + fs * 1.5, fs, " ".join(parts[:-1])))
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                     % (cx(i), y(0) + fs * 2.6, fs, parts[-1]))
        else:
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-weight="500" fill="#2B3439">%s</text>'
                     % (cx(i), y(0) + fs * 1.5, fs, ad))
    # kalan hata satırı
    ry = y(0) + fs * 4.1
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#DDE3E6" stroke-width="1"/>'
             % (ml, ry - fs * .95, W - MR, ry - fs * .95))
    o.append('<text x="%.1f" y="%.1f" text-anchor="start" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="%s">kalan hata</text>' % (4, ry, fs - 1, INK))
    for i, v in enumerate(seviye):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="600" fill="#2B3439">%%%s</text>'
                 % (cx(i), ry, fs, tr(v)))

    o.append('<text transform="translate(13,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">Ortalama hata '
             '[%%]</text>' % (MT + PH / 2, fs + 1, INK))
    o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" font-weight="600" '
             'fill="%s">Net sonuç: %%{{FIZIK}} → %%{{HOLDOUT}} · %%{{IYILESME}} iyileşme</text>'
             % (ml, 16, fs + 2, INK))
    # grafiğin kendi lejantı
    lx = ml
    for k, (col, lab) in enumerate(((BRAND, "başlangıç ve sonuç"), ("#2B7B9B", "hatayı azaltan"),
                                    (AMBER, "hatayı artıran"))):
        o.append('<rect x="%.1f" y="%.1f" width="10" height="10" fill="%s"/>' % (lx, 28, col))
        o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" '
                 'font-weight="500" fill="#2B3439">%s</text>' % (lx + 14, 37, fs - 1, lab))
        lx += 26 + len(lab) * 6.4
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Kalibrasyon iyilesme selalesi">%s</svg>' % (W, H, "".join(o)))


KATSAYI = [
    ("Sistem verimi (η_BoS)", "0,942", "kablolama, inverter ve trafo zincirinin toplam etkisi"),
    ("Bifacial kazanç", "%7,3", "modüllerin arka yüzünden gelen ek üretim"),
    ("Kalibrasyonda kullanılan saat", "1.487", "kalite süzgecini geçen gündüz saati, 120 gün"),
    ("Kalibrasyon tarihi", "19 Temmuz 2026", "katsayıların son güncellenme tarihi"),
]

rows = "".join('<tr><td class="lb">%s</td><td class="val">%s</td></tr>'
               '<tr><td class="ac" colspan="2">%s</td></tr>' % k for k in KATSAYI)

CSS = """
.fig{margin-top:6mm}
.two{display:flex;gap:11mm;margin-top:7mm}
.two > div{flex:1}
.two h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-bottom:3mm}
.two p{font-size:9pt;line-height:1.56;margin-top:0}
.two p + p{margin-top:3mm}
table{margin-top:0}
td{padding:1.5mm 0;border:0}
td.lb{font-size:9pt;font-weight:500;letter-spacing:0;text-transform:none}
td.val{font-family:PlexSans;font-size:9pt;font-weight:600;text-align:right;white-space:nowrap;
  font-variant-numeric:tabular-nums;letter-spacing:0}
td.ac{font-size:8pt;color:SEC;padding-top:0;padding-bottom:2.6mm;
  border-bottom:.6pt solid #E8EDEA}
tr:nth-child(even) td{background:none}
.note{margin-top:6mm}
""".replace("BRAND", BRAND).replace("SEC", SEC)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Kalibrasyon</div>
  <h1>Fizikten hibrite: iyileşmenin kanıtı</h1>
  <p class="lead" style="max-width:162mm">Model önce saf fizikle çalışır: hava tahmini, panel
  geometrisi ve sıcaklık. Sonra santralinizin kendi geçmiş üretimiyle kalibre edilir. Bu bölüm o
  yolun her adımını sayıyla belgeler — hangi düzeltmenin ne kazandırdığı, hangisinin bedel
  ödettiği dâhil.</p>

  """ + selale() + """
    <div class="figcap"><b>Şekil 9.1</b>&nbsp;&nbsp;Ham fizik modelinden hibrit modele geçişte
      ortalama hatanın adım adım kapanması. Aradaki sütunlar havada durur, çünkü bir seviyeyi
      değil bir değişimi gösterirler; her sütunun altındaki satır o adımdan sonra kalan hatayı
      verir. Değişimler yüzde puanı cinsindendir. En büyük iki katkı sistem verimi düzeltmesi
      (−1,8 puan) ve makine öğrenmesinin artık hatayı öğrenmesinden (−2,0 puan) geliyor. Bulut
      geçişi düzeltmesi bu pencerede küçük bir bedel ödetti (+0,3 puan) ve iyileştirme
      listesinde tutuluyor.</div>

  <div class="two">
    <div>
      <h2>Bulunan katsayılar</h2>
      <table>""" + rows + """</table>
    </div>
    <div>
      <h2>Katsayılar makul mü?</h2>
      <p>Kalibrasyonun bir modeli veriye uydurup uydurmadığı, bulunan katsayıların fiziksel
      olarak anlamlı olup olmadığına bakılarak anlaşılır. Sistem verimi 0,942, tipik bir
      kablolama–inverter–trafo zincirinin beklenen aralığındadır. %7,3'lük bifacial kazanç,
      sahanın 0,16 olan zemin albedosuyla tutarlıdır.</p>
      <p>Katsayılar fiziksel aralığın dışına çıkarsa model “şüpheli kalibrasyon” olarak
      işaretlenir ve sonuç yayımlanmadan önce incelenir. Bu raporda böyle bir işaret yoktur.</p>
    </div>
  </div>

  <div class="note">
    <h3>Neden bedel ödeten adım da gösteriliyor?</h3>
    <p>Bulut geçişi düzeltmesi bu 120 günlük pencerede hatayı 0,3 puan artırdı. Adımı gizleyip
    yalnızca net iyileşmeyi yazmak daha iyi görünürdü, ama o zaman şelale bir kanıt olmaktan
    çıkıp bir sunuma dönüşürdü. Modelin hangi parçasının çalışmadığını bilmek, çalıştığını
    bilmek kadar değerlidir.</p>
  </div>
""" + foot(9) + """
</div></div>"""

build("PVQuant_Konya_GES_s09_kalibrasyon", CSS, BODY,
      "PVQuant — Konya GES · Kalibrasyon")
