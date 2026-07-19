"""
PVQuant Sayfa Fonksiyonlari (Faz 2)
"""

from santralim import render_santralim


def render_veri_yukleme() -> None:
    from veri_yukleme import render_veri_yukleme as _render
    _render()


def render_kalibrasyon() -> None:
    from kalibrasyon import render_kalibrasyon as _render
    _render()


def render_tahminler() -> None:
    from tahminler import render_tahminler as _render
    _render()


def render_dogruluk() -> None:
    from dogruluk import render_dogruluk as _render
    _render()
def render_raporlar() -> None:
    from raporlar import render_raporlar as _render
    _render()


PAGE_RENDERERS = {
    "santralim":    render_santralim,
    "veri_yukleme": render_veri_yukleme,
    "kalibrasyon":  render_kalibrasyon,
    "tahminler":    render_tahminler,
    "dogruluk":    render_dogruluk,
    "raporlar":     render_raporlar,
}