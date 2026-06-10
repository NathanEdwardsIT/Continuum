"""Professional knowledge graph visualization."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from continuum.models.entities import GraphEdge, GraphNode, NodeType
from continuum.ui.components.buttons import GhostButton, PrimaryButton
from continuum.ui.components.typography import Body, Caption, H1, H2
from continuum.ui.theme_palette import ThemePalette, ThemeId, get_palette


class GraphCanvas(QWidget):
    """Custom-painted graph with pan, zoom, hover, and edge-type styling."""

    node_clicked = Signal(str)
    node_hovered = Signal(str)
    node_double_clicked = Signal(str)

    _EDGE_COLORS = {
        "backlink": "graph_edge",
        "wiki": "accent",
        "category": "graph_category",
        "tag": "warning",
        "shared_tag": "accent",
        "tag_link": "warning",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("graphCanvas")
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

        self._palette = get_palette(ThemeId.STUDIO)
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []
        self._positions: dict[str, tuple[float, float]] = {}
        self._node_map: dict[str, GraphNode] = {}
        self._degrees: dict[str, int] = {}

        self._offset = QPointF(0, 0)
        self._scale = 1.0
        self._dragging = False
        self._drag_start = QPointF()
        self._hovered_id: str | None = None
        self._selected_id: str | None = None
        self._filter_text = ""

    def set_palette(self, palette: ThemePalette) -> None:
        self._palette = palette
        self.update()

    def render_graph(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        positions: dict[str, tuple[float, float]],
        degrees: dict[str, int] | None = None,
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._positions = positions
        self._node_map = {n.id: n for n in nodes}
        self._degrees = degrees or {}
        self._hovered_id = None
        self._selected_id = None
        self._offset = QPointF(0, 0)
        self._scale = 1.0
        self.update()

    def set_filter(self, text: str) -> None:
        self._filter_text = text.lower()
        self.update()

    def focus_node(self, node_id: str) -> None:
        if node_id not in self._positions:
            return
        self._selected_id = node_id
        x, y = self._positions[node_id]
        self._offset = QPointF(
            self.width() / 2 - x * 200 * self._scale,
            self.height() / 2 - y * 200 * self._scale,
        )
        self.update()

    def fit_view(self) -> None:
        if not self._positions:
            return
        xs = [p[0] for p in self._positions.values()]
        ys = [p[1] for p in self._positions.values()]
        if not xs:
            return
        pw = self.width() - 40
        ph = self.height() - 40
        dx = max(xs) - min(xs) or 1
        dy = max(ys) - min(ys) or 1
        self._scale = min(pw / dx, ph / dy) * 0.85
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        self._offset = QPointF(
            self.width() / 2 - cx * self._scale * 200,
            self.height() / 2 - cy * self._scale * 200,
        )
        self.update()

    def zoom_in(self) -> None:
        self._scale = min(8.0, self._scale * 1.25)
        self.update()

    def zoom_out(self) -> None:
        self._scale = max(0.15, self._scale / 1.25)
        self.update()

    def reset_view(self) -> None:
        self._offset = QPointF(0, 0)
        self._scale = 1.0
        self.fit_view()

    def _to_screen(self, x: float, y: float) -> QPointF:
        s = 200 * self._scale
        return QPointF(x * s + self._offset.x(), y * s + self._offset.y())

    def _node_radius(self, node: GraphNode) -> float:
        if node.node_type == NodeType.CATEGORY:
            return 14 * min(node.size, 1.5)
        if node.node_type == NodeType.TAG:
            return 8 * min(node.size, 1.2)
        return 10 * min(node.size, 1.4)

    def _edge_color(self, edge_type: str, alpha: float) -> QColor:
        attr = self._EDGE_COLORS.get(edge_type, "graph_edge")
        c = QColor(getattr(self._palette, attr))
        c.setAlphaF(alpha)
        return c

    def _node_color(self, node: GraphNode, alpha: float = 1.0) -> QColor:
        if node.node_type == NodeType.CATEGORY:
            c = QColor(self._palette.graph_category)
        elif node.node_type == NodeType.TAG:
            c = QColor(self._palette.warning)
        else:
            c = QColor(self._palette.graph_note)
        c.setAlphaF(alpha)
        return c

    def _find_node_at(self, pos: QPointF) -> str | None:
        best_id = None
        best_dist = float("inf")
        for node in self._nodes:
            if node.id not in self._positions:
                continue
            x, y = self._positions[node.id]
            sp = self._to_screen(x, y)
            r = self._node_radius(node) + 4
            dist = math.hypot(pos.x() - sp.x(), pos.y() - sp.y())
            if dist < r and dist < best_dist:
                best_dist = dist
                best_id = node.id
        return best_id

    def _is_dimmed(self, node_id: str) -> bool:
        if not self._filter_text:
            return False
        node = self._node_map.get(node_id)
        return node is not None and self._filter_text not in node.label.lower()

    def _draw_edge(self, painter: QPainter, p1: QPointF, p2: QPointF, edge: GraphEdge, highlighted: bool) -> None:
        alpha = 0.75 if highlighted else 0.2
        color = self._edge_color(edge.edge_type, alpha)
        pen = QPen(color)
        pen.setWidthF(2.2 if highlighted and edge.edge_type == "backlink" else 1.4 if highlighted else 0.7)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if edge.edge_type in ("backlink", "shared_tag", "wiki") and highlighted:
            path = QPainterPath(p1)
            mid = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
            dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
            length = math.hypot(dx, dy) or 1
            offset = min(30, length * 0.15)
            ctrl = QPointF(mid.x() - dy / length * offset, mid.y() + dx / length * offset)
            path.quadTo(ctrl, p2)
            painter.drawPath(path)
        else:
            painter.drawLine(p1, p2)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(self._palette.bg_card))

        if not self._nodes:
            painter.setPen(QColor(self._palette.text_muted))
            font = QFont("Segoe UI", 13)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No connections yet.\nCreate notes and they'll link automatically.",
            )
            painter.end()
            return

        highlight_set: set[str] = set()
        if self._hovered_id or self._selected_id:
            focus = self._hovered_id or self._selected_id
            if focus:
                highlight_set.add(focus)
            for edge in self._edges:
                if edge.source == focus:
                    highlight_set.add(edge.target)
                if edge.target == focus:
                    highlight_set.add(edge.source)

        for edge in self._edges:
            if edge.source not in self._positions or edge.target not in self._positions:
                continue
            if self._is_dimmed(edge.source) and self._is_dimmed(edge.target):
                continue

            p1 = self._to_screen(*self._positions[edge.source])
            p2 = self._to_screen(*self._positions[edge.target])
            is_highlighted = edge.source in highlight_set and edge.target in highlight_set
            self._draw_edge(painter, p1, p2, edge, is_highlighted)

        for node in self._nodes:
            if node.id not in self._positions:
                continue
            dimmed = self._is_dimmed(node.id)
            is_focus = node.id in highlight_set
            is_selected = node.id == self._selected_id

            sp = self._to_screen(*self._positions[node.id])
            r = self._node_radius(node)
            alpha = 0.2 if dimmed else (1.0 if is_focus or is_selected else 0.85)
            color = self._node_color(node, alpha)

            if node.node_type == NodeType.NOTE and (is_focus or is_selected):
                glow = QRadialGradient(sp, r * 2.5)
                glow_color = QColor(self._palette.graph_note)
                glow_color.setAlphaF(0.25)
                glow.setColorAt(0, glow_color)
                glow.setColorAt(1, QColor(0, 0, 0, 0))
                painter.setBrush(QBrush(glow))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(sp, r * 2.5, r * 2.5)

            painter.setBrush(QBrush(color))
            border_color = QColor(self._palette.accent if is_selected else self._palette.border)
            painter.setPen(QPen(border_color, 2 if is_selected else 1))
            if node.node_type == NodeType.CATEGORY:
                rect = QRectF(sp.x() - r, sp.y() - r, r * 2, r * 2)
                painter.drawRoundedRect(rect, 4, 4)
            else:
                painter.drawEllipse(sp, r, r)

        label_positions: list[tuple[float, float, str]] = []
        for node in self._nodes:
            if node.id not in self._positions or self._is_dimmed(node.id):
                continue
            is_hovered = node.id == self._hovered_id
            is_selected = node.id == self._selected_id
            is_category = node.node_type == NodeType.CATEGORY
            if not (is_hovered or is_selected or is_category):
                continue
            sp = self._to_screen(*self._positions[node.id])
            r = self._node_radius(node)
            label = node.label[:24] + ("…" if len(node.label) > 24 else "")
            label_positions.append((sp.x(), sp.y() + r + 14, label))

        for lx, ly, label in label_positions:
            font = QFont("Segoe UI", 9)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            fm = QFontMetrics(font)
            tw = fm.horizontalAdvance(label)
            pill_rect = QRectF(lx - tw / 2 - 6, ly - 12, tw + 12, 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self._palette.bg_elevated))
            painter.drawRoundedRect(pill_rect, 4, 4)
            painter.setPen(QColor(self._palette.text_primary))
            painter.drawText(QPointF(lx - tw / 2, ly), label)

        painter.end()

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
        old_scale = self._scale
        self._scale = max(0.15, min(8.0, self._scale * factor))
        mouse = event.position()
        ratio = self._scale / old_scale
        self._offset = QPointF(
            mouse.x() - ratio * (mouse.x() - self._offset.x()),
            mouse.y() - ratio * (mouse.y() - self._offset.y()),
        )
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            node_id = self._find_node_at(event.position())
            if node_id:
                self._selected_id = node_id
                self.node_clicked.emit(node_id)
                self.update()
            else:
                self._dragging = True
                self._drag_start = event.position() - self._offset
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            node_id = self._find_node_at(event.position())
            if node_id:
                self.node_double_clicked.emit(node_id)
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self._offset = event.position() - self._drag_start
            self.update()
        else:
            node_id = self._find_node_at(event.position())
            if node_id != self._hovered_id:
                self._hovered_id = node_id
                if node_id:
                    self.node_hovered.emit(node_id)
                self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        super().mouseReleaseEvent(event)


class GraphViewWidget(QWidget):
    """Full graph page with toolbar, canvas, and detail panel."""

    note_selected = Signal(int)
    tag_selected = Signal(str)
    category_selected = Signal(str)
    filter_changed = Signal(str, bool, bool)
    layout_changed = Signal(str)

    MODES = {
        "Notes Only": (True, False, False),
        "Notes + Tags": (True, False, True),
        "Notes + Categories": (True, True, False),
        "Full Graph": (True, True, True),
    }

    LAYOUTS = {
        "Spring": "spring",
        "Organic (Kamada-Kawai)": "kamada_kawai",
        "Circular": "circular",
        "Shell": "shell",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace")
        self._palette = get_palette(ThemeId.STUDIO)
        self._current_nodes: list[GraphNode] = []
        self._current_edges: list[GraphEdge] = []
        self._degrees: dict[str, int] = {}
        self._tool_btns: list[GhostButton] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        self._title = H1("Knowledge Graph")
        title_col.addWidget(self._title)
        self._subtitle = Body("Explore how your notes connect")
        title_col.addWidget(self._subtitle)
        header.addLayout(title_col)
        header.addStretch()
        self._stats = Caption("")
        header.addWidget(self._stats)
        layout.addLayout(header)

        toolbar = QWidget()
        toolbar.setObjectName("glassPanel")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(10, 8, 10, 8)
        tb_layout.setSpacing(8)

        from continuum.ui.components.inputs import SearchField
        self._search = SearchField("Filter nodes…")
        self._search.setFixedWidth(200)
        self._search.textChanged.connect(self._on_filter_text)
        tb_layout.addWidget(self._search)

        view_lbl = Caption("View")
        tb_layout.addWidget(view_lbl)
        self._view_lbl = view_lbl
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(list(self.MODES.keys()))
        self._mode_combo.setCurrentIndex(1)  # Notes + Tags
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        tb_layout.addWidget(self._mode_combo)

        layout_lbl = Caption("Layout")
        tb_layout.addWidget(layout_lbl)
        self._layout_lbl = layout_lbl
        self._layout_combo = QComboBox()
        self._layout_combo.addItems(list(self.LAYOUTS.keys()))
        self._layout_combo.currentTextChanged.connect(self._on_layout_changed)
        tb_layout.addWidget(self._layout_combo)

        tb_layout.addStretch()

        for label, slot in [
            ("−", self._canvas_zoom_out),
            ("+", self._canvas_zoom_in),
            ("Fit", self._canvas_fit),
            ("Reset", self._canvas_reset),
        ]:
            btn = GhostButton(label)
            btn.setFixedWidth(44 if label in ("−", "+") else 52)
            btn.clicked.connect(lambda checked=False, fn=slot: fn())
            self._tool_btns.append(btn)
            tb_layout.addWidget(btn)

        self._toolbar = toolbar
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._canvas = GraphCanvas()
        self._canvas.node_clicked.connect(self._on_node_click)
        self._canvas.node_hovered.connect(self._on_node_hover)
        self._canvas.node_double_clicked.connect(self._on_node_double_click)
        splitter.addWidget(self._canvas)

        self._side_panel = QWidget()
        self._side_panel.setObjectName("glassPanel")
        self._side_panel.setFixedWidth(240)
        side_layout = QVBoxLayout(self._side_panel)
        side_layout.setContentsMargins(16, 16, 16, 16)
        side_layout.setSpacing(10)

        self._detail_title = H2("Select a node")
        self._detail_title.setWordWrap(True)
        side_layout.addWidget(self._detail_title)
        self._detail_type = Caption("")
        side_layout.addWidget(self._detail_type)
        self._detail_info = Body("Click a node · double-click to open · drag to pan")
        side_layout.addWidget(self._detail_info)

        self._open_btn = PrimaryButton("Open Note")
        self._open_btn.hide()
        self._open_btn.clicked.connect(lambda checked=False: self._open_selected_note())
        side_layout.addWidget(self._open_btn)

        self._filter_btn = PrimaryButton("View Tagged Notes")
        self._filter_btn.hide()
        self._filter_btn.clicked.connect(lambda checked=False: self._filter_selected_tag())
        side_layout.addWidget(self._filter_btn)

        self._filter_cat_btn = PrimaryButton("View Category Notes")
        self._filter_cat_btn.hide()
        self._filter_cat_btn.clicked.connect(lambda checked=False: self._filter_selected_category())
        side_layout.addWidget(self._filter_cat_btn)

        conn_lbl = Caption("Connections")
        side_layout.addWidget(conn_lbl)
        self._conn_lbl = conn_lbl
        self._connections = QListWidget()
        self._connections.setMaximumHeight(160)
        self._connections.itemDoubleClicked.connect(self._on_connection_clicked)
        side_layout.addWidget(self._connections)

        side_layout.addStretch()
        self._legend = Caption(
            "● Notes  ■ Categories  ● Tags  — shared-tag links connect notes with common tags"
        )
        side_layout.addWidget(self._legend)

        splitter.addWidget(self._side_panel)
        splitter.setSizes([700, 240])
        layout.addWidget(splitter, stretch=1)

        self._selected_note_id: int | None = None
        self._selected_tag: str | None = None
        self._selected_category: str | None = None

    def apply_palette(self, p: ThemePalette) -> None:
        self._palette = p
        self._canvas.set_palette(p)
        self._title.apply_palette(p)
        self._subtitle.apply_palette(p)
        self._detail_title.apply_palette(p)
        self._detail_type.apply_palette(p)
        self._detail_info.apply_palette(p)
        self._legend.apply_palette(p)
        self._conn_lbl.apply_palette(p)
        self._open_btn.apply_palette(p)
        self._filter_btn.apply_palette(p)
        self._filter_cat_btn.apply_palette(p)
        self._search.apply_palette(p)
        self._view_lbl.apply_palette(p)
        self._layout_lbl.apply_palette(p)
        for btn in self._tool_btns:
            btn.apply_palette(p)
        for w in (self._toolbar, self._side_panel):
            w.setStyleSheet(f"""
              QWidget#glassPanel {{
                background: {p.glass_bg};
                border: 1px solid {p.glass_border};
                border-radius: 14px;
              }}
            """)
        self._connections.setStyleSheet(f"""
            QListWidget {{
                background: {p.bg_tertiary};
                border: 1px solid {p.border_subtle};
                border-radius: 8px;
                color: {p.text_secondary};
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 4px 8px;
            }}
            QListWidget::item:selected {{
                background: {p.accent_subtle};
                color: {p.text_primary};
            }}
        """)

    set_palette = apply_palette

    def render_graph(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        positions: dict[str, tuple[float, float]],
        degrees: dict[str, int] | None = None,
    ) -> None:
        self._current_nodes = nodes
        self._current_edges = edges
        self._degrees = degrees or {}
        note_count = sum(1 for n in nodes if n.node_type == NodeType.NOTE)
        cat_count = sum(1 for n in nodes if n.node_type == NodeType.CATEGORY)
        tag_count = sum(1 for n in nodes if n.node_type == NodeType.TAG)
        self._stats.setText(
            f"{note_count} notes · {cat_count} categories · {tag_count} tags · {len(edges)} links"
        )
        self._canvas.render_graph(nodes, edges, positions, degrees)
        self._canvas.fit_view()

    def _on_filter_text(self, text: str) -> None:
        self._canvas.set_filter(text)

    def _on_mode_changed(self, mode: str) -> None:
        show_notes, show_cats, show_tags = self.MODES.get(mode, (True, True, False))
        self.filter_changed.emit(mode, show_cats, show_tags)

    def _on_layout_changed(self, label: str) -> None:
        layout = self.LAYOUTS.get(label, "spring")
        self.layout_changed.emit(layout)

    def _canvas_zoom_in(self) -> None:
        self._canvas.zoom_in()

    def _canvas_zoom_out(self) -> None:
        self._canvas.zoom_out()

    def _canvas_fit(self) -> None:
        self._canvas.fit_view()

    def _canvas_reset(self) -> None:
        self._canvas.reset_view()

    def _on_node_click(self, node_id: str) -> None:
        self._update_detail(node_id)
        self._selected_note_id = None
        self._selected_tag = None
        self._selected_category = None
        self._open_btn.hide()
        self._filter_btn.hide()
        self._filter_cat_btn.hide()

        if node_id.startswith("note_"):
            try:
                self._selected_note_id = int(node_id.split("_", 1)[1])
                self._open_btn.show()
            except ValueError:
                pass
        elif node_id.startswith("tag_"):
            self._selected_tag = node_id.split("_", 1)[1]
            self._filter_btn.show()
        elif node_id.startswith("cat_"):
            self._selected_category = node_id.split("_", 1)[1]
            self._filter_cat_btn.show()

    def _on_node_double_click(self, node_id: str) -> None:
        if node_id.startswith("note_"):
            try:
                self.note_selected.emit(int(node_id.split("_", 1)[1]))
            except ValueError:
                pass

    def _on_node_hover(self, node_id: str) -> None:
        self._update_detail(node_id)

    def _on_connection_clicked(self, item: QListWidgetItem) -> None:
        node_id = item.data(Qt.ItemDataRole.UserRole)
        if node_id:
            self._canvas.focus_node(node_id)
            self._on_node_click(node_id)

    def _update_detail(self, node_id: str) -> None:
        node = next((n for n in self._current_nodes if n.id == node_id), None)
        if not node:
            return
        self._detail_title.setText(node.label)
        names = {NodeType.NOTE: "Note", NodeType.CATEGORY: "Category", NodeType.TAG: "Tag"}
        degree = self._degrees.get(node_id, 0)
        self._detail_type.setText(f"{names.get(node.node_type, 'Node')} · {degree} connection{'s' if degree != 1 else ''}")
        if node.node_type == NodeType.NOTE:
            self._detail_info.setText("Double-click or use Open Note to view in editor.")
        elif node.node_type == NodeType.CATEGORY:
            self._detail_info.setText("Category grouping — use View Category Notes to browse.")
        else:
            note_links = sum(
                1 for edge in self._current_edges
                if edge.edge_type == "tag"
                and (edge.source == node_id or edge.target == node_id)
            )
            self._detail_info.setText(
                f"On {note_links} note{'s' if note_links != 1 else ''} · "
                "notes with this tag are linked in the graph"
            )

        self._connections.clear()
        neighbors: dict[str, tuple[str, float]] = {}
        for edge in self._current_edges:
            if edge.source == node_id:
                neighbors[edge.target] = (edge.edge_type, edge.weight)
            elif edge.target == node_id:
                neighbors[edge.source] = (edge.edge_type, edge.weight)

        for neighbor_id, (edge_type, weight) in sorted(
            neighbors.items(), key=lambda item: item[1][1], reverse=True
        )[:12]:
            neighbor = next((n for n in self._current_nodes if n.id == neighbor_id), None)
            if not neighbor:
                continue
            prefix = {
                "backlink": "↔", "wiki": "⇒", "category": "▣",
                "tag": "#", "shared_tag": "⊕", "tag_link": "≈",
            }.get(edge_type, "·")
            item = QListWidgetItem(f"{prefix} {neighbor.label[:28]}")
            item.setData(Qt.ItemDataRole.UserRole, neighbor_id)
            item.setToolTip(f"{edge_type} · strength {weight:.2f}")
            self._connections.addItem(item)

    def _open_selected_note(self) -> None:
        if self._selected_note_id is not None:
            self.note_selected.emit(self._selected_note_id)

    def _filter_selected_tag(self) -> None:
        if self._selected_tag:
            self.tag_selected.emit(self._selected_tag)

    def _filter_selected_category(self) -> None:
        if self._selected_category:
            self.category_selected.emit(self._selected_category)
