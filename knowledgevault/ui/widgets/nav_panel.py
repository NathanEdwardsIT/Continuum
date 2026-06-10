"""Designer sidebar — icon nav + auto-organized tree."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from knowledgevault.ui.components.buttons import NavButton, PrimaryButton
from knowledgevault.ui.components.typography import Caption, H2, SectionLabel
from knowledgevault.ui.theme_palette import ThemePalette
from knowledgevault.models.entities import Category, Folder


class NavPanel(QWidget):
    view_changed = Signal(str)
    filter_selected = Signal(str, str)
    new_note_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(260)
        self._nav_buttons: list[NavButton] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(4)

        self._title = H2("Vault")
        layout.addWidget(self._title)
        self._sub = Caption("Automatically organized")
        layout.addWidget(self._sub)
        layout.addSpacing(12)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        for icon, label, vid in [
            ("◈", "Dashboard", "dashboard"),
            ("◇", "All Notes", "notes"),
            ("◎", "Graph", "graph"),
        ]:
            btn = NavButton(label, icon)
            btn.clicked.connect(lambda c, v=vid: self.view_changed.emit(v))
            self._btn_group.addButton(btn)
            self._nav_buttons.append(btn)
            layout.addWidget(btn)
        if self._nav_buttons:
            self._nav_buttons[0].setChecked(True)

        layout.addSpacing(12)
        self._new_btn = PrimaryButton("+  New Note")
        self._new_btn.clicked.connect(lambda checked=False: self.new_note_requested.emit())
        layout.addWidget(self._new_btn)

        layout.addSpacing(8)
        self._cat_header = SectionLabel("Categories")
        layout.addWidget(self._cat_header)

        self._category_tree = QTreeWidget()
        self._category_tree.setHeaderHidden(True)
        self._category_tree.itemClicked.connect(self._on_category_click)
        layout.addWidget(self._category_tree)

        self._folder_header = SectionLabel("Folders")
        layout.addWidget(self._folder_header)

        self._folder_tree = QTreeWidget()
        self._folder_tree.setHeaderHidden(True)
        self._folder_tree.itemClicked.connect(self._on_folder_click)
        layout.addWidget(self._folder_tree, stretch=1)

    def apply_palette(self, p: ThemePalette) -> None:
        self._title.apply_palette(p)
        self._sub.apply_palette(p)
        self._cat_header.apply_palette(p)
        self._folder_header.apply_palette(p)
        self._new_btn.apply_palette(p)
        for btn in self._nav_buttons:
            btn.apply_palette(p)

    def set_active_view(self, view: str) -> None:
        mapping = {"dashboard": 0, "notes": 1, "graph": 2}
        idx = mapping.get(view, 0)
        if idx < len(self._nav_buttons):
            self._nav_buttons[idx].setChecked(True)

    def update_categories(self, categories: list[Category]) -> None:
        self._category_tree.clear()
        for cat in categories:
            item = QTreeWidgetItem([f"  {cat.name}   {cat.note_count}"])
            item.setData(0, 256, ("category", cat.name))
            self._category_tree.addTopLevelItem(item)

    def update_folders(self, folders: list[Folder]) -> None:
        self._folder_tree.clear()
        tree_map: dict[str, QTreeWidgetItem] = {}
        for folder in folders:
            parts = [p.strip() for p in folder.name.split("/")]
            parent_item = None
            for i, part in enumerate(parts):
                key = "/".join(parts[: i + 1])
                if key not in tree_map:
                    suffix = f"  {folder.note_count}" if i == len(parts) - 1 else ""
                    item = QTreeWidgetItem([f"  {part}{suffix}"])
                    item.setData(0, 256, ("folder", folder.name))
                    if parent_item:
                        parent_item.addChild(item)
                    else:
                        self._folder_tree.addTopLevelItem(item)
                    tree_map[key] = item
                parent_item = tree_map[key]

    def _on_category_click(self, item: QTreeWidgetItem, _col: int) -> None:
        data = item.data(0, 256)
        if data:
            self.filter_selected.emit(data[0], data[1])

    def _on_folder_click(self, item: QTreeWidgetItem, _col: int) -> None:
        data = item.data(0, 256)
        if data:
            self.filter_selected.emit(data[0], data[1])
