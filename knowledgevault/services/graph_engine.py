"""Knowledge graph engine using NetworkX."""

from __future__ import annotations

import math
from enum import Enum
from itertools import combinations

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

        if show_tags:
            for tag in tags:
                node_id = f"tag_{tag.name}"
                size = 0.8 + math.log1p(tag.note_count) * 0.5
                g.add_node(
                    node_id,
                    label=tag.name,
                    node_type=NodeType.TAG.value,
                    size=size,
                )

            note_tag_sets: dict[int, set[str]] = {}
            tag_pair_counts: dict[tuple[str, str], int] = {}

            for note in notes:
                note_node = f"note_{note.id}"
                tag_set = set(note.tags)
                note_tag_sets[note.id or 0] = tag_set
                for tag_name in tag_set:
                    tag_node = f"tag_{tag_name}"
                    if g.has_node(tag_node):
                        g.add_edge(note_node, tag_node, weight=0.35, edge_type="tag")
                sorted_tags = sorted(tag_set)
                for a, b in combinations(sorted_tags, 2):
                    pair = (a, b)
                    tag_pair_counts[pair] = tag_pair_counts.get(pair, 0) + 1

            # Note↔note edges for notes sharing tags
            note_ids = [note.id for note in notes if note.id is not None]
            for i, note_a_id in enumerate(note_ids):
                tags_a = note_tag_sets.get(note_a_id, set())
                if not tags_a:
                    continue
                for note_b_id in note_ids[i + 1:]:
                    shared = tags_a & note_tag_sets.get(note_b_id, set())
                    if not shared:
                        continue
                    src = f"note_{note_a_id}"
                    tgt = f"note_{note_b_id}"
                    if not (g.has_node(src) and g.has_node(tgt)):
                        continue
                    weight = min(0.2 + 0.15 * len(shared), 0.85)
                    existing = g.get_edge_data(src, tgt)
                    if existing and existing.get("edge_type") == "backlink":
                        existing["weight"] = max(existing["weight"], weight)
                        existing["shared_tags"] = len(shared)
                    else:
                        g.add_edge(
                            src, tgt,
                            weight=weight,
                            edge_type="shared_tag",
                            shared_tags=len(shared),
                        )

            # Tag↔tag co-occurrence edges (tags appearing together on 2+ notes)
            for (tag_a, tag_b), count in tag_pair_counts.items():
                if count < 2:
                    continue
                node_a = f"tag_{tag_a}"
                node_b = f"tag_{tag_b}"
                if g.has_node(node_a) and g.has_node(node_b):
                    g.add_edge(
                        node_a, node_b,
                        weight=min(0.15 + 0.1 * count, 0.7),
                        edge_type="tag_link",
                        cooccurrence=count,
                    )

        if show_categories:
            for note in notes:
                note_node = f"note_{note.id}"
                for cat_name in note.categories:
                    cat_node = f"cat_{cat_name}"
                    if g.has_node(cat_node):
                        g.add_edge(note_node, cat_node, weight=0.5, edge_type="category")

        seen_pairs: set[tuple[str, str]] = set()
        for bl in backlinks:
            src = f"note_{bl.source_note_id}"
            tgt = f"note_{bl.target_note_id}"
            pair = tuple(sorted([src, tgt]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if g.has_node(src) and g.has_node(tgt):
                edge_type = "wiki" if "wiki" in (bl.reason or "").lower() else "backlink"
                existing = g.get_edge_data(src, tgt)
                if existing:
                    existing["weight"] = max(existing.get("weight", 0), bl.strength)
                    if edge_type == "wiki":
                        existing["edge_type"] = "wiki"
                else:
                    g.add_edge(src, tgt, weight=bl.strength, edge_type=edge_type)

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
