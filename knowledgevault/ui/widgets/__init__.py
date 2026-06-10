"""UI widgets."""

from knowledgevault.ui.widgets.dashboard import DashboardWidget
from knowledgevault.ui.widgets.graph_view import GraphCanvas, GraphViewWidget
from knowledgevault.ui.widgets.heatmap import ActivityHeatmap
from knowledgevault.ui.widgets.nav_panel import NavPanel
from knowledgevault.ui.widgets.top_bar import TopBar
from knowledgevault.ui.widgets.note_editor import NoteEditorPanel
from knowledgevault.ui.widgets.note_list import NoteListPanel

__all__ = [
    "ActivityHeatmap",
    "DashboardWidget",
    "GraphCanvas",
    "GraphViewWidget",
    "NavPanel",
    "NoteEditorPanel",
    "NoteListPanel",
    "TopBar",
]
