"""Quick dialog to create a new category profile."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from continuum.services.category_profile_service import CategoryProfileService
from continuum.services.note_service import NoteService
from continuum.ui.components.typography import Body, H1
from continuum.ui.theme_engine import ThemeEngine
from continuum.ui.theme_palette import ThemeId


class AddCategoryDialog(QDialog):
    """Create a category with optional keywords in one step."""

    def __init__(self, service: NoteService, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._profiles = CategoryProfileService(service.repository, service._user_id)
        self.setWindowTitle("Add Category")
        self.setMinimumWidth(400)
        self._setup_ui()
        ThemeEngine.instance().apply(self, ThemeId.STUDIO)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(H1("New Category"))
        layout.addWidget(Body("Categories auto-tag notes when their keywords appear in your writing."))

        form = QFormLayout()
        self._name = QLineEdit()
        self._name.setPlaceholderText("e.g. Research, Health, Projects")
        self._name.setMinimumHeight(36)
        form.addRow("Name", self._name)

        self._keywords = QTextEdit()
        self._keywords.setPlaceholderText("python, api, backend  (comma-separated, optional)")
        self._keywords.setMaximumHeight(80)
        form.addRow("Keywords", self._keywords)
        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._submit)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self._name.setFocus()

    def _submit(self) -> None:
        name = self._name.text().strip()
        if not name:
            self._name.setFocus()
            return
        keywords = CategoryProfileService.text_to_keywords(self._keywords.toPlainText())
        if not keywords:
            keywords = [w.lower() for w in name.split() if w]
        self._profiles.add_profile(name, keywords)
        self.accept()

    @property
    def category_name(self) -> str:
        return self._name.text().strip()
