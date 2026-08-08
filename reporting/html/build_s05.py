from pvq import *

# --- tipik gün: saat ortası değerleri [MW]; toplamı 65,8 MWh — BASE_KW'den türetilir
from veri import BASE_KW, P50_GUN
BASE = [(5.0, 0.0)] + [(5.5 + i, BASE_KW[i] / 1000) for i in range(len(BASE_KW))] + [(20.0, 0.0)]
DAILY = P50_GUN[:8]
MEAN = 64.8 / 65.8


def bez(pts, start=True):
    """Catmull-Rom → kübik bezier; yumuşak ama veriye sadık eğri."""
    d = ("M %.1f,%.1f " % pts[0]) if start else ("L %.1f,%.1f " % pts[0])
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += "C %.1f,%.1f %.1f,%.1f %.1f,%.1f " % (c1 + c2 + p2)
    return d


# ---------------------------------------------------------------- Şekil 5.1
def profile(W=1000, H=292, ml=54, mb=50, fs=15):
    MR, MT = 30, 14
    PW, PH = W - ml - MR, H - MT - mb
    X = lambda h: ml + PW * h / 24
    Y = lambda v: MT + PH * (10 - v) / 10
    o = []
    for t in range(0, 11, 2):
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.3"/>'
                 % (ml, Y(t), W - MR, Y(t), GRID))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" font-size="%d"'
                 ' font-weight="500" fill="#2B3439">%d</text>' % (ml - 9, Y(t) + fs * .34, fs, t))
    mid = [(h, v * MEAN) for h, v in BASE]
    up = [(X(h), Y(min(10, v * 1.13))) for h, v in mid]
    dn = [(X(h), Y(max(0, v * .87))) for h, v in mid]
    o.append('<path d="%s%s Z" fill="%s"/>' % (bez(up), bez(list(reversed(dn)), False), FAN_AREA))
    for ser in (up, dn):
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.3"/>' % (bez(ser), FAN_EDGE))
    o.append('<path d="%s" fill="none" stroke="%s" stroke-width="3.2" stroke-linecap="round"/>'
             % (bez([(X(h), Y(v)) for h, v in mid]), BRAND))
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" stroke-width="1.5"/>'
             % (ml, Y(0), W - MR, Y(0)))
    for h in range(0, 25, 3):
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#2B3439">%02d:00</text>'
                 % (X(h), Y(0) + fs * 1.5, fs, h))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="%s">Yerel saat</text>'
             % (ml + PW / 2, Y(0) + fs * 3.1, fs + 1, INK))
    o.append('<text transform="translate(14,%.1f) rotate(-90)" text-anchor="middle" '
             'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">[MW]</text>'
             % (MT + PH / 2, fs + 1, INK))
    # tepe açıklaması
    o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8FA4AE" '
             'stroke-width="1.2" stroke-dasharray="5 4"/>' % (X(12.5), Y(8.9), X(12.5), Y(9.9)))
    o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" font-size="%d" '
             'font-weight="600" fill="%s">tepe {{TEPE_TIPIK}} MW</text>' % (X(12.5), Y(10) - 3, fs, INK))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Tipik gun profili">%s</svg>' % (W, H, "".join(o)))


# ---------------------------------------------------------------- Şekil 5.2
def multiples(W=1000, H=402, fs=13):
    cols, rows, gx, gyr = 4, 2, 22, 26
    cw = (W - gx * (cols - 1)) / cols
    padl = 36
    pwd = cw - padl - 6
    ph = (H - 16 - gyr - 2 * (14 + 44)) / rows
    o = []
    for k in range(8):
        r, c = divmod(k, cols)
        ox = c * (cw + gx) + padl
        oy = 16 + r * (ph + 14 + 44 + gyr) + 14
        sc = DAILY[k] / 65.8
        X = lambda h: ox + pwd * h / 24
        Y = lambda v: oy + ph * (10 - v) / 10
        for t in range(0, 11, 2):
            o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                     'stroke-width="1.1"/>' % (ox, Y(t), ox + pwd, Y(t), GRID))
            o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" '
                     'font-size="%d" font-weight="500" fill="#2B3439">%d</text>'
                     % (ox - 7, Y(t) + fs * .34, fs, t))
        pts = [(h, v * sc) for h, v in BASE]
        up = [(X(h), Y(min(10, v * 1.13))) for h, v in pts]
        dn = [(X(h), Y(max(0, v * .87))) for h, v in pts]
        o.append('<path d="%s%s Z" fill="%s" stroke="%s" stroke-width="1"/>'
                 % (bez(up), bez(list(reversed(dn)), False), FAN_AREA, FAN_EDGE))
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.8" '
                 'stroke-linecap="round"/>' % (bez([(X(h), Y(v)) for h, v in pts]), BRAND))
        o.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#7C8781" '
                 'stroke-width="1.4"/>' % (ox, Y(0), ox + pwd, Y(0)))
        for h in (0, 6, 12, 18, 24):
            o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                     'font-size="%d" font-weight="500" fill="#2B3439">%d</text>'
                     % (X(h), Y(0) + fs * 1.5, fs, h))
        o.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="PlexSans" '
                 'font-size="%d" font-weight="600" fill="%s">[saat]</text>'
                 % (ox + pwd / 2, Y(0) + fs * 3, fs, INK))
        o.append('<text x="%.1f" y="%.1f" font-family="PlexSans" font-size="%d" '
                 'font-weight="600" fill="%s">%02d Ağustos</text>'
                 % (ox - padl + 2, oy - 7, fs + 1.5, INK, 5 + k))
        o.append('<text x="%.1f" y="%.1f" text-anchor="end" font-family="PlexSans" '
                 'font-size="%d" font-weight="500" fill="#5B686F">%s MWh</text>'
                 % (ox + pwd, oy - 7, fs, ("%.1f" % DAILY[k]).replace(".", ",")))
        if c == 0:
            o.append('<text transform="translate(%.1f,%.1f) rotate(-90)" text-anchor="middle" '
                     'font-family="PlexSans" font-size="%d" font-weight="600" fill="%s">[MW]</text>'
                     % (ox - padl - 4, oy + ph / 2, fs, INK))
    return ('<svg class="fig" viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-label="Ilk sekiz gunun saatlik profilleri">%s</svg>' % (W, H, "".join(o)))


CSS = """
.fig{margin-top:5mm}
.two{display:flex;gap:11mm;margin-top:5mm}
.two > div{flex:1}
.two p{font-size:9pt;line-height:1.56;margin-top:0}
.two h2{font-size:10.5pt;font-weight:600;padding-bottom:2mm;border-bottom:.9pt solid BRAND;
  margin-bottom:3.5mm}
""".replace("BRAND", BRAND)

BODY = """<div class="page"><div class="sheet">
""" + HEAD + """
  <div class="eyebrow">Tahmin detayı · devam</div>
  <h1>Saatlik profiller</h1>
  <p class="lead" style="max-width:160mm">Günlük toplamlar üretimin ne zaman geldiğini
  göstermez. Bu bölüm tipik bir günün saat saat seyrini ve ufkun ilk sekiz gününün profillerini
  verir; dengeleme, bakım planlaması ve saatlik satış kararları bu görünümden okunur.</p>

  """ + profile() + """
    <div class="legend"><span><i class="line"></i>Beklenti (P50)</span>
      <span><i class="fan"></i>%80 olasılık aralığı (P10–P90)</span></div>
    <div class="figcap"><b>Şekil 5.1</b>&nbsp;&nbsp;Tipik gün profili. Üretim 05:15 civarında
      başlar, 12:00–13:00 arasında {{TEPE_TIPIK}} MW tepe değerine ulaşır ve 19:45'te sona erer. Kum
      rengi alan %80 olasılık aralığıdır; gerçekleşen üretim on günün sekizinde bu alanın
      içinde kalır.</div>

  <div class="two">
    <div>
      <h2>Öğle platosu neden düz?</h2>
      <p>Tepe {{TEPE_TIPIK}} MW'ta kalıyor; santralin şebeke gücü ise {{SEBEKE}}. Yani inverterler kırpma
      yapmıyor, üretilen gücün tamamı şebekeye verilebiliyor. Plato tavana dayansaydı aradaki
      fark kalıcı kayıp olurdu.</p>
    </div>
    <div>
      <h2>Aralık neden öğlen genişliyor?</h2>
      <p>Mutlak belirsizlik üretimin yüksek olduğu saatlerde büyür; oransal olarak ise gün
      boyunca benzer kalır. Doğruluk ölçümünde bu yüzden üretimle ağırlıklandırılmış hata
      kullanılır.</p>
    </div>
  </div>

  """ + multiples() + """
    <div class="legend" style="margin-top:2mm"><span><i class="line"></i>Beklenti (P50)</span>
      <span><i class="fan"></i>%80 olasılık aralığı</span></div>
    <div class="figcap"><b>Şekil 5.2</b>&nbsp;&nbsp;Ufkun ilk sekiz gününün profilleri, ortak
      eksende. Sağ üstteki değer o günün toplam beklentisidir. 11 ve 12 Ağustos'ta eğri hem
      alçalıyor hem yayvanlaşıyor: cephe geçişinin saatlik karşılığı budur.</div>
""" + foot(5) + """
</div></div>"""

build("PVQuant_Konya_GES_s05_saatlik_profiller", CSS, BODY,
      "PVQuant — Konya GES · Saatlik profiller")
