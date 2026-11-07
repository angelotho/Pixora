"""Tokens de design, folha de estilos (QSS) e integração com a barra de título do Windows."""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget


@dataclass(frozen=True)
class Tokens:
    name: str
    bg: str
    surface: str
    surface2: str
    surface3: str
    border: str
    border_strong: str
    text: str
    text_muted: str
    text_faint: str
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str
    on_accent: str
    success: str
    success_soft: str
    danger: str
    danger_soft: str
    warning: str
    warning_soft: str
    overlay: str

    @property
    def dark(self) -> bool:
        return self.name == "dark"


DARK = Tokens(
    name="dark",
    bg="#0E1014", surface="#161920", surface2="#1C2029", surface3="#242936",
    border="#262B36", border_strong="#353B49",
    text="#ECEEF3", text_muted="#9BA3B4", text_faint="#666E80",
    accent="#7C5CFF", accent_hover="#8D72FF", accent_pressed="#6A48F2",
    accent_soft="rgba(124, 92, 255, 0.16)", on_accent="#FFFFFF",
    success="#3DD68C", success_soft="rgba(61, 214, 140, 0.13)",
    danger="#FF6B7A", danger_soft="rgba(255, 107, 122, 0.13)",
    warning="#FFB547", warning_soft="rgba(255, 181, 71, 0.13)",
    overlay="rgba(10, 12, 16, 0.72)",
)

LIGHT = Tokens(
    name="light",
    bg="#F3F4F8", surface="#FFFFFF", surface2="#F6F7FA", surface3="#ECEEF3",
    border="#E1E4EB", border_strong="#CDD2DC",
    text="#151821", text_muted="#5B6476", text_faint="#9198A6",
    accent="#6447F5", accent_hover="#7358FF", accent_pressed="#5236E0",
    accent_soft="rgba(100, 71, 245, 0.10)", on_accent="#FFFFFF",
    success="#13A866", success_soft="rgba(19, 168, 102, 0.10)",
    danger="#E03D52", danger_soft="rgba(224, 61, 82, 0.09)",
    warning="#C97A00", warning_soft="rgba(201, 122, 0, 0.10)",
    overlay="rgba(255, 255, 255, 0.82)",
)

_current: Tokens = DARK


def current() -> Tokens:
    return _current


def qcolor(value: str) -> QColor:
    if value.startswith("rgba"):
        r, g, b, a = (float(x) for x in value[value.index("(") + 1: -1].split(","))
        c = QColor(int(r), int(g), int(b))
        c.setAlphaF(a)
        return c
    return QColor(value)


def build_qss(t: Tokens, check_icon: str = "") -> str:
    return f"""
* {{ outline: none; }}
QWidget {{ color: {t.text}; font-size: 10pt; }}
QMainWindow, QDialog, #Root {{ background: {t.bg}; }}
QToolTip {{ background: {t.surface3}; color: {t.text}; border: 1px solid {t.border_strong};
            padding: 6px 8px; border-radius: 6px; }}

/* Superfícies */
#Card {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 14px; }}
#Footer {{ background: {t.surface}; border: 1px solid {t.border}; border-radius: 14px; }}
#Chip {{ background: {t.surface2}; border: 1px solid {t.border}; border-radius: 9px; }}

/* Tipografia */
QLabel {{ background: transparent; }}
QLabel[role="appTitle"] {{ font-size: 15pt; font-weight: 700; }}
QLabel[role="appSubtitle"] {{ color: {t.text_muted}; font-size: 9.5pt; }}
QLabel[role="version"] {{
    color: {t.accent}; background: {t.accent_soft}; border-radius: 8px;
    padding: 1px 7px; font-size: 8.5pt; font-weight: 600;
}}
QLabel[role="section"] {{ color: {t.text_muted}; font-size: 9pt; font-weight: 600; letter-spacing: 0.4px; }}
QLabel[role="title"] {{ font-size: 13pt; font-weight: 600; }}
QLabel[role="heading"] {{ font-size: 11pt; font-weight: 600; }}
QLabel[role="muted"] {{ color: {t.text_muted}; }}
QLabel[role="faint"] {{ color: {t.text_faint}; font-size: 9pt; }}
QLabel[role="error"] {{ color: {t.danger}; font-size: 9.5pt; }}
QLabel[role="success"] {{ color: {t.success}; font-size: 9.5pt; }}
QLabel[role="counter"] {{ color: {t.text_muted}; font-size: 9.5pt; }}

/* Campo de link */
QLineEdit {{
    background: {t.surface2}; border: 1px solid {t.border}; border-radius: 10px;
    padding: 0 12px; min-height: 42px; selection-background-color: {t.accent};
    selection-color: {t.on_accent}; font-size: 10.5pt;
}}
QLineEdit:hover {{ border-color: {t.border_strong}; }}
QLineEdit:focus {{ border: 1px solid {t.accent}; background: {t.surface}; }}
QLineEdit[invalid="true"] {{ border: 1px solid {t.danger}; }}
QLineEdit:disabled {{ color: {t.text_faint}; }}

/* Botões */
QPushButton {{
    background: {t.surface2}; border: 1px solid {t.border}; border-radius: 10px;
    padding: 0 16px; min-height: 40px; font-weight: 600;
}}
QPushButton:hover {{ background: {t.surface3}; border-color: {t.border_strong}; }}
QPushButton:pressed {{ background: {t.border}; }}
QPushButton:disabled {{ color: {t.text_faint}; background: {t.surface2}; border-color: {t.border}; }}
QPushButton:focus {{ border-color: {t.accent}; }}
QPushButton[variant="primary"] {{
    background: {t.accent}; color: {t.on_accent}; border: 1px solid {t.accent};
}}
QPushButton[variant="primary"]:hover {{ background: {t.accent_hover}; border-color: {t.accent_hover}; }}
QPushButton[variant="primary"]:pressed {{ background: {t.accent_pressed}; }}
QPushButton[variant="primary"]:disabled {{
    background: {t.surface3}; color: {t.text_faint}; border-color: {t.surface3};
}}
QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid transparent; }}
QPushButton[variant="ghost"]:hover {{ background: {t.surface2}; border-color: {t.border}; }}
QPushButton[variant="ghost"]:pressed {{ background: {t.surface3}; }}
QPushButton[variant="ghost"]:disabled {{ background: transparent; border-color: transparent; }}
QPushButton[variant="danger"] {{ color: {t.danger}; }}
QPushButton[variant="danger"]:hover {{ background: {t.danger_soft}; border-color: {t.danger}; }}
QPushButton[variant="icon"] {{
    background: transparent; border: 1px solid transparent; min-height: 36px; min-width: 36px;
    max-width: 36px; padding: 0; border-radius: 9px;
}}
QPushButton[variant="icon"]:hover {{ background: {t.surface2}; border-color: {t.border}; }}
QPushButton[variant="small"] {{ min-height: 30px; padding: 0 12px; border-radius: 8px; font-size: 9.5pt; }}
QPushButton[variant="link"] {{
    background: transparent; border: none; color: {t.accent}; min-height: 24px; padding: 0 4px;
}}
QPushButton[variant="link"]:hover {{ color: {t.accent_hover}; text-decoration: underline; }}

/* Progresso */
QProgressBar {{
    background: {t.surface3}; border: none; border-radius: 3px; max-height: 6px; min-height: 6px;
    text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {t.accent}; border-radius: 3px; }}

/* Rolagem */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t.border_strong}; border-radius: 4px; min-height: 36px; margin: 0 2px; }}
QScrollBar::handle:vertical:hover {{ background: {t.text_faint}; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {t.border_strong}; border-radius: 4px; min-width: 36px; margin: 2px 0; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* Formulários */
QCheckBox {{ spacing: 10px; background: transparent; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px; border: 1px solid {t.border_strong};
    background: {t.surface2};
}}
QCheckBox::indicator:hover {{ border-color: {t.accent}; }}
QCheckBox::indicator:checked {{ background: {t.accent}; border-color: {t.accent}; image: url({check_icon}); }}
QComboBox {{
    background: {t.surface2}; border: 1px solid {t.border}; border-radius: 9px; padding: 0 12px;
    min-height: 36px;
}}
QComboBox:hover {{ border-color: {t.border_strong}; }}
QComboBox:focus {{ border-color: {t.accent}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: {t.surface}; border: 1px solid {t.border_strong}; border-radius: 8px; padding: 4px;
    selection-background-color: {t.accent_soft}; selection-color: {t.text};
}}

/* Tabela do histórico */
QTableWidget {{
    background: {t.surface}; border: 1px solid {t.border}; border-radius: 12px;
    gridline-color: transparent; selection-background-color: {t.accent_soft}; selection-color: {t.text};
    alternate-background-color: {t.surface2};
}}
QTableWidget::item {{ padding: 6px 10px; border: none; }}
QHeaderView::section {{
    background: {t.surface}; color: {t.text_muted}; border: none; border-bottom: 1px solid {t.border};
    padding: 8px 10px; font-weight: 600; font-size: 9pt;
}}
QTableCornerButton::section {{ background: {t.surface}; border: none; }}

QMessageBox {{ background: {t.surface}; }}
QMessageBox QLabel {{ color: {t.text}; }}
QMenu {{ background: {t.surface}; border: 1px solid {t.border_strong}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {t.accent_soft}; }}
"""


def apply_theme(app: QApplication, name: str) -> Tokens:
    global _current
    _current = LIGHT if name == "light" else DARK
    t = _current
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, qcolor(t.bg))
    pal.setColor(QPalette.ColorRole.WindowText, qcolor(t.text))
    pal.setColor(QPalette.ColorRole.Base, qcolor(t.surface2))
    pal.setColor(QPalette.ColorRole.AlternateBase, qcolor(t.surface))
    pal.setColor(QPalette.ColorRole.Text, qcolor(t.text))
    pal.setColor(QPalette.ColorRole.Button, qcolor(t.surface2))
    pal.setColor(QPalette.ColorRole.ButtonText, qcolor(t.text))
    pal.setColor(QPalette.ColorRole.Highlight, qcolor(t.accent))
    pal.setColor(QPalette.ColorRole.HighlightedText, qcolor(t.on_accent))
    pal.setColor(QPalette.ColorRole.ToolTipBase, qcolor(t.surface3))
    pal.setColor(QPalette.ColorRole.ToolTipText, qcolor(t.text))
    pal.setColor(QPalette.ColorRole.PlaceholderText, qcolor(t.text_faint))
    pal.setColor(QPalette.ColorRole.Link, qcolor(t.accent))
    app.setPalette(pal)
    from .icons import icon_file
    app.setStyleSheet(build_qss(t, icon_file("check", t.on_accent, stroke=3)))
    for w in app.topLevelWidgets():
        apply_window_frame(w)
    return t


def default_font() -> QFont:
    font = QFont("Segoe UI Variable Text" if sys.platform == "win32" else "")
    if sys.platform == "win32":
        font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Arial"])
    font.setPointSizeF(10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return font


def apply_window_frame(widget: QWidget) -> None:
    """Deixa a barra de título nativa do Windows 10/11 no mesmo tema do app."""
    if sys.platform != "win32" or not widget.isWindow():
        return
    try:
        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if _current.dark else 0)
        dwm = ctypes.windll.dwmapi  # type: ignore[attr-defined]
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (novo e legado)
            if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
        # Cor da legenda (Windows 11): combina com o fundo da janela.
        bg = qcolor(_current.bg)
        colorref = ctypes.c_int(bg.red() | (bg.green() << 8) | (bg.blue() << 16))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref), ctypes.sizeof(colorref))
    except Exception:  # noqa: BLE001 — cosmético; nunca deve impedir a abertura da janela
        pass
