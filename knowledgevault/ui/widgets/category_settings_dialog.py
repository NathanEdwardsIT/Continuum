"""User-defined category profile editor."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QVBoxLayout,
)

from continuum.services.category_profile_service import CategoryProfileService
from continuum.services.note_service import NoteService
from continuum.ui.components.buttons import GhostButton, PrimaryButton
from continuum.ui.components.typography import Body, H1
from continuum.ui.theme_engine import ThemeEngine
from continuum.ui.theme_palette import ThemeId


class CategorySettingsDialog(QDialog):
    def __init__(self, service: NoteService, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._profiles = CategoryProfileService(service.repository, service._user_id)
        self.setWindowTitle("Category Profiles")
        self.setMinimumSize(480, 420)
        self._setup_ui()
        ThemeEngine.instance().apply(self, ThemeId.STUDIO)
        self._reload()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(H1("Categories"))
        layout.addWidget(Body("Define keyword profiles used for automatic categorization."))

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        add_btn = GhostButton("Add Category")
        add_btn.clicked.connect(lambda checked=False: self._add_profile())
        edit_btn = GhostButton("Edit")
        edit_btn.clicked.connect(lambda checked=False: self._edit_profile())
        del_btn = GhostButton("Delete")
        del_btn.clicked.connect(lambda checked=False: self._delete_profile())
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)

    def _reload(self) -> None:
        self._list.clear()
        for profile in self._profiles.get_profiles():
            label = f"{profile.name}  ({len(profile.keywords)} keywords)"
            if profile.is_builtin:
                label += "  · built-in"
            self._list.addItem(label)
            item = self._list.item(self._list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, profile.id)

    def _selected_profile(self):
        item = self._list.currentItem()
        if not item:
            return None
        pid = item.data(Qt.ItemDataRole.UserRole)
        return self._profiles._repo.get_category_profile(pid) if pid else None

    def _add_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New Category", "Category name:")
        if not ok or not name.strip():
            return
        keywords, ok2 = QInputDialog.getMultiLineText(
            self, "Keywords", "Comma-separated keywords:",
        )
        if not ok2:
            return
        kw = CategoryProfileService.text_to_keywords(keywords)
        self._profiles.add_profile(name.strip(), kw)
        self._reload()

    def _edit_profile(self) -> None:
        profile = self._selected_profile()
        if not profile or profile.id is None:
            return
        name, ok = QInputDialog.getText(self, "Edit Category", "Category name:", text=profile.name)
        if not ok or not name.strip():
            return
        keywords, ok2 = QInputDialog.getMultiLineText(
            self,
            "Keywords",
            "Comma-separated keywords:",
            CategoryProfileService.keywords_to_text(profile.keywords),
        )
        if not ok2:
            return
        self._profiles.update_profile(profile.id, name.strip(), CategoryProfileService.text_to_keywords(keywords))
        self._reload()

    def _delete_profile(self) -> None:
        profile = self._selected_profile()
        if not profile or profile.id is None:
            return
        if profile.is_builtin:
            QMessageBox.warning(self, "Cannot Delete", "Built-in categories cannot be deleted.")
            return
        if QMessageBox.question(self, "Delete Category", f"Delete profile '{profile.name}'?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self._profiles.delete_profile(profile.id)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot Delete", str(exc))
        self._reload()
