"""09.11.2026 v2.554 (Aşama 2, S4) — IEC 60870-5-104 SALT-OKUR VERİ İSTEMCİSİ (ikinci izleme istemcisi; EDAŞ/TEİAŞ RTU hattına dokunmaz).

Giden yönde yalnız: STARTDT/STOPDT/TESTFR U-çerçeveleri, S-çerçevesi (alındı onayı) ve C_IC_NA_1 (100, genel sorgulama, QOI 20). İsteğe bağlı C_CI_NA_1
(101, sayaç sorgulama). C_CS_NA_1 (103 saat eşitleme), komutlar (45–51, 58–64), parametre yükleme ve dosya aktarımı KOD YOLUNDA YOKTUR.
Gelen ASDU tipleri: 1 M_SP_NA_1, 3 M_DP_NA_1, 9 M_ME_NA_1 (normalize), 11 M_ME_NB_1 (ölçekli), 13 M_ME_NC_1 (kısa kayan), 15 M_IT_NA_1 (sayaç), 30/31/34/35/36/37
(CP56Time2a zaman etiketli karşılıkları), 70 M_EI_NA_1 (başlatma sonu), 100 C_IC_NA_1 onay/sonlanma. Bilinmeyen tip atlanır ve sayılır.
Parametreler santral başına: k, w, t0–t3 (başlangıç 12/8/30/15/10/20; kaynaklar t0'da 10–30 s arası çelişiyor), CA/IOA/COT boyları (2/3/2).
Kalite bitleri (QDS/SIQ/DIQ): IV geçersiz, NT güncel değil, SB ikame, BL bloke, OV taşma → ölçüm «eksik» ya da «ikame» sayılır (kaynak_secim tamlığı değil, alan kalitesi).
CP56Time2a cihaz saatidir; saat dilimi bilinmediği için UTC varsayılır ve `zaman_kaynagi: cihaz` işaretlenir; toplayıcı istemcinin UTC saatini esas alır.
STARTDT yalnız sahibin «ayrı istemci yuvası tanımlandı» onayıyla gönderilir (v2.548 kuralı). Gerçek RTU ile DOĞRULANMADI; sahte sunucuyla sınandı.
Kaynaklar: IEC 60870-5-104 APCI/ASDU biçimi (ikincil kütüphane belgeleri lib60870, j60870, go-iecp5 — Opus 08 §5).
"""
from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from datetime import datetime, timezone

VARSAYILAN_PORT = 2404
IZLEME_TIPLERI = {1: "M_SP_NA_1", 3: "M_DP_NA_1", 9: "M_ME_NA_1", 11: "M_ME_NB_1", 13: "M_ME_NC_1", 15: "M_IT_NA_1", 30: "M_SP_TB_1", 31: "M_DP_TB_1",
                  34: "M_ME_TD_1", 35: "M_ME_TE_1", 36: "M_ME_TF_1", 37: "M_IT_TB_1", 70: "M_EI_NA_1", 100: "C_IC_NA_1", 101: "C_CI_NA_1"}
ELEMAN_BOYU = {1: 1, 3: 1, 9: 3, 11: 3, 13: 5, 15: 5, 30: 8, 31: 8, 34: 10, 35: 10, 36: 12, 37: 12, 70: 1, 100: 1, 101: 1}
GIDEN_IZINLI = {100, 101}   # salt-okur küme — başka tip gönderilmez
COT_ETIKET = {3: "spontan", 5: "istek", 6: "etkinleştirme", 7: "etkinleştirme onayı", 10: "etkinleştirme sonu", 20: "genel sorgulama", 37: "sayaç sorgulama"}


@dataclass
class Parametreler:
    k: int = 12
    w: int = 8
    t0: float = 30.0
    t1: float = 15.0
    t2: float = 10.0
    t3: float = 20.0
    ca_boy: int = 2
    ioa_boy: int = 3
    cot_boy: int = 2

    @classmethod
    def ayardan(cls, d: dict | None) -> "Parametreler":
        d = d or {}
        p = cls()
        for ad in ("k", "w", "ca_boy", "ioa_boy", "cot_boy"):
            if d.get(ad) is not None:
                setattr(p, ad, int(d[ad]))
        for ad in ("t0", "t1", "t2", "t3"):
            if d.get(ad) is not None:
                setattr(p, ad, float(d[ad]))
        if not (1 <= p.k <= 32767) or not (1 <= p.w <= p.k) or p.ca_boy not in (1, 2) or p.ioa_boy not in (1, 2, 3) or p.cot_boy not in (1, 2):
            raise ValueError("IEC 104 parametreleri geçersiz (k 1–32767, w ≤ k, CA 1–2, IOA 1–3, COT 1–2)")
        return p


class Iec104Hata(RuntimeError):
    def __init__(self, mesaj: str, kod: str = "protokol_hatasi"):
        super().__init__(mesaj); self.kod = kod


# ----------------------------------------------------------------------------- çerçeveler
def u_cerceve(cf1: int) -> bytes:
    return bytes([0x68, 0x04, cf1, 0x00, 0x00, 0x00])


STARTDT_ACT, STARTDT_CON, STOPDT_ACT, STOPDT_CON, TESTFR_ACT, TESTFR_CON = (u_cerceve(c) for c in (0x07, 0x0B, 0x13, 0x23, 0x43, 0x83))


def s_cerceve(nr: int) -> bytes:
    return bytes([0x68, 0x04, 0x01, 0x00, (nr << 1) & 0xFE, (nr >> 7) & 0xFF])


def i_cerceve(ns: int, nr: int, asdu: bytes) -> bytes:
    return bytes([0x68, 4 + len(asdu), (ns << 1) & 0xFE, (ns >> 7) & 0xFF, (nr << 1) & 0xFE, (nr >> 7) & 0xFF]) + asdu


def asdu_genel_sorgulama(ca: int, p: Parametreler, tip: int = 100, qoi: int = 20) -> bytes:
    """C_IC_NA_1 (100) etkinleştirme (COT 6), IOA 0, QOI 20 (istasyon). tip 101 → C_CI_NA_1 QCC 5 (genel sayaç isteği)."""
    if tip not in GIDEN_IZINLI:
        raise Iec104Hata(f"tip {tip} gönderilemez (salt-okur istemci)", "yasak_tip")
    cot = bytes([6]) + (bytes([0]) if p.cot_boy == 2 else b"")
    cab = struct.pack("<H", ca) if p.ca_boy == 2 else bytes([ca & 0xFF])
    ioa = (0).to_bytes(p.ioa_boy, "little")
    return bytes([tip, 0x01]) + cot + cab + ioa + bytes([qoi if tip == 100 else 5])


# ----------------------------------------------------------------------------- çözücüler
def cp56(b: bytes) -> datetime | None:
    if len(b) < 7:
        return None
    ms = struct.unpack("<H", b[0:2])[0]
    dk, sa, gun, ay, yil = b[2] & 0x3F, b[3] & 0x1F, b[4] & 0x1F, b[5] & 0x0F, (b[6] & 0x7F) + 2000
    gecersiz = bool(b[2] & 0x80)
    try:
        t = datetime(yil, ay, gun, sa, dk, ms // 1000, (ms % 1000) * 1000, tzinfo=timezone.utc)
    except ValueError:
        return None
    return None if gecersiz else t


def _kalite(q: int) -> dict:
    return {"iv": bool(q & 0x80), "nt": bool(q & 0x40), "sb": bool(q & 0x20), "bl": bool(q & 0x10), "ov": bool(q & 0x01)}


def _eleman(tip: int, b: bytes) -> dict:
    """Tek bilgi nesnesi gövdesi → {deger, kalite, zaman}."""
    if tip in (1, 30):
        q = b[0]; out = {"deger": int(q & 0x01), "kalite": {**_kalite(q & 0xF0), "ov": False}}
    elif tip in (3, 31):
        q = b[0]; out = {"deger": int(q & 0x03), "kalite": {**_kalite(q & 0xF0), "ov": False}}   # 1 KAPALI, 2 AÇIK, 0/3 belirsiz
    elif tip in (9, 34):
        out = {"deger": struct.unpack("<h", b[0:2])[0] / 32768.0, "kalite": _kalite(b[2])}
    elif tip in (11, 35):
        out = {"deger": float(struct.unpack("<h", b[0:2])[0]), "kalite": _kalite(b[2])}
    elif tip in (13, 36):
        out = {"deger": float(struct.unpack("<f", b[0:4])[0]), "kalite": _kalite(b[4])}
    elif tip in (15, 37):
        sayac = struct.unpack("<i", b[0:4])[0]; sq = b[4]
        out = {"deger": float(sayac), "kalite": {"iv": bool(sq & 0x80), "nt": False, "sb": False, "bl": False, "ov": bool(sq & 0x20)}, "sira": sq & 0x1F, "ayarlandi": bool(sq & 0x40)}
    else:
        return {"deger": None, "kalite": None}
    if tip >= 30:
        out["zaman"] = cp56(b[ELEMAN_BOYU[tip] - 7:ELEMAN_BOYU[tip]])
        out["zaman_kaynagi"] = "cihaz"
    return out


def asdu_coz(asdu: bytes, p: Parametreler) -> dict:
    """ASDU → {tip, tip_adi, cot, pn, test, ca, nesneler: [{ioa, deger, kalite, zaman}]}."""
    if len(asdu) < 2 + p.cot_boy + p.ca_boy:
        raise Iec104Hata("ASDU başlığı kısa")
    tip, vsq = asdu[0], asdu[1]
    sq, n = bool(vsq & 0x80), vsq & 0x7F
    cot_b = asdu[2]; cot, pn, test = cot_b & 0x3F, bool(cot_b & 0x40), bool(cot_b & 0x80)
    i = 2 + p.cot_boy
    ca = struct.unpack("<H", asdu[i:i + 2])[0] if p.ca_boy == 2 else asdu[i]
    i += p.ca_boy
    nesneler = []
    boy = ELEMAN_BOYU.get(tip)
    if boy is None:
        return {"tip": tip, "tip_adi": IZLEME_TIPLERI.get(tip, f"tip {tip}"), "cot": cot, "pn": pn, "test": test, "ca": ca, "nesneler": [], "bilinmeyen": True}
    if sq:
        ioa0 = int.from_bytes(asdu[i:i + p.ioa_boy], "little"); i += p.ioa_boy
        for k in range(n):
            if i + boy > len(asdu):
                raise Iec104Hata("ASDU gövdesi kısa (SQ)")
            nesneler.append({"ioa": ioa0 + k, **_eleman(tip, asdu[i:i + boy])}); i += boy
    else:
        for _ in range(n):
            if i + p.ioa_boy + boy > len(asdu):
                raise Iec104Hata("ASDU gövdesi kısa")
            ioa = int.from_bytes(asdu[i:i + p.ioa_boy], "little"); i += p.ioa_boy
            nesneler.append({"ioa": ioa, **_eleman(tip, asdu[i:i + boy])}); i += boy
    return {"tip": tip, "tip_adi": IZLEME_TIPLERI.get(tip, f"tip {tip}"), "cot": cot, "pn": pn, "test": test, "ca": ca, "nesneler": nesneler}


# ----------------------------------------------------------------------------- istemci
class Iec104Istemci:
    """Tek oturum: bağlan → STARTDT → genel sorgulama → sonlanmaya kadar dinle → STOPDT → kapat. Gelen her I-çerçevesi sayılır, S-çerçevesiyle onaylanır."""

    def __init__(self, host: str, port: int = VARSAYILAN_PORT, p: Parametreler | None = None, baglanti_zaman_asimi: float | None = None):
        self.host, self.port, self.p = host, int(port), p or Parametreler()
        self._s: socket.socket | None = None
        self.ns = 0; self.nr = 0; self._onaysiz = 0
        self.gonderilen_tipler: list[int] = []

    def __enter__(self):
        self._s = socket.create_connection((self.host, self.port), timeout=self.p.t0)
        self._s.settimeout(self.p.t1)
        return self

    def __exit__(self, *a):
        self.kapat()

    def kapat(self) -> None:
        if self._s is not None:
            try:
                self._s.close()
            finally:
                self._s = None

    def _al_apdu(self) -> tuple[int, bytes]:
        assert self._s is not None
        bas = b""
        while len(bas) < 2:
            parca = self._s.recv(2 - len(bas))
            if not parca:
                raise Iec104Hata("bağlantı kapandı", "baglanti_kapandi")
            bas += parca
        if bas[0] != 0x68:
            raise Iec104Hata(f"APCI başlangıç baytı {bas[0]:#x} ≠ 0x68")
        n = bas[1]
        if n < 4 or n > 253:
            raise Iec104Hata(f"APDU uzunluğu {n} geçersiz")
        veri = b""
        while len(veri) < n:
            parca = self._s.recv(n - len(veri))
            if not parca:
                raise Iec104Hata("bağlantı kapandı", "baglanti_kapandi")
            veri += parca
        return n, veri

    def _gonder(self, b: bytes) -> None:
        assert self._s is not None
        self._s.sendall(b)

    def startdt(self) -> None:
        self._gonder(STARTDT_ACT)
        n, v = self._al_apdu()
        if v[0] != 0x0B:
            raise Iec104Hata(f"STARTDT onayı gelmedi (CF1 {v[0]:#x})", "protokol_yaniti_yok")

    def stopdt(self) -> None:
        try:
            self._gonder(STOPDT_ACT)
            self._s.settimeout(min(self.p.t1, 3.0))
            self._al_apdu()
        except (Iec104Hata, OSError):
            pass

    def _i_gonder(self, asdu: bytes) -> None:
        tip = asdu[0]
        if tip not in GIDEN_IZINLI:
            raise Iec104Hata(f"tip {tip} gönderilemez (salt-okur istemci)", "yasak_tip")
        self._gonder(i_cerceve(self.ns, self.nr, asdu))
        self.gonderilen_tipler.append(tip)
        self.ns = (self.ns + 1) & 0x7FFF

    def genel_sorgulama(self, ca: int, azami_sure: float | None = None, sayac: bool = False) -> dict:
        """C_IC_NA_1 gönderir; etkinleştirme sonuna (COT 10) ya da süre dolana kadar gelen ASDU'ları toplar. Döner {noktalar, asdular, cot_akisi, bilinmeyen, sonlandi}."""
        import time
        p = self.p
        self._i_gonder(asdu_genel_sorgulama(ca, p, 101 if sayac else 100))
        noktalar: list[dict] = []; asdular = 0; bilinmeyen = 0; cot_akisi: list[int] = []; sonlandi = False
        bitis = time.monotonic() + (azami_sure or max(p.t1 * 4, 20.0))
        while time.monotonic() < bitis:
            try:
                n, v = self._al_apdu()
            except socket.timeout:
                # t3: boşta kaldı → TESTFR act gönder, con bekle; yanıt yoksa bitir
                try:
                    self._gonder(TESTFR_ACT); self._al_apdu()
                except (Iec104Hata, OSError):
                    break
                continue
            cf1 = v[0]
            if cf1 & 0x01 == 0:   # I-çerçevesi
                self.nr = (self.nr + 1) & 0x7FFF; self._onaysiz += 1
                try:
                    a = asdu_coz(v[4:], p)
                except Iec104Hata:
                    bilinmeyen += 1; a = None
                if a is not None:
                    asdular += 1; cot_akisi.append(a["cot"])
                    if a.get("bilinmeyen"):
                        bilinmeyen += 1
                    elif a["tip"] in (100, 101):
                        if a["cot"] == 10 or (a["pn"] and a["cot"] == 7):
                            sonlandi = True
                    elif a["tip"] != 70:
                        for o in a["nesneler"]:
                            noktalar.append({"ioa": o["ioa"], "tip": a["tip"], "tip_adi": a["tip_adi"], "ca": a["ca"], "cot": a["cot"], "deger": o.get("deger"),
                                             "kalite": o.get("kalite"), "zaman": (o["zaman"].isoformat() if o.get("zaman") else None), "zaman_kaynagi": o.get("zaman_kaynagi")})
                if self._onaysiz >= p.w or sonlandi:
                    self._gonder(s_cerceve(self.nr)); self._onaysiz = 0
                if sonlandi:
                    break
            elif cf1 & 0x03 == 0x01:   # S-çerçevesi: karşı tarafın onayı; bizim giden sayımız küçük, izlemeye gerek yok
                continue
            else:   # U-çerçevesi
                if cf1 == 0x43:
                    self._gonder(TESTFR_CON)
                elif cf1 == 0x13:   # karşı taraf STOPDT istedi
                    self._gonder(STOPDT_CON); break
        if self._onaysiz:
            try:
                self._gonder(s_cerceve(self.nr)); self._onaysiz = 0
            except OSError:
                pass
        return {"noktalar": noktalar, "asdu_sayisi": asdular, "bilinmeyen": bilinmeyen, "cot_akisi": cot_akisi, "sonlandi": sonlandi, "gonderilen_tipler": list(self.gonderilen_tipler)}


def genel_sorgulama(host: str, port: int, ca: int, p: Parametreler | None = None, azami_sure: float | None = None) -> dict:
    """Kısa yol: bağlan → STARTDT → GI → STOPDT. OSError bağlantı katmanında yükselir; Iec104Hata protokol."""
    with Iec104Istemci(host, port, p) as c:
        c.startdt()
        try:
            r = c.genel_sorgulama(ca, azami_sure)
        finally:
            c.stopdt()
    return r
