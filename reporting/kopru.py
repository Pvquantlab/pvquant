# -*- coding: utf-8 -*-
"""kopru.py — uygulama ile HTML rapor motoru arasındaki tek kapı (Dalga E.2, Adım 3a).

Kullanım (uygulamadan):
    from reporting.kopru import json_ile_uret
    pdf_yolu = json_ile_uret("/tmp/rapor_girdi.json")            # doğrulama içeride

Kullanım (komut satırı / CI):
    python3 kopru.py <girdi.json> [cikti_klasoru]

Sözleşme:
- Girdi: JSON v2.0/v2.1 (şema: html/docs/veri_haritasi.md, örnek: html/ornek_girdi_v21.json).
- Eksik alan SESSİZCE varsayılana düşmez — adaptör KeyError ile gürültüyle durur.
- Üretim sonrası iki bekçi koşar; ikisi de geçmeden yol dönmez:
    (1) sayfa sayısı == 16 (tek A4 taşma yok),
    (2) denetim_uygulama.py çıkış kodu 0 (taban ile çapraz tutarlılık).
- Dönüş: (pdf_yolu, html_yolu). Bekçi düşerse RaporUretimHatasi.
"""
import os
import re
import subprocess
import sys

_BURASI = os.path.dirname(os.path.abspath(__file__))
_HTML = os.path.join(_BURASI, "html")
_DENETIM = os.path.join(_BURASI, "denetim", "denetim_uygulama.py")
_TABAN = os.path.join(_BURASI, "denetim", "taban_d.json")
_RAPOR_AD = "PVQuant_Konya_GES_RAPOR_16sayfa"  # E.3'te santral adından türetilecek


class RaporUretimHatasi(RuntimeError):
    pass


def json_ile_uret(json_yolu, cikti=None, denetim=True):
    """JSON girdisinden 16 sayfalık raporu üretir, bekçilerden geçirir, yolları döner."""
    json_yolu = os.path.abspath(json_yolu)
    if not os.path.exists(json_yolu):
        raise RaporUretimHatasi("girdi yok: %s" % json_yolu)
    env = dict(os.environ, PVQ_VERI_JSON=json_yolu)
    if cikti:
        cikti = os.path.abspath(cikti)
        os.makedirs(cikti, exist_ok=True)
        env["PVQ_CIKTI"] = cikti
    else:
        cikti = os.path.join(_HTML, "cikti")

    p = subprocess.run([sys.executable, "uret.py"], cwd=_HTML, env=env,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RaporUretimHatasi("uret.py düştü:\n" + p.stdout[-2000:] + p.stderr[-2000:])

    # Bekçi 1 — 16 sayfa, taşma yok (uret çıktısından sayılır)
    tek = len(re.findall(r": 1 sayfa|sayfa: 1", p.stdout))
    if tek != 16 or "Tüm sayfalar tek A4'e sığdı." not in p.stdout:
        raise RaporUretimHatasi("sayfa bekçisi düştü: %d/16 tek sayfa\n%s"
                                % (tek, p.stdout[-1500:]))

    pdf = os.path.join(cikti, _RAPOR_AD + ".pdf")
    html = os.path.join(cikti, _RAPOR_AD + ".html")

    # Bekçi 2 — çapraz denetim (çıkış kodu 0 şart)
    # NOT: taban_d.json Konya kanonik tabanıdır; farklı santral girdisinde
    # denetim=False geçilir ve E.3'te taban da girdiden türetilir.
    if denetim:
        d = subprocess.run([sys.executable, _DENETIM, pdf, _TABAN],
                           capture_output=True, text=True)
        if d.returncode != 0:
            raise RaporUretimHatasi("çapraz denetim düştü:\n" + d.stdout[-1500:])

    return pdf, html


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    try:
        pdf, html = json_ile_uret(sys.argv[1],
                                  sys.argv[2] if len(sys.argv) > 2 else None)
        print("RAPOR HAZIR")
        print("pdf :", pdf)
        print("html:", html)
    except RaporUretimHatasi as e:
        print("RAPOR ÜRETİLEMEDİ —", e)
        sys.exit(1)
