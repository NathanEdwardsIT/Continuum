"""Knowledge graph engine using NetworkX."""

from __future__ import annotations

import math
from enum import Enum

import networkx as nx

from continuum.database.repository import NoteRepository
from continuum.models.entities import GraphEdge, GraphNode, NodeType


class LayoutAlgorithm(str, Enum):
    SPRING = "spring"
    KAMADA_KAWAI = "kamada_kawai"
    CIRCULAR = "circular"
    SHELL = "shell"


class GraphEngine:
    """Builds and manages the knowledge graph from notes, tags, and categories."""

    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository
        self._graph: nx.Graph | None = None
        self._layout: LayoutAlgorithm = LayoutAlgorithm.SPRING

    def set_layout(self, layout: LayoutAlgorithm | str) -> None:
        if isinstance(layout, str):
            layout = LayoutAlgorithm(layout)
        self._layout = layout

    def build_graph(
        self,
        show_notes: bool = True,
        show_categories: bool = True,
        show_tags: bool = False,
    ) -> nx.Graph:
        """Construct the knowledge graph with optional node-type filters."""
        g = nx.Graph()

        notes = self._repo.get_all_notes()
        categories = self._repo.get_all_categories() if show_categories else []
        tags = self._repo.get_all_tags() if show_tags else []
        backlinks = self._repo.get_all_backlinks()

        if not show_notes:
            self._graph = g
            return g

        for note in notes:
            node_id = f"note_{note.id}"
            size = 1.0 + math.log1p(len(note.content) / 500)
            g.add_node(
                node_id,
                label=note.title or "Untitled",
                node_type=NodeType.NOTE.value,
                size=size,
                db_id=note.id,
            )

        for cat in categories:
            node_id = f"cat_{cat.name}"
            size = 1.0 + math.log1p(cat.note_count)
            g.add_node(
                node_id,
                label=cat.name,
                node_type=NodeType.CATEGORY.value,
                size=size,
            )

        for tag in tags:
            node_id = f"tag_{tag.name}"
            size = 0.8 + math.log1p(tag.note_count) * 0.5
            g.add_node(
                node_id,
                label=tag.name,
                node_type=NodeType.TAG.value,
                size=size,
            )

        if show_categories:
            for note in notes:
                note_node = f"note_{note.id}"
                for cat_name in note.categories:
                    cat_node = f"cat_{cat_name}"
                    if g.has_node(cat_node):
                        g.add_edge(note_node, cat_node, weight=0.5, edge_type="category")

        if show_tags:
            top_tags = {t.name for t in sorted(tags, key=lambda t: t.note_count, reverse=True)[:15]}
            for note in notes:
                note_node = f"note_{note.id}"
                for tag_name in note.tags:
                    if tag_name in top_tags:
                        tag_node = f"tag_{tag_name}"
                        if g.has_node(tag_node):
                            g.add_edge(note_node, tag_node, weight=0.3, edge_type="tag")

        seen_pairs: set[tuple[str, str]] = set()
        for bl in backlinks:
            src = f"note_{bl.source_note_id}"
            tgt = f"note_{bl.target_note_id}"
            pair = tuple(sorted([src, tgt]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if g.has_node(src) and g.has_node(tgt):
                g.add_edge(src, tgt, weight=bl.strength, edge_type="backlink")

        self._graph = g
        return g

    def get_layout_positions(
        self,
        g: nx.Graph | None = None,
        layout: LayoutAlgorithm | str | None = None,
    ) -> dict[str, tuple[float, float]]:
        """Compute node positions using the selected layout algorithm."""
        graph = g or self._graph
        if graph is None or graph.number_of_nodes() == 0:
            return {}

        algo = layout or self._layout
        if isinstance(algo, str):
            algo = LayoutAlgorithm(algo)

        n = graph.number_of_nodes()
        weight = "weight"

        if algo == LayoutAlgorithm.KAMADA_KAWAI and n <= 120 and graph.number_of_edges() > 0:
            try:
                return nx.kamada_kawai_layout(graph, weight=weight)
            except nx.NetworkXError:
                pass

        if algo == LayoutAlgorithm.CIRCULAR:
            return nx.circular_layout(graph)

        if algo == LayoutAlgorithm.SHELL:
            note_nodes = [nid for nid, data in graph.nodes(data=True) if data.get("node_type") == "note"]
            other_nodes = [nid for nid in graph.nodes if nid not in note_nodes]
            if note_nodes and other_nodes:
                return nx.shell_layout(graph, nlist=[note_nodes, other_nodes])
            return nx.shell_layout(graph)

        k = max(1.2, 2.8 / math.sqrt(n))
        return nx.spring_layout(graph, k=k, iterations=100, seed=42, weight=weight)

    def get_nodes(self, g: nx.Graph | None = None) -> list[GraphNode]:
        graph = g or self._graph
        if graph is None:
            return []
        nodes = []
        for node_id, data in graph.nodes(data=True):
            nodes.append(
                GraphNode(
                    id=node_id,
                    label=data.get("label", node_id),
                    node_type=NodeType(data.get("node_type", "note")),
                    size=data.get("size", 1.0),
                )
            )
        return nodes

    def get_edges(self, g: nx.Graph | None = None) -> list[GraphEdge]:
        graph = g or self._graph
        if graph is None:
            return []
        return [
            GraphEdge(
                source=u,
                target=v,
                weight=data.get("weight", 1.0),
                edge_type=data.get("edge_type", "backlink"),
            )
            for u, v, data in graph.edges(data=True)
        ]

    def get_node_degree(self, g: nx.Graph | None = None) -> dict[str, int]:
        graph = g or self._graph
        if graph is None:
            return {}
        return dict(graph.degree())

    def get_neighbors(self, node_id: str, g: nx.Graph | None = None) -> list[tuple[str, str, float]]:
        """Return (neighbor_id, edge_type, weight) for a node."""
        graph = g or self._graph
        if graph is None or node_id not in graph:
            return []
        results = []
        for neighbor in graph.neighbors(node_id):
            data = graph.get_edge_data(node_id, neighbor, default={})
            results.append((
                neighbor,
                data.get("edge_type", "backlink"),
                data.get("weight", 1.0),
            ))
        return sorted(results, key=lambda item: item[2], reverse=True)

    def get_subgraph_for_note(self, note_id: int, depth: int = 2) -> nx.Graph:
        """Get neighborhood subgraph around a specific note."""
        full = self.build_graph()
        center = f"note_{note_id}"
        if center not in full:
            return nx.Graph()

        nodes = {center}
        frontier = {center}
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                next_frontier.update(full.neighbors(node))
            nodes.update(next_frontier)
            frontier = next_frontier

        return full.subgraph(nodes).copy()

    @property
    def graph(self) -> nx.Graph | None:
        return self._graph
