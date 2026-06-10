"""Application bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QApplication

from knowledgevault.config import APP_NAME
from knowledgevault.database.connection import DatabaseConnection
from knowledgevault.services.auth_service import AuthService
from knowledgevault.services.note_service import NoteService
from knowledgevault.ui.main_window import MainWindow
from knowledgevault.ui.widgets.login_dialog import LoginDialog


def _restore_session(auth: AuthService, settings: QSettings):
    raw = settings.value("session_user_id")
    if raw is None:
        return None
    try:
        user_id = int(raw)
    except (TypeError, ValueError):
        return None
    return auth.get_user(user_id)


def run(seed_example_data: bool = False) -> int:
    """Launch the KnowledgeVault application."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("KnowledgeVault")

    db = DatabaseConnection()
    auth = AuthService(db)
    settings = QSettings("KnowledgeVault", "KnowledgeVault")

    user = _restore_session(auth, settings)
    if user is None:
        dialog = LoginDialog(auth)
        if dialog.exec() != LoginDialog.DialogCode.Accepted or dialog.user is None:
            db.close()
            return 0
        user = dialog.user
        settings.setValue("session_user_id", user.id)

    if seed_example_data:
        from knowledgevault.data.seed import seed_example_notes
        seed_example_notes(NoteService(db, user.id))

    window = MainWindow(NoteService(db, user.id), user=user, auth=auth, settings=settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
