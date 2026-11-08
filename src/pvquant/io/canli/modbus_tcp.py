"""08.11.2026 v2.545 (P4b ilk bağlayıcı) — asgari Modbus TCP istemcisi, YALNIZ OKUMA (fonksiyon 0x03 Read Holding Registers).

Bağımlılık yok (soket). MBAP başlığı: işlem kimliği (2), protokol 0 (2), uzunluk (2), birim kimliği (1); PDU: fonksiyon (1) + adres (2) + adet (2).
Yazma fonksiyonları (0x05/0x06/0x0F/0x10) bilerek yoktur — istemci yapısal olarak salt okumadır (Modbus Application Protocol V1.1b3).
"""
from __future__ import annotations

import socket
import struct

ISTISNALAR = {1: "desteklenmeyen fonksiyon", 2: "geçersiz veri adresi", 3: "geçersiz veri değeri", 4: "cihaz hatası",
              5: "onay (işlem sürüyor)", 6: "cihaz meşgul", 10: "ağ geçidi yolu yok", 11: "ağ geçidi hedefi yanıt vermedi"}
AZAMI_KAYIT = 125   # tek istekte okunabilecek en çok kayıt (protokol sınırı)


class ModbusHata(RuntimeError):
    pass


class ModbusTcpIstemci:
    def __init__(self, host: str, port: int = 502, birim: int = 1, zaman_asimi: float = 5.0):
        self.host, self.port, self.birim, self.zaman_asimi = host, int(port), int(birim), float(zaman_asimi)
        self._s: socket.socket | None = None
        self._islem = 0

    def __enter__(self):
        self.baglan(); return self

    def __exit__(self, *a):
        self.kapat()

    def baglan(self) -> None:
        self._s = socket.create_connection((self.host, self.port), timeout=self.zaman_asimi)

    def kapat(self) -> None:
        if self._s is not None:
            try:
                self._s.close()
            finally:
                self._s = None

    def _al(self, n: int) -> bytes:
        assert self._s is not None
        veri = b""
        while len(veri) < n:
            parca = self._s.recv(n - len(veri))
            if not parca:
                raise ModbusHata("bağlantı kapandı")
            veri += parca
        return veri

    def oku(self, adres: int, adet: int) -> list[int]:
        """Holding register'ları (FC3) okur; 16 bit işaretsiz liste döner. adet > 125 parçalanır."""
        if self._s is None:
            self.baglan()
        out: list[int] = []
        kalan, a = int(adet), int(adres)
        while kalan > 0:
            n = min(kalan, AZAMI_KAYIT)
            out += self._oku_tek(a, n)
            a += n; kalan -= n
        return out

    def _oku_tek(self, adres: int, adet: int) -> list[int]:
        assert self._s is not None
        self._islem = (self._islem + 1) & 0xFFFF
        pdu = struct.pack(">BHH", 0x03, adres, adet)
        mbap = struct.pack(">HHHB", self._islem, 0, len(pdu) + 1, self.birim)
        self._s.sendall(mbap + pdu)
        bas = self._al(7)
        islem, proto, uzunluk, birim = struct.unpack(">HHHB", bas)
        if islem != self._islem or proto != 0:
            raise ModbusHata("beklenmeyen yanıt başlığı")
        govde = self._al(uzunluk - 1)
        fonk = govde[0]
        if fonk & 0x80:
            kod = govde[1] if len(govde) > 1 else 0
            raise ModbusHata(f"Modbus istisnası {kod}: {ISTISNALAR.get(kod, 'bilinmeyen')}")
        if fonk != 0x03:
            raise ModbusHata(f"beklenmeyen fonksiyon {fonk}")
        bayt = govde[1]
        if bayt != 2 * adet or len(govde) < 2 + bayt:
            raise ModbusHata("yanıt uzunluğu uyumsuz")
        return list(struct.unpack(f">{adet}H", govde[2:2 + bayt]))
