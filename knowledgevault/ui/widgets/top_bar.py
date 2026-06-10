"""Top chrome bar — Snetch-style application header."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from continuum.ui.components.buttons import GhostButton, PrimaryButton, TabButton
from continuum.ui.components.typography import Badge
from continuum.ui.theme_palette import ThemeId, ThemePalette, get_palette


class LogoMark(QLabel):
  def __init__(self, parent=None) -> None:
    super().__init__("C", parent)
    self.setObjectName("logoMark")
    self.setFixedSize(32, 32)
    self.setAlignment(Qt.AlignmentFlag.AlignCenter)

  def apply_palette(self, p: ThemePalette) -> None:
    self.setStyleSheet(f"""
      QLabel#logoMark {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
          stop:0 {p.gradient_start}, stop:1 {p.gradient_end});
        color: white;
        font-weight: 800;
        font-size: 11px;
        border-radius: 10px;
      }}
    """)


class TopBar(QWidget):
    view_changed = Signal(str)
    new_note_requested = Signal()
    focus_mode_requested = Signal()
    theme_requested = Signal(object)
    export_requested = Signal()
    backup_requested = Signal()
    logout_requested = Signal()
    category_settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topChrome")
        self.setFixedHeight(56)
        self._palette = get_palette(ThemeId.STUDIO)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        self._logo = LogoMark()
        layout.addWidget(self._logo)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        self._brand = QLabel("Continuum")
        self._brand.setObjectName("brandName")
        brand_col.addWidget(self._brand)
        layout.addLayout(brand_col)

        self._auto_badge = Badge("AUTO")
        layout.addWidget(self._auto_badge)

        layout.addSpacing(24)

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tabs: list[TabButton] = []
        for label, vid in [("Dashboard", "dashboard"), ("Notes", "notes"), ("Graph", "graph")]:
            tab = TabButton(label)
            tab.clicked.connect(lambda checked, v=vid: self.view_changed.emit(v))
            self._tab_group.addButton(tab)
            self._tabs.append(tab)
            layout.addWidget(tab)
        if self._tabs:
            self._tabs[0].setChecked(True)

        layout.addSpacerItem(
            QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        self._focus_btn = GhostButton("Focus")
        self._focus_btn.clicked.connect(lambda checked=False: self.focus_mode_requested.emit())
        layout.addWidget(self._focus_btn)

        self._menu_btn = GhostButton("···")
        self._menu_btn.setFixedWidth(44)
        self._menu_btn.clicked.connect(self._show_menu)
        layout.addWidget(self._menu_btn)

        self._new_btn = PrimaryButton("New Note")
        self._new_btn.clicked.connect(lambda checked=False: self.new_note_requested.emit())
        layout.addWidget(self._new_btn)

        self._avatar = QLabel("?")
        self._avatar.setObjectName("avatar")
        self._avatar.setFixedSize(32, 32)
        self._avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._avatar.mousePressEvent = lambda _e: self._show_user_menu()
        layout.addWidget(self._avatar)

    def _show_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("Export Report…", lambda checked=False: self.export_requested.emit())
        menu.addAction("Backup Now", lambda checked=False: self.backup_requested.emit())
        menu.addAction("Category Settings…", lambda checked=False: self.category_settings_requested.emit())
        menu.addSeparator()
        themes = menu.addMenu("Theme")
        for tid in ThemeId:
            pal = get_palette(tid)
            themes.addAction(
                pal.display_name,
                lambda checked=False, t=tid: self.theme_requested.emit(t),
            )
        menu.addSeparator()
        menu.addAction("About Continuum")
        menu.exec(self._menu_btn.mapToGlobal(self._menu_btn.rect().bottomLeft()))

    def _show_user_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("Sign Out", lambda checked=False: self.logout_requested.emit())
        menu.exec(self._avatar.mapToGlobal(self._avatar.rect().bottomRight()))

    def set_user_display(self, display_name: str) -> None:
        initial = (display_name.strip()[:1] or "?").upper()
        self._avatar.setText(initial)
        self._avatar.setToolTip(display_name)

    def set_active_view(self, view: str) -> None:
        mapping = {"dashboard": 0, "notes": 1, "graph": 2}
        idx = mapping.get(view, 0)
        if idx < len(self._tabs):
            self._tabs[idx].setChecked(True)

    def apply_palette(self, p: ThemePalette) -> None:
        self._palette = p
        self._logo.apply_palette(p)
        self._auto_badge.apply_palette(p)
        self._focus_btn.apply_palette(p)
        self._menu_btn.apply_palette(p)
        self._new_btn.apply_palette(p)
        for tab in self._tabs:
            tab.apply_palette(p)
        self.setStyleSheet(f"""
          QWidget#topChrome {{
            background: {p.topbar};
            border-bottom: 1px solid {p.border_subtle};
          }}
          QLabel#brandName {{
            font-size: 15px;
            font-weight: 700;
            color: {p.text_primary};
            letter-spacing: -0.3px;
          }}
          QLabel#avatar {{
            background: {p.bg_tertiary};
            color: {p.text_secondary};
            border: 1px solid {p.border};
            border-radius: 16px;
            font-weight: 700;
            font-size: 12px;
          }}
        """)
