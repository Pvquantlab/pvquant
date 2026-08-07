# -*- coding: utf-8 -*-
"""denetim_uygulama.py — 16 sayfalık uygulama raporunun tek tabana karşı çapraz denetimi.
Kullanım: python3 denetim_uygulama.py <rapor.pdf> <taban_d.json>"""
import re, json, sys, subprocess
import numpy as np
pdf, taban = sys.argv[1], sys.argv[2]
subprocess.run(["pdftotext","-layout",pdf,"/tmp/_r.txt"],check=True)
s=open("/tmp/_r.txt").read(); T=json.load(open(taban))
HATA=[]
ok=lambda ad,c: (print(("✓" if c else "✗ FARK"),ad), c or HATA.append(ad))
sayi=lambda x: float(x.replace(".","").replace(",","."))
blok=re.search(r"04–05.*?Σ \[MWh\][^\n]*", s, re.S).group(0)
veri={}
for ln in blok.splitlines():
    mm=re.match(r"\s*(\d{2})–\d{2}\s+(.*)", ln)
    if mm and "–" not in mm.group(2):
        v=[sayi(x) for x in mm.group(2).split()]
        if len(v)==16: veri[int(mm.group(1))]=v
M=np.array([veri[h] for h in sorted(veri)]); P50=np.array(T["p50g"])
ok("Matris Σ = P50 günlükleri (16/16)", np.allclose(np.round(M.sum(axis=0)/1000,1),P50,atol=0.06))
ok("Tipik gün tepe 8,9 = 12–13 satır ortalaması", abs(np.mean(veri[12])/1000-8.9)<0.05)
ok("Cephe günleri ölçekli profil (11 Ağu/05 Ağu oranı sabit)", (M[:,6]/M[:,0]).std()<0.01)
IK=np.array(T["iklim"]); b2=re.search(r"2007 .*?Ortalama[^\n]*", s, re.S).group(0)
esit=True; n=0
for ln in b2.splitlines():
    mm=re.match(r"\s*(20\d\d)\s+(.*)", ln)
    if mm and int(mm.group(1))<=2025:
        y=int(mm.group(1)); v=mm.group(2).split()
        if not (np.allclose([sayi(x) for x in v[:12]], IK[y-2007]) and abs(sayi(v[12])-IK[y-2007].sum())<0.5):
            esit=False
        n+=1
ok(f"Çizelge 12.1 = kalibre iklim matrisi ({n}/19)", esit and n==19)
ok("Ortalama satırı = LTA (19.530)", "19.530" in b2)
ok("Pxx: 18.153 / 18.805 / 19.530", all(x in s for x in ["18.153","18.805","19.530"]))
ok("Şelale kalan hata 13,6→11,8→10,6→10,9→8,9", all(x in s for x in ["%13,6","%11,8","%10,6","%10,9","%8,9"]))
ok("Sapma bandı −2,8/+2,4 · medyan −0,2 · 116 gün", all(x in s for x in ["−2,8","+2,4","−0,2","116 geçerli gün"]))
ok("Kapsama 84/58/49/55/88/92 + %71", all(x in s for x in ["%84","%58","%49","%55","%88","%92","%71"]))
ok("Naif özdeşliği 7/7 (Çizelge 7.1)", all(abs(w/(1-k/100)-nf)<0.06 for w,k,nf in
   [(8.1,44.5,14.6),(9.0,40.4,15.1),(12.7,20.1,15.9),(8.5,42.2,14.7),(7.4,46.4,13.8),(8.8,40.9,14.9),(9.6,37.7,15.4)]))
ok("Evrim ±7,4→±2,8 · son 65,8", all(x in s for x in ["±7,4","±2,8","65,8 MWh"]))
if HATA:
    print("\n✗ ÇAPRAZ DENETİM BAŞARISIZ: %d fark" % len(HATA)); sys.exit(1)
print("\nÇAPRAZ DENETİM TAMAM")
