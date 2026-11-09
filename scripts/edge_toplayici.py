#!/usr/bin/env python3
"""PVQuant saha toplayıcısı — referans uygulama (v2.561, Aşama 6 E1).

Ne yapar: Modbus TCP / SunSpec (ya da üretici haritası) cihazlarını YALNIZ OKUR (FC03/FC04; pvquant.io.canli), her örneği artan sıra numarasıyla yerel
journal'a yazar (JSONL, fsync), PVQuant'a HTTPS ile parti parti gönderir ve yalnız sunucunun ack'ladığı sıraya kadar olanları gönderilmiş sayar
(en az bir kez teslim; sunucu idempotent). Ack'lanmamış kayıt hiçbir koşulda silinmez; journal eşiği aşılınca ALARM satırı yazar, sessiz silme yapmaz.
Sunucudan komut almaz: yanıttaki tek bilgi ack_sira ve çatışma listesidir.

Kullanım:
  edge_toplayici.py --host 192.168.10.5 --port 502 --birim 1 [--cihazlar 2,3] [--profil sunspec|huawei_smartlogger|sungrow_string|growatt_rtu]
                    --sunucu https://pvquant.com --anahtar-dosya /etc/pvquant/toplayici.key --journal /var/lib/pvquant-edge
                    [--periyot 60] [--parti 200] [--azami-mb 2048] [--sakla-gun 14] [--sertifika istemci.pem --sertifika-anahtari istemci.key] [--tek-tur]
Anahtar dosyası: Santralim › Saha toplayıcısı'ndan üretilen «pvqe_…» metni (tek satır). mTLS: --sertifika ile istemci sertifikası (Caddy tarafı docs/edge/TOPLAYICI.md).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx

from pvquant.services import canli_ornekleme_service as co
from pvquant.services.canli_alim_service import hedef_dogrula


def _fsync_yaz(yol: str, metin: str, ekle: bool = True) -> None:
    with open(yol, "a" if ekle else "w", encoding="utf-8") as f:
        f.write(metin); f.flush(); os.fsync(f.fileno())


def _oku_int(yol: str, varsayilan: int) -> int:
    try:
        return int(open(yol, encoding="utf-8").read().strip())
    except (OSError, ValueError):
        return varsayilan


class Journal:
    def __init__(self, dizin: str):
        self.dizin = dizin; os.makedirs(dizin, exist_ok=True)
        self.sira = _oku_int(os.path.join(dizin, "sira.txt"), -1)
        self.ack = _oku_int(os.path.join(dizin, "ack.txt"), -1)

    def ekle(self, o: dict) -> int:
        self.sira += 1; o = {**o, "sira": self.sira}
        gun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _fsync_yaz(os.path.join(self.dizin, f"{gun}.jsonl"), json.dumps(o, ensure_ascii=False) + "\n")
        _fsync_yaz(os.path.join(self.dizin, "sira.txt"), str(self.sira), ekle=False)
        return self.sira

    def gonderilmemis(self, en_cok: int) -> list[dict]:
        out: list[dict] = []
        for yol in sorted(glob.glob(os.path.join(self.dizin, "*.jsonl"))):
            with open(yol, encoding="utf-8") as f:
                for satir in f:
                    try:
                        o = json.loads(satir)
                    except ValueError:
                        continue
                    if o.get("sira", -1) > self.ack:
                        out.append(o)
                        if len(out) >= en_cok:
                            return out
        return out

    def ack_yaz(self, sira: int) -> None:
        if sira is not None and sira > self.ack:
            self.ack = sira; _fsync_yaz(os.path.join(self.dizin, "ack.txt"), str(sira), ekle=False)

    def boyut_mb(self) -> float:
        return sum(os.path.getsize(p) for p in glob.glob(os.path.join(self.dizin, "*.jsonl"))) / 1e6

    def temizle(self, sakla_gun: int) -> int:
        """Yalnız tamamı ack'lanmış ve sakla_gun'den eski dosyalar silinir; ack'lanmamış satır içeren dosya asla silinmez."""
        n = 0; esik = time.time() - sakla_gun * 86400
        for yol in glob.glob(os.path.join(self.dizin, "*.jsonl")):
            if os.path.getmtime(yol) > esik:
                continue
            with open(yol, encoding="utf-8") as f:
                en_buyuk = max((json.loads(s).get("sira", -1) for s in f if s.strip()), default=-1)
            if en_buyuk <= self.ack:
                os.remove(yol); n += 1
        return n


def ornek_al(b: dict) -> tuple[list[dict], list[str]]:
    liste, hatalar = co.ornekler_al(b)
    return [{**o, "ts_utc": o["ts_utc"].isoformat()} for o in liste], hatalar


def gonder(istemci: httpx.Client, sunucu: str, anahtar: str, parti: list[dict]) -> dict:
    r = istemci.post(f"{sunucu.rstrip('/')}/v1/edge/ornekler", json={"ornekler": parti, "toplayici_surum": "v2.561"}, headers={"X-Toplayici-Anahtar": anahtar})
    r.raise_for_status()
    return r.json()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PVQuant saha toplayıcısı (yalnız okur; journal + ack)")
    ap.add_argument("--host", required=True); ap.add_argument("--port", type=int, default=502); ap.add_argument("--birim", type=int, default=1)
    ap.add_argument("--cihazlar", default=""); ap.add_argument("--profil", default=None); ap.add_argument("--zaman-asimi", type=float, default=None)
    ap.add_argument("--sunucu", required=True); ap.add_argument("--anahtar-dosya", required=True); ap.add_argument("--journal", required=True)
    ap.add_argument("--periyot", type=int, default=60); ap.add_argument("--parti", type=int, default=200); ap.add_argument("--azami-mb", type=float, default=2048)
    ap.add_argument("--sakla-gun", type=int, default=14); ap.add_argument("--sertifika", default=None); ap.add_argument("--sertifika-anahtari", default=None)
    ap.add_argument("--tek-tur", action="store_true", help="bir okuma + bir gönderim denemesi, sonra çık (sınama)")
    a = ap.parse_args(argv)
    anahtar = open(a.anahtar_dosya, encoding="utf-8").read().strip()
    cihazlar = [{"birim": int(x)} for x in a.cihazlar.replace(";", ",").split(",") if x.strip()] or None
    b = hedef_dogrula(a.host, a.port, a.birim, a.zaman_asimi, a.profil, cihazlar)
    j = Journal(a.journal)
    cert = (a.sertifika, a.sertifika_anahtari) if a.sertifika and a.sertifika_anahtari else (a.sertifika or None)
    bekleme = 5.0
    print(f"[toplayici] başladı · hedef {b['host']}:{b['port']} birim {b['birim']}{' +' + str(len(cihazlar)) + ' cihaz' if cihazlar else ''} · journal sira={j.sira} ack={j.ack}", flush=True)
    with httpx.Client(timeout=30.0, cert=cert) as istemci:
        while True:
            t0 = time.time()
            try:
                liste, hatalar = ornek_al(b)
                for o in liste:
                    j.ekle(o)
                print(f"[oku] {len(liste)} örnek journal'a yazıldı (sira {j.sira})" + (f"; hata: {'; '.join(hatalar)}" if hatalar else ""), flush=True)
            except Exception as e:   # noqa: BLE001 — okuma hatası gönderimi durdurmaz
                print(f"[oku] HATA {type(e).__name__}: {e}", flush=True)
            if j.boyut_mb() > a.azami_mb:
                print(f"[ALARM] journal {j.boyut_mb():.0f} MB > {a.azami_mb:.0f} MB; ack'lanmamış veri SİLİNMEZ — bağlantıyı ve diski kontrol edin", flush=True)
            while True:
                parti = j.gonderilmemis(a.parti)
                if not parti:
                    break
                try:
                    y = gonder(istemci, a.sunucu, anahtar, parti)
                    j.ack_yaz(y.get("ack_sira"))
                    print(f"[gonder] kabul {y.get('kabul')} yinelenen {y.get('yinelenen')} çatışma {len(y.get('catisma') or [])} hatalı {len(y.get('hatali') or [])} → ack {j.ack}", flush=True)
                    if y.get("catisma"):
                        print(f"[gonder] ÇATIŞMA sıraları {y['catisma']}: aynı sıra farklı içerik — journal bozulmuş olabilir; bu satırlar yeni sıra ile yeniden gönderilmeli (elle inceleme)", flush=True)
                        break
                    bekleme = 5.0
                    if y.get("ack_sira") is None or y["ack_sira"] < max(o["sira"] for o in parti):
                        break   # ilerleme yoksa döngüde kalma
                except Exception as e:   # noqa: BLE001 — ağ/sunucu hatası: geri çekil, journal kalır
                    print(f"[gonder] HATA {type(e).__name__}: {e}; {bekleme:.0f} sn sonra yeniden (journal'da {len(parti)}+ bekliyor)", flush=True)
                    time.sleep(bekleme); bekleme = min(bekleme * 2, 300.0); break
            silinen = j.temizle(a.sakla_gun)
            if silinen:
                print(f"[journal] {silinen} eski ve tamamı ack'lanmış dosya silindi", flush=True)
            if a.tek_tur:
                return 0
            time.sleep(max(1.0, a.periyot - (time.time() - t0)))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
