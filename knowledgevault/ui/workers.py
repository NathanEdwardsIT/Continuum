"""Background worker threads for heavy operations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from knowledgevault.models.entities import SearchResult
from knowledgevault.services.note_service import NoteService
from knowledgevault.services.report_generator import ReportGenerator


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class SearchWorker(QRunnable):
    def __init__(self, service: NoteService, query: str) -> None:
        super().__init__()
        self.service = service
        self.query = query
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            results = self.service.search.search(self.query)
            self.signals.finished.emit(results)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class GraphWorker(QRunnable):
    def __init__(
        self,
        service: NoteService,
        show_categories: bool = True,
        show_tags: bool = False,
        layout: str = "spring",
    ) -> None:
        super().__init__()
        self.service = service
        self.show_categories = show_categories
        self.show_tags = show_tags
        self.layout = layout
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            graph = self.service.rebuild_graph(
                show_notes=True,
                show_categories=self.show_categories,
                show_tags=self.show_tags,
                layout=self.layout,
            )
            positions = self.service.graph.get_layout_positions(graph, self.layout)
            nodes = self.service.graph.get_nodes(graph)
            edges = self.service.graph.get_edges(graph)
            degrees = self.service.graph.get_node_degree(graph)
            self.signals.finished.emit({
                "graph": graph,
                "positions": positions,
                "nodes": nodes,
                "edges": edges,
                "degrees": degrees,
            })
        except Exception as exc:
            self.signals.error.emit(str(exc))


class ReportWorker(QRunnable):
    def __init__(
        self, service: NoteService, start: datetime, end: datetime, output: Path,
    ) -> None:
        super().__init__()
        self.service = service
        self.start = start
        self.end = end
        self.output = output
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            generator = ReportGenerator(self.service.repository)
            path = generator.generate_report(self.start, self.end, self.output)
            self.signals.finished.emit(str(path))
        except Exception as exc:
            self.signals.error.emit(str(exc))


_thread_pool: QThreadPool | None = None


def get_thread_pool() -> QThreadPool:
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = QThreadPool.globalInstance()
        _thread_pool.setMaxThreadCount(4)
    return _thread_pool
