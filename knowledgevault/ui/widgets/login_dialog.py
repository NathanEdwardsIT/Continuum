"""Login and registration dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from continuum.services.auth_service import AuthError, AuthService, User
from continuum.ui.components.buttons import GhostButton, PrimaryButton
from continuum.ui.components.typography import Body, Caption, H1
from continuum.ui.theme_engine import ThemeEngine
from continuum.ui.theme_palette import ThemeId, get_palette


class LoginDialog(QDialog):
    """Sign in or create a local vault account."""

    def __init__(self, auth: AuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth = auth
        self._user: User | None = None
        self._palette = get_palette(ThemeId.STUDIO)

        self.setWindowTitle("Continuum — Sign In")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._setup_ui()
        ThemeEngine.instance().apply(self, ThemeId.STUDIO)

    @property
    def user(self) -> User | None:
        return self._user

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(16)

        self._title = H1("Welcome to Continuum")
        root.addWidget(self._title)
        self._subtitle = Body("Sign in to access your private vault.")
        root.addWidget(self._subtitle)

        tab_row = QHBoxLayout()
        self._login_tab = GhostButton("Sign In")
        self._register_tab = GhostButton("Create Account")
        self._login_tab.setCheckable(True)
        self._register_tab.setCheckable(True)
        self._login_tab.setChecked(True)
        self._login_tab.clicked.connect(lambda checked=False: self._switch_page(0))
        self._register_tab.clicked.connect(lambda checked=False: self._switch_page(1))
        tab_row.addWidget(self._login_tab)
        tab_row.addWidget(self._register_tab)
        tab_row.addStretch()
        root.addLayout(tab_row)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_login_page())
        self._stack.addWidget(self._build_register_page())
        root.addWidget(self._stack)

        self._error = Caption("")
        self._error.setStyleSheet(f"color: {self._palette.warning};")
        self._error.hide()
        root.addWidget(self._error)

        self._submit = PrimaryButton("Sign In")
        self._submit.clicked.connect(lambda checked=False: self._submit_form())
        root.addWidget(self._submit)

    def _build_login_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setSpacing(10)
        self._login_user = QLineEdit()
        self._login_user.setPlaceholderText("Username")
        self._login_user.setMinimumHeight(40)
        self._login_pass = QLineEdit()
        self._login_pass.setPlaceholderText("Password")
        self._login_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._login_pass.setMinimumHeight(40)
        self._login_pass.returnPressed.connect(self._submit_form)
        form.addRow("Username", self._login_user)
        form.addRow("Password", self._login_pass)
        return page

    def _build_register_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setSpacing(10)
        self._reg_user = QLineEdit()
        self._reg_user.setPlaceholderText("Choose a username")
        self._reg_user.setMinimumHeight(40)
        self._reg_display = QLineEdit()
        self._reg_display.setPlaceholderText("Your name (optional)")
        self._reg_display.setMinimumHeight(40)
        self._reg_pass = QLineEdit()
        self._reg_pass.setPlaceholderText("At least 6 characters")
        self._reg_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._reg_pass.setMinimumHeight(40)
        self._reg_confirm = QLineEdit()
        self._reg_confirm.setPlaceholderText("Repeat password")
        self._reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._reg_confirm.setMinimumHeight(40)
        self._reg_confirm.returnPressed.connect(self._submit_form)
        form.addRow("Username", self._reg_user)
        form.addRow("Display name", self._reg_display)
        form.addRow("Password", self._reg_pass)
        form.addRow("Confirm", self._reg_confirm)
        hint = Caption("Your notes stay on this device. Each account has its own vault.")
        form.addRow(hint)
        return page

    def _switch_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._login_tab.setChecked(index == 0)
        self._register_tab.setChecked(index == 1)
        self._submit.setText("Sign In" if index == 0 else "Create Account")
        self._error.hide()

    def _show_error(self, message: str) -> None:
        self._error.setText(message)
        self._error.show()

    def _submit_form(self) -> None:
        self._error.hide()
        try:
            if self._stack.currentIndex() == 0:
                self._user = self._auth.login(
                    self._login_user.text(),
                    self._login_pass.text(),
                )
            else:
                if self._reg_pass.text() != self._reg_confirm.text():
                    raise AuthError("Passwords do not match.")
                self._user = self._auth.register(
                    self._reg_user.text(),
                    self._reg_pass.text(),
                    self._reg_display.text() or None,
                )
            self.accept()
        except AuthError as exc:
            self._show_error(str(exc))
