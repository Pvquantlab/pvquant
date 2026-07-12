"""Aşama 1 — Dosya formatı algılama.

Harici bağımlılık kullanmadan (chardet vb. yok) deterministik
sezgisellerle çalışır. Türkçe sahada en sık görülen üç tuzağa göre
tasarlandı:

  1. Kodlama: Türkçe Excel/FusionSolar dosyaları sıklıkla Windows-1254
     (cp1254) ile gelir; utf-8 okuma 'ı, ş, ğ' karakterlerinde patlar.
  2. Ayraç: Türkçe bölgesel ayarlı Excel, CSV'yi noktalı virgülle yazar
     (çünkü ondalık ayracı virgüldür).
  3. Başlık satırı: FusionSolar ve benzeri portallar dosyanın başına
     3-5 satır meta bilgi (santral adı, rapor aralığı) koyar; gerçek
     başlık aşağıdadır. Bu MERKAS xlsx örneğinde de görüldü ve
     Excel dosyaları için de aynı taramayı yapıyoruz artık
     (`_detect_excel_format`).
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from .contracts import FileFormat

#: Deneme sırası önemli: utf-8-sig BOM'u yutar; cp1254 Türkçe Windows;
#: latin-1 hiçbir zaman UnicodeDecodeError vermez (son çare).
ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "cp1254", "latin-1")

DELIMITER_CANDIDATES = (";", ",", "\t")

#: Başlık araması bu kadar satırla sınırlı — daha derindeyse dosya
#: zaten standart dışıdır, kullanıcı manuel belirtir.
MAX_HEADER_SEARCH_ROWS = 15

#: Başlık satırında aranan anahtar kelimeler (küçük harfe çevrilerek).
HEADER_HINTS = (
    "time", "date", "tarih", "zaman", "saat",
    "power", "güç", "guc", "energy", "enerji", "yield", "üretim", "uretim",
    "kw", "mw", "irrad", "ışınım", "isinim",
    # Marka referans dokümanından eklenen ipuçları
    "period", "interval", "timestamp", "datetime",
    "ac_power", "pac", "wnow", "etotal", "wh",
    "ambient", "module", "temperature", "sicaklik",
)


def detect_encoding(path: Path, sample_bytes: int = 65536) -> str:
    """Kodlamayı deneme-yanılma ile bulur.

    utf-8 katıdır: cp1254 baytları utf-8'de neredeyse her zaman hata
    verir, bu yüzden 'ilk hatasız çözülen kazanır' stratejisi pratikte
    güvenilirdir. latin-1 asla hata vermez, o yüzden en sonda durur.
    """
    raw = path.read_bytes()[:sample_bytes]
    for enc in ENCODING_CANDIDATES:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "latin-1"  # teorik olarak erişilmez


def detect_delimiter(sample_lines: list[str]) -> tuple[str, float]:
    """Ayracı, satırlar arası tutarlılığa göre seçer.

    Doğru ayraç, her satırda aynı sayıda ve >0 parça üretendir.
    Dönen ikinci değer güven (0-1): tutarlılık oranı.
    """
    best, best_score = ",", 0.0
    for delim in DELIMITER_CANDIDATES:
        counts = [line.count(delim) for line in sample_lines if line.strip()]
        if not counts or max(counts) == 0:
            continue
        # En yaygın parça sayısının satırlara oranı = tutarlılık
        mode_count = max(set(counts), key=counts.count)
        consistency = counts.count(mode_count) / len(counts)
        # Daha çok kolon üreten ayraç, eşitlikte tercih edilir
        score = consistency + 0.01 * mode_count
        if mode_count > 0 and score > best_score:
            best, best_score = delim, score
    return best, min(best_score, 1.0)


def detect_decimal(sample_lines: list[str], delimiter: str) -> str:
    """Ondalık işaretini tahmin eder.

    Kural: ayraç noktalı virgülse sayı içi virgüller ondalıktır
    (Türk Excel deseni). Ayraç virgülse ondalık nokta olmak zorundadır.
    Tab ayracında her iki desen sayılır, çoğunluk kazanır.
    """
    if delimiter == ",":
        return "."
    if delimiter == ";":
        # ; ayraçlı dosyada "12,5" görünüyorsa ondalık virgüldür
        comma_decimals = sum(
            1 for line in sample_lines
            for tok in line.split(delimiter)
            if _looks_like_decimal(tok.strip(), ",")
        )
        dot_decimals = sum(
            1 for line in sample_lines
            for tok in line.split(delimiter)
            if _looks_like_decimal(tok.strip(), ".")
        )
        return "," if comma_decimals >= dot_decimals else "."
    # tab
    comma = sum(1 for l in sample_lines for t in l.split("\t") if _looks_like_decimal(t.strip(), ","))
    dot = sum(1 for l in sample_lines for t in l.split("\t") if _looks_like_decimal(t.strip(), "."))
    return "," if comma > dot else "."


def _looks_like_decimal(token: str, sep: str) -> bool:
    """'1234,56' / '1234.56' gibi tek ayraçlı sayı mı?"""
    if token.count(sep) != 1:
        return False
    left, right = token.split(sep)
    left = left.lstrip("-")
    return left.isdigit() and right.isdigit() and len(right) <= 6


def _row_header_score(cells: list[str]) -> float:
    """Başlık adayı skorlaması (CSV ve Excel için ortak).

    HEADER_HINTS ipuçlarına vurgu, sayısal görünen hücrelere ceza.
    Meta satırlar (tek hücre, çoğu boş) düşük skor alır.
    """
    if len(cells) < 2:
        return -1.0
    hint_hits = sum(1 for c in cells if any(h in c for h in HEADER_HINTS))
    numeric_cells = sum(1 for c in cells if _is_numeric_like(c))
    empty_cells = sum(1 for c in cells if not c.strip())
    return hint_hits * 2.0 - numeric_cells - 0.3 * empty_cells + 0.1 * len(cells)


def detect_header_row(sample_lines: list[str], delimiter: str) -> tuple[int, float]:
    """Gerçek başlık satırını CSV için bulur."""
    best_row, best_score = 0, -1.0
    for i, line in enumerate(sample_lines[:MAX_HEADER_SEARCH_ROWS]):
        cells = [c.strip().lower() for c in line.split(delimiter)]
        score = _row_header_score(cells)
        if score > best_score:
            best_row, best_score = i, score
    confidence = 0.9 if best_score >= 2 else 0.5
    return best_row, confidence


def _is_numeric_like(cell: str) -> bool:
    c = cell.replace(",", ".").replace("-", "").replace(":", "").replace(" ", "")
    return c.replace(".", "").isdigit() and len(c) > 0


def _detect_excel_format(path: Path) -> FileFormat:
    """Excel için başlık satırını taraması, sayfa seçimi.

    Çok sayfalı dosyalarda ilk sayfa varsayılır; kullanıcı UI'da
    sheet_name'i değiştirebilir. Başlık satırı CSV ile aynı puanlama
    mantığıyla bulunur — 'Tesis Raporu MERKAS GES' gibi meta üstlerini
    aşar ve gerçek başlığı (5. satırda) bulur.
    """
    try:
        xls = pd.ExcelFile(path)
    except Exception:
        return FileFormat(encoding="binary", delimiter=",", decimal=".",
                          header_row=0, sheet_name=None, confidence=0.3)

    sheet = xls.sheet_names[0] if xls.sheet_names else None

    try:
        # header=None: her satır ham veri olarak gelsin, başlığı biz seçelim
        raw = pd.read_excel(path, sheet_name=sheet, header=None,
                            nrows=MAX_HEADER_SEARCH_ROWS, dtype=str)
    except Exception:
        return FileFormat(encoding="binary", delimiter=",", decimal=".",
                          header_row=0, sheet_name=sheet, confidence=0.3)

    best_row, best_score = 0, -1.0
    for i in range(len(raw)):
        cells = [str(c).strip().lower() if pd.notna(c) else "" for c in raw.iloc[i]]
        score = _row_header_score(cells)
        if score > best_score:
            best_row, best_score = i, score

    confidence = 0.9 if best_score >= 2 else 0.5
    return FileFormat(
        encoding="binary",
        delimiter=",",           # Excel için anlamsız ama yapıyı koru
        decimal=".",             # aynı
        header_row=best_row,
        sheet_name=sheet,
        n_preview_rows=len(raw),
        confidence=confidence,
    )


def detect_file_format(path: str | Path) -> FileFormat:
    """Aşama 1'in tamamı: kodlama + ayraç + ondalık + başlık satırı.

    Excel dosyaları (.xlsx/.xls) için ayrı yol: `_detect_excel_format`
    başlık satırını da tarar (MERKAS xlsx gibi 5. satırda başlık olan
    dosyalar için gereklidir).
    """
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        return _detect_excel_format(path)

    encoding = detect_encoding(path)
    with io.open(path, "r", encoding=encoding, errors="replace") as f:
        sample_lines = [f.readline().rstrip("\n\r") for _ in range(50)]
    sample_lines = [l for l in sample_lines if l is not None]

    delimiter, delim_conf = detect_delimiter(sample_lines)
    header_row, header_conf = detect_header_row(sample_lines, delimiter)
    # Ondalık tespiti başlık SONRASI (veri) satırlarından yapılmalı
    decimal = detect_decimal(sample_lines[header_row + 1:], delimiter)

    return FileFormat(
        encoding=encoding,
        delimiter=delimiter,
        decimal=decimal,
        header_row=header_row,
        n_preview_rows=len(sample_lines),
        confidence=round(min(delim_conf, header_conf), 2),
    )