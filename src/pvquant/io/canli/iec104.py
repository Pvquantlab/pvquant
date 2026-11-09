"""09.11.2026 v2.547 (P4b-3) — IEC 60870-5-104 ULAŞILABİLİRLİK sınaması, yalnız bağlantı katmanı.

Yapılan: TCP bağlantısı + STARTDT act U-çerçevesi (68 04 07 00 00 00) gönderilir, STARTDT con (0B) beklenir, ardından STOPDT act (13) ile kapatılır.
Yapılmayan: genel sorgulama (C_IC_NA_1) dâhil hiçbir ASDU gönderilmez — komut yok, veri çekişi yok. Bu sınama yalnız «istasyon 104 konuşuyor» der.
Kaynak: IEC 60870-5-104 APCI U-biçimi (STARTDT/STOPDT/TESTFR). Gerçek RTU ile doğrulanmadı; sahte sunucuyla sınandı.
"""
from __future__ import annotations

import socket

VARSAYILAN_PORT = 2404
STARTDT_ACT = bytes([0x68, 0x04, 0x07, 0x00, 0x00, 0x00])
STARTDT_CON = bytes([0x68, 0x04, 0x0B, 0x00, 0x00, 0x00])
STOPDT_ACT = bytes([0x68, 0x04, 0x13, 0x00, 0x00, 0x00])


def ulasilabilirlik(host: str, port: int = VARSAYILAN_PORT, zaman_asimi: float = 5.0) -> dict:
    """Döner {tcp: bool, startdt_con: bool, yanit_hex: str|None}. TCP açılamazsa OSError yükselir."""
    with socket.create_connection((host, int(port)), timeout=zaman_asimi) as s:
        s.sendall(STARTDT_ACT)
        try:
            yanit = s.recv(6)
        except socket.timeout:
            yanit = b""
        con = yanit[:6] == STARTDT_CON
        if con:
            try:
                s.sendall(STOPDT_ACT)
            except OSError:
                pass
        return {"tcp": True, "startdt_con": con, "yanit_hex": yanit.hex() or None}
