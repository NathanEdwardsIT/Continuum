"""Main window — designer shell layout."""

from __future__ import annotations

from datetime import datetime, time
from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from continuum.config import AUTOSAVE_INTERVAL_MS, BACKUP_INTERVAL_MS
from continuum.services.autosave import AutosaveManager
from continuum.services.backup import BackupService
from continuum.models.entities import SearchFilters
from continuum.services.note_service import NoteService
from continuum.ui.theme_engine import ThemeEngine
from continuum.ui.theme_palette import ThemeId
from continuum.ui.widgets.dashboard import DashboardWidget
from continuum.ui.widgets.graph_view import GraphViewWidget
from continuum.ui.widgets.nav_panel import NavPanel
from continuum.ui.widgets.note_editor import NoteEditorPanel
from continuum.ui.widgets.note_list import NoteListPanel
from continuum.ui.widgets.top_bar import TopBar
from continuum.ui.workers import GraphWorker, ReportWorker, SearchWorker, get_thread_pool


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: NoteService | None = None,
        user=None,
        auth=None,
        settings: QSettings | None = None,
    ) -> None:
        super().__init__()
        self.service = service or NoteService()
        self._auth = auth
        self._user = user
        self._settings = settings or QSettings("Continuum", "Continuum")
        self._engine = ThemeEngine.instance()
        saved = self._settings.value("theme", ThemeId.STUDIO.value)
        for legacy in ("neon_studio", "arctic"):
            pass
        if saved == "neon_studio":
            saved = ThemeId.STUDIO.value
        try:
            self._theme = ThemeId(saved)
        except ValueError:
            self._theme = ThemeId.STUDIO

        self._current_view = "dashboard"
        self._filter_type: str | None = None
        self._filter_value: str | None = None
        self._graph_show_cats = True
        self._graph_show_tags = False
        self._graph_layout = "spring"
        self._focus_mode = False

        self.setWindowTitle("Continuum")
        self.setMinimumSize(1280, 800)
        self.resize(1480, 920)
        self.menuBar().setVisible(False)

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_services()
        self._connect_signals()
        self._apply_theme(self._theme)
        if self._user:
            self._top_bar.set_user_display(self._user.display_name)
        self._refresh_all()

    def _setup_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("shell")
        self.setCentralWidget(shell)
        root = QVBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._top_bar = TopBar()
        root.addWidget(self._top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._nav = NavPanel()
        self._splitter.addWidget(self._nav)

        self._stack = QStackedWidget()
        self._stack.setObjectName("workspace")
        self._dashboard = DashboardWidget()
        self._note_list = NoteListPanel()
        self._graph = GraphViewWidget()
        self._stack.addWidget(self._dashboard)
        self._stack.addWidget(self._note_list)
        self._stack.addWidget(self._graph)
        self._splitter.addWidget(self._stack)

        self._editor = NoteEditorPanel()
        self._editor.setMinimumWidth(400)
        self._splitter.addWidget(self._editor)

        self._splitter.setSizes([260, 520, 480])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        body.addWidget(self._splitter)
        root.addLayout(body, stretch=1)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, self._on_new_note)
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_search)
        QShortcut(QKeySequence("Ctrl+P"), self, self._toggle_preview)
        QShortcut(QKeySequence("Ctrl+Shift+P"), self, self._toggle_pin)
        QShortcut(QKeySequence("Delete"), self, self._shortcut_delete)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._on_view_changed("dashboard"))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._on_view_changed("notes"))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._on_view_changed("graph"))
        QShortcut(QKeySequence("Ctrl+Shift+F"), self, self._toggle_focus_mode)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    def _setup_services(self) -> None:
        self._autosave = AutosaveManager(AUTOSAVE_INTERVAL_MS, self)
        self._autosave.set_save_callback(self._autosave_callback)
        self._autosave.saved.connect(self._on_autosaved)
        self._backup = BackupService(self.service.db, BACKUP_INTERVAL_MS, self)

    def _connect_signals(self) -> None:
        self._top_bar.view_changed.connect(self._on_view_changed)
        self._top_bar.new_note_requested.connect(self._on_new_note)
        self._top_bar.focus_mode_requested.connect(self._toggle_focus_mode)
        self._top_bar.theme_requested.connect(self._apply_theme)
        self._top_bar.export_requested.connect(self._on_export_report)
        self._top_bar.backup_requested.connect(self._on_backup)
        self._top_bar.logout_requested.connect(self._on_logout)
        self._top_bar.category_settings_requested.connect(self._on_category_settings)

        self._nav.view_changed.connect(self._on_view_changed)
        self._nav.filter_selected.connect(self._on_filter_selected)
        self._nav.new_note_requested.connect(self._on_new_note)

        self._note_list.note_selected.connect(self._on_note_selected)
        self._note_list.search_changed.connect(self._on_search_filters)
        self._note_list.trash_empty_requested.connect(self._on_empty_trash)
        self._editor.content_changed.connect(self._autosave.mark_dirty)
        self._editor.focus_mode_toggled.connect(self._on_focus_mode)
        self._editor.backlink_clicked.connect(self._on_note_selected)
        self._editor.delete_requested.connect(self._on_delete_note)
        self._editor.restore_requested.connect(self._on_restore_note)
        self._editor.pin_toggled.connect(self._on_pin_toggled)
        self._editor.overrides_changed.connect(self._on_overrides_changed)
        self._editor.attachment_added.connect(self._on_attachment_action)
        self._graph.note_selected.connect(self._on_graph_note_selected)
        self._graph.filter_changed.connect(self._on_graph_filter_changed)
        self._graph.layout_changed.connect(self._on_graph_layout_changed)
        self._dashboard.note_clicked.connect(self._on_dashboard_note_clicked)
        self._dashboard.collection_clicked.connect(self._on_collection_clicked)

    def _apply_theme(self, theme: ThemeId) -> None:
        self._theme = theme
        self._settings.setValue("theme", theme.value)
        self._engine.apply(self, theme)

    def _refresh_all(self) -> None:
        self._refresh_nav()
        self._refresh_note_list()
        self._refresh_dashboard()

    def _refresh_nav(self) -> None:
        cats = self.service.get_categories()
        self._nav.update_categories(cats)
        self._nav.update_folders(self.service.get_folders())
        self._note_list.set_category_options([c.name for c in cats])
        profile_names = [p.name for p in self.service.categories.get_profiles()]
        self._editor.set_category_options(profile_names)

    def _refresh_note_list(self) -> None:
        if self._filter_type == "trash":
            self._note_list.set_trash_mode(True)
            self._note_list.set_notes(self.service.get_trash_notes())
            return
        self._note_list.set_trash_mode(False)
        if self._filter_type and self._filter_value is not None:
            notes = self.service.get_notes_by_filter(self._filter_type, self._filter_value)
        elif self._filter_type == "pinned":
            notes = self.service.get_notes_by_filter("pinned", "")
        else:
            notes = self.service.get_all_notes()
        self._note_list.set_notes(notes)

    def _refresh_dashboard(self) -> None:
        self._dashboard.update_stats(self.service.get_stats())
        self._dashboard.update_insights(self.service.get_insights())
        self._dashboard.update_collections(self.service.get_collections())
        self._dashboard.update_activity(self.service.get_all_notes(limit=8))

    def _on_view_changed(self, view: str) -> None:
        self._current_view = view
        self._top_bar.set_active_view(view)
        self._nav.set_active_view(view)
        if view == "dashboard":
            self._stack.setCurrentIndex(0)
            self._refresh_dashboard()
        elif view == "notes":
            self._stack.setCurrentIndex(1)
            if self._filter_type != "trash":
                self._filter_type = None
                self._filter_value = None
            self._refresh_note_list()
        elif view == "graph":
            self._stack.setCurrentIndex(2)
            self._load_graph()

    def _on_filter_selected(self, ft: str, fv: str) -> None:
        self._stack.setCurrentIndex(1)
        self._filter_type, self._filter_value = ft, fv
        self._top_bar.set_active_view("notes")
        self._nav.set_active_view("notes")
        self._refresh_note_list()

    def _on_collection_clicked(self, cid: str) -> None:
        for coll in self.service.get_collections():
            if coll.id == cid and coll.notes:
                self._stack.setCurrentIndex(1)
                self._filter_type = None
                self._filter_value = None
                self._note_list.set_notes(coll.notes)
                if coll.notes[0].id:
                    self._on_note_selected(coll.notes[0].id)
                break

    def _on_dashboard_note_clicked(self, nid: int) -> None:
        self._stack.setCurrentIndex(1)
        self._note_list.select_note(nid)
        self._on_note_selected(nid)

    def _on_new_note(self) -> None:
        self._stack.setCurrentIndex(1)
        self._editor.new_note()

    def _on_note_selected(self, nid: int) -> None:
        note = self.service.get_note(nid)
        if note:
            self._editor.load_note(note)
            self._editor.load_backlinks(self.service.get_backlinks(nid))
            self._editor.load_attachments(self.service.get_attachments(nid))

    def _on_graph_note_selected(self, nid: int) -> None:
        self._stack.setCurrentIndex(1)
        self._note_list.select_note(nid)
        self._on_note_selected(nid)

    def _on_search_filters(self, filters: SearchFilters) -> None:
        if not any([
            filters.query.strip(),
            filters.category,
            filters.tag,
            filters.modified_after,
            filters.modified_before,
            filters.pinned_only,
        ]):
            self._refresh_note_list()
            return
        notes = self.service.search_filtered(filters)
        self._note_list.set_notes(notes)

    def _on_search(self, q: str) -> None:
        self._on_search_filters(SearchFilters(query=q))

    def _autosave_callback(self):
        title, content = self._editor.get_title(), self._editor.get_content()
        nid = self._editor.current_note_id
        if not title and not content:
            return nid, title, content
        note = self.service.save_note(nid, title or "Untitled", content)
        self._editor.set_note_id(note.id or 0)
        return note.id, note.title, note.content

    def _on_autosaved(self, nid: int) -> None:
        self._status.showMessage("Saved", 2000)
        self._refresh_nav()
        if self._current_view == "dashboard":
            self._refresh_dashboard()
        note = self.service.get_note(nid)
        if note:
            self._editor.load_note(note)
            self._editor.load_backlinks(self.service.get_backlinks(nid))
            self._editor.load_attachments(self.service.get_attachments(nid))

        if note:
            self._editor.load_note(note)
            self._editor.load_backlinks(self.service.get_backlinks(nid))
            self._editor.load_attachments(self.service.get_attachments(nid))

    def _on_delete_note(self, nid: int) -> None:
        self.service.move_to_trash(nid)
        self._editor.new_note()
        self._refresh_all()
        self._status.showMessage("Moved to trash", 2000)

    def _on_restore_note(self, nid: int) -> None:
        self.service.restore_note(nid)
        self._filter_type = None
        self._filter_value = None
        self._refresh_all()
        self._on_note_selected(nid)
        self._status.showMessage("Note restored", 2000)

    def _on_empty_trash(self) -> None:
        if QMessageBox.question(
            self, "Empty Trash", "Permanently delete all trashed notes?",
        ) != QMessageBox.StandardButton.Yes:
            return
        count = self.service.empty_trash()
        self._editor.new_note()
        self._refresh_all()
        self._status.showMessage(f"Deleted {count} notes", 3000)

    def _on_pin_toggled(self, nid: int, pinned: bool) -> None:
        self.service.set_pinned(nid, pinned)
        self._refresh_note_list()

    def _on_overrides_changed(self, nid: int) -> None:
        self.service.update_overrides(nid, self._editor.get_overrides())
        note = self.service.get_note(nid)
        if note:
            self._editor.load_note(note)
        self._refresh_nav()

    def _on_attachment_action(self, note_id: int, path_or_id: str) -> None:
        if Path(path_or_id).exists():
            if self._editor.current_note_id is None:
                self._autosave.force_save()
            nid = self._editor.current_note_id or note_id
            if not nid:
                return
            att = self.service.add_attachment(nid, Path(path_or_id))
            self._editor.load_attachments(self.service.get_attachments(att.note_id))
            self._status.showMessage("Attachment added", 2000)
        else:
            try:
                att_id = int(path_or_id)
                for att in self.service.get_attachments(note_id):
                    if att.id == att_id:
                        path = self.service.open_attachment(att)
                        NoteEditorPanel.open_file_path(str(path))
                        break
            except ValueError:
                pass

    def _on_category_settings(self) -> None:
        from continuum.ui.widgets.category_settings_dialog import CategorySettingsDialog
        dlg = CategorySettingsDialog(self.service, self)
        if dlg.exec():
            self._refresh_all()

    def _focus_search(self) -> None:
        self._stack.setCurrentIndex(1)
        self._note_list._search.setFocus()

    def _toggle_preview(self) -> None:
        self._editor._prev_btn.click()

    def _toggle_pin(self) -> None:
        if self._editor.current_note_id:
            self._editor._pin_btn.click()

    def _shortcut_delete(self) -> None:
        if self._editor.current_note_id and not self._editor._is_deleted:
            self._on_delete_note(self._editor.current_note_id)

    def _load_graph(self) -> None:
        w = GraphWorker(
            self.service,
            self._graph_show_cats,
            self._graph_show_tags,
            self._graph_layout,
        )
        w.signals.finished.connect(self._on_graph_loaded)
        get_thread_pool().start(w)

    def _on_graph_loaded(self, data: dict) -> None:
        self._graph.render_graph(
            data["nodes"],
            data["edges"],
            data["positions"],
            data.get("degrees", {}),
        )

    def _on_graph_filter_changed(self, _m, cats, tags) -> None:
        self._graph_show_cats, self._graph_show_tags = cats, tags
        self._load_graph()

    def _on_graph_layout_changed(self, layout: str) -> None:
        self._graph_layout = layout
        self._load_graph()

    def _on_logout(self) -> None:
        reply = QMessageBox.question(
            self,
            "Sign Out",
            "Sign out and return to the login screen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._autosave.is_dirty:
            self._autosave.force_save()
        self._backup.create_backup()
        self._settings.remove("session_user_id")
        self.hide()

        from continuum.ui.widgets.login_dialog import LoginDialog

        if self._auth is None:
            self.close()
            return

        dialog = LoginDialog(self._auth)
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.user is None:
            self.service.close()
            self.close()
            return

        user = dialog.user
        self._user = user
        self._settings.setValue("session_user_id", user.id)
        self.service.set_user_id(user.id)
        self._top_bar.set_user_display(user.display_name)
        self._editor.new_note()
        self._refresh_all()
        self.show()

    def _toggle_focus_mode(self) -> None:
        self._on_focus_mode(not self._focus_mode)

    def _on_focus_mode(self, on: bool) -> None:
        self._focus_mode = on
        self._nav.setVisible(not on)
        self._top_bar.setVisible(not on)
        self._splitter.setSizes([0, 0, 2000] if on else [260, 520, 480])

    def _on_export_report(self) -> None:
        d = ReportDialog(self)
        if d.exec():
            start, end = d.get_dates()
            path, _ = QFileDialog.getSaveFileName(self, "Save Report", "report.pdf", "PDF (*.pdf)")
            if path:
                w = ReportWorker(self.service, start, end, Path(path))
                w.signals.finished.connect(lambda p: self._status.showMessage("Report saved", 4000))
                get_thread_pool().start(w)

    def _on_backup(self) -> None:
        self._backup.create_backup()
        self._status.showMessage("Backup created", 3000)

    def closeEvent(self, event) -> None:
        if self._autosave.is_dirty:
            self._autosave.force_save()
        self._backup.create_backup()
        self.service.close()
        event.accept()


class ReportDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Report")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Date range:"))
        today = datetime.now().date()
        self._s = QDateEdit()
        self._s.setCalendarPopup(True)
        self._s.setDate(today)
        self._e = QDateEdit()
        self._e.setCalendarPopup(True)
        self._e.setDate(today)
        layout.addWidget(self._s)
        layout.addWidget(self._e)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_dates(self):
        return (
            datetime.combine(self._s.date().toPython(), time.min),
            datetime.combine(self._e.date().toPython(), time.max),
        )
