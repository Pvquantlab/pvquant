"""08.11.2026 v2.545 (P4b ilk bağlayıcı) — asgari Modbus TCP istemcisi, YALNIZ OKUMA (fonksiyon 0x03 Read Holding Registers).
v2.549 (Aşama 1, D3) — MBAP sertleştirme: yanıt başlığında işlem kimliği, protokol (0), BİRİM kimliği ve uzunluk (3–253) doğrulanır; gövde byte-count
2×adet ile birebir olmalı; kısa/parçalı/uzun çerçeve yapısal `ModbusHata(kod='protokol_hatasi')` ile reddedilir ve bağlantı kapatılır (eski cevap yeni
isteğe bağlanmaz). Hata kodları: protokol_hatasi · cihaz_istisnasi (kod) · cihaz_mesgul · zaman_asimi · baglanti_kapandi. Zaman aşımı profil/bağlantı
başına verilir (varsayılan 5 sn; Fronius Datamanager belgesi ≥10 sn önerir).

Bağımlılık yok (soket). MBAP başlığı: işlem kimliği (2), protokol 0 (2), uzunluk (2), birim kimliği (1); PDU: fonksiyon (1) + adres (2) + adet (2).
Yazma fonksiyonları (0x05/0x06/0x0F/0x10) bilerek yoktur — istemci yapısal olarak yalnızca okumadır (Modbus Application Protocol V1.1b3).
v2.552 (S2): FC04 Read Input Registers eklendi (yine okuma); üretici profilleri 3x alanını bununla okur.
"""
from __future__ import annotations

import socket
import struct

ISTISNALAR = {1: "desteklenmeyen fonksiyon", 2: "geçersiz veri adresi", 3: "geçersiz veri değeri", 4: "cihaz hatası",
              5: "onay (işlem sürüyor)", 6: "cihaz meşgul", 10: "ağ geçidi yolu yok", 11: "ağ geçidi hedefi yanıt vermedi"}
AZAMI_KAYIT = 125   # tek istekte okunabilecek en çok kayıt (protokol sınırı)
AZAMI_UZUNLUK = 253   # MBAP uzunluk alanı üst sınırı (birim + PDU)
VARSAYILAN_ZAMAN_ASIMI = 5.0


class ModbusHata(RuntimeError):
    def __init__(self, mesaj: str, kod: str = "protokol_hatasi", istisna_kodu: int | None = None):
        super().__init__(mesaj)
        self.kod = kod
        self.istisna_kodu = istisna_kodu


class ModbusTcpIstemci:
    def __init__(self, host: str, port: int = 502, birim: int = 1, zaman_asimi: float = VARSAYILAN_ZAMAN_ASIMI):
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
            try:
                parca = self._s.recv(n - len(veri))
            except socket.timeout as e:
                self.kapat()
                raise ModbusHata("yanıt zaman aşımı", "zaman_asimi") from e
            if not parca:
                self.kapat()
                raise ModbusHata("bağlantı kapandı", "baglanti_kapandi")
            veri += parca
        return veri

    def _ret(self, mesaj: str) -> ModbusHata:
        self.kapat()   # çerçeve senkronu kayboldu: eski cevabın yeni isteğe bağlanmaması için bağlantı kapatılır
        return ModbusHata(mesaj, "protokol_hatasi")

    def oku(self, adres: int, adet: int) -> list[int]:
        """Holding register'ları (FC3) okur; 16 bit işaretsiz liste döner. adet > 125 parçalanır."""
        return self._oku(adres, adet, 0x03)

    def oku_giris(self, adres: int, adet: int) -> list[int]:
        """v2.552 (S2): giriş register'ları (FC4 Read Input Registers) — yine yalnızca okuma; üretici profilleri (Sungrow 3x, Growatt) için."""
        return self._oku(adres, adet, 0x04)

    def _oku(self, adres: int, adet: int, fonk: int) -> list[int]:
        if self._s is None:
            self.baglan()
        out: list[int] = []
        kalan, a = int(adet), int(adres)
        while kalan > 0:
            n = min(kalan, AZAMI_KAYIT)
            out += self._oku_tek(a, n, fonk)
            a += n; kalan -= n
        return out

    def _oku_tek(self, adres: int, adet: int, fonk_istek: int = 0x03) -> list[int]:
        if self._s is None:
            self.baglan()
        assert self._s is not None
        if not (1 <= adet <= AZAMI_KAYIT) or not (0 <= adres <= 0xFFFF):
            raise ModbusHata(f"geçersiz istek: adres {adres}, adet {adet}", "ayar_hatasi")
        self._islem = (self._islem + 1) & 0xFFFF
        pdu = struct.pack(">BHH", fonk_istek, adres, adet)
        mbap = struct.pack(">HHHB", self._islem, 0, len(pdu) + 1, self.birim)
        self._s.sendall(mbap + pdu)
        bas = self._al(7)
        islem, proto, uzunluk, birim = struct.unpack(">HHHB", bas)
        if islem != self._islem or proto != 0:
            raise self._ret(f"beklenmeyen yanıt başlığı (işlem {islem}≠{self._islem} ya da protokol {proto})")
        if birim != self.birim:
            raise self._ret(f"yanıt birim kimliği uyuşmuyor ({birim}≠{self.birim})")
        if not (2 <= uzunluk <= AZAMI_UZUNLUK):   # birim (1, okundu) + fonksiyon (1) + en az 1 bayt gövde
            raise self._ret(f"geçersiz MBAP uzunluğu {uzunluk}")
        govde = self._al(uzunluk - 1)
        fonk = govde[0]
        if fonk & 0x80:
            kod = govde[1] if len(govde) > 1 else 0
            if fonk != (fonk_istek | 0x80):
                raise self._ret(f"beklenmeyen istisna fonksiyonu {fonk:#x}")
            if kod in (5, 6):
                raise ModbusHata(f"Modbus istisnası {kod}: {ISTISNALAR.get(kod, 'bilinmeyen')}", "cihaz_mesgul", kod)
            raise ModbusHata(f"Modbus istisnası {kod}: {ISTISNALAR.get(kod, 'bilinmeyen')}", "cihaz_istisnasi", kod)
        if fonk != fonk_istek:
            raise self._ret(f"beklenmeyen fonksiyon {fonk}")
        if len(govde) < 2:
            raise self._ret("yanıt gövdesi kısa")
        bayt = govde[1]
        if bayt != 2 * adet or len(govde) != 2 + bayt:
            raise self._ret(f"yanıt uzunluğu uyumsuz (byte-count {bayt}, beklenen {2 * adet}, gövde {len(govde)})")
        return list(struct.unpack(f">{adet}H", govde[2:2 + bayt]))
