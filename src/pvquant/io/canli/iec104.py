"""09.11.2026 v2.547 (P4b-3) — IEC 60870-5-104 ULAŞILABİLİRLİK sınaması, yalnız bağlantı katmanı.
v2.548 (Aşama 0 hijyen, H2): varsayılan sınama YALNIZ TCP bağlantısıdır; STARTDT gönderilmez.

Neden: IEC 104 slave'lerinin yaygın bir uygulaması (lib60870, varsayılan «tek yedeklilik grubu» kipi) yeni bir istemciden STARTDT gelince mevcut aktif
bağlantıyı kapatır. PVQuant ikinci bir istemci olarak STARTDT gönderirse birincil SCADA'nın oturumunu düşürebilir. Üretici cihazlarının (Huawei SmartLogger,
Sungrow Logger, GoodWe EzLogger, GE FLEXIQ) bu davranışı DOĞRULANMADI; ihtiyat gereği STARTDT yalnız sahibin «ayrı istemci yuvası tanımlandı» onayıyla gönderilir.

startdt=False: TCP bağlantısı açılır ve kapatılır; döner {tcp: True, startdt_con: None, startdt_gonderildi: False}.
startdt=True : STARTDT act U-çerçevesi (68 04 07 00 00 00) gönderilir, STARTDT con (0B) beklenir, ardından STOPDT act (13) ile kapatılır.
Her iki kipte de genel sorgulama (C_IC_NA_1) dâhil hiçbir ASDU gönderilmez — komut yok, veri çekişi yok.
Kaynak: IEC 60870-5-104 APCI U-biçimi (STARTDT/STOPDT/TESTFR). Gerçek RTU ile doğrulanmadı; sahte sunucuyla sınandı.
"""
from __future__ import annotations

import socket

VARSAYILAN_PORT = 2404
STARTDT_ACT = bytes([0x68, 0x04, 0x07, 0x00, 0x00, 0x00])
STARTDT_CON = bytes([0x68, 0x04, 0x0B, 0x00, 0x00, 0x00])
STOPDT_ACT = bytes([0x68, 0x04, 0x13, 0x00, 0x00, 0x00])


def ulasilabilirlik(host: str, port: int = VARSAYILAN_PORT, zaman_asimi: float = 5.0, startdt: bool = False) -> dict:
    """Döner {tcp: bool, startdt_con: bool|None, startdt_gonderildi: bool, yanit_hex: str|None}. TCP açılamazsa OSError yükselir."""
    with socket.create_connection((host, int(port)), timeout=zaman_asimi) as s:
        if not startdt:
            return {"tcp": True, "startdt_con": None, "startdt_gonderildi": False, "yanit_hex": None}
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
        return {"tcp": True, "startdt_con": con, "startdt_gonderildi": True, "yanit_hex": yanit.hex() or None}
