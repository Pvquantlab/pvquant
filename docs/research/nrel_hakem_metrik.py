import csv, glob, os, re, sys, math
from collections import defaultdict
kok = sys.argv[1:]  # klasorler
def oku(p):
    d = {}
    with open(p, newline="") as f:
        r = csv.reader(f); next(r)
        for t, v in r:
            d[t[:11]] = d.get(t[:11], 0.0)  # placeholder
    return d
def saatlik(p, dakika):
    # "01/01/06 00:05" -> saat anahtari "01/01/06 00"
    agg = defaultdict(list)
    with open(p, newline="") as f:
        r = csv.reader(f); next(r)
        for t, v in r:
            agg[t[:11]].append(float(v))
    return {k: sum(v)/len(v) for k, v in agg.items()}
def metrik(a, f, cap):
    keys = [k for k in a if k in f and (a[k] > 0.01*cap or f[k] > 0.01*cap)]  # gunduz
    if not keys: return None
    err = [f[k]-a[k] for k in keys]; abse = [abs(e) for e in err]
    return dict(n=len(keys), wmape=100*sum(abse)/sum(a[k] for k in keys),
                nmae=100*sum(abse)/len(keys)/cap,
                nrmse=100*math.sqrt(sum(e*e for e in err)/len(keys))/cap,
                nmbe=100*sum(err)/len(keys)/cap)
sonuc = defaultdict(list)
for k in kok:
    for act in glob.glob(os.path.join(k, "**", "Actual_*_5_Min.csv"), recursive=True):
        m = re.search(r"Actual_(.+)_2006_([A-Z]+)_(\d+)MW_5_Min", act)
        if not m: continue
        site, tip, cap = m.group(1), m.group(2), float(m.group(3))
        a = saatlik(act, 5)
        for ufuk in ("DA", "HA4"):
            fp = glob.glob(os.path.join(os.path.dirname(act), f"{ufuk}_{site}_2006_{tip}_{int(cap)}MW_60_Min.csv"))
            if not fp: continue
            mt = metrik(a, saatlik(fp[0], 60), cap)
            if mt: sonuc[(os.path.basename(k.rstrip('/')), ufuk)].append(mt)
print(f"{'eyalet':<14}{'ufuk':<5}{'santral':>8}{'WMAPE%':>9}{'nMAE%':>8}{'nRMSE%':>8}{'nMBE%':>8}")
for (ey, uf), L in sorted(sonuc.items()):
    n = len(L); g = lambda kk: sum(x[kk] for x in L)/n
    print(f"{ey:<14}{uf:<5}{n:>8}{g('wmape'):>9.1f}{g('nmae'):>8.1f}{g('nrmse'):>8.1f}{g('nmbe'):>8.1f}")
