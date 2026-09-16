"""
Forensic Graph Analytics Engine for Case-Scoped Knowledge Networks (Slice 8D).

Graph Projection Semantics:
- degree: unique communicating neighbors (in-degree, out-degree, and total unique neighbors)
- frequency: observed communication message count between directed pair (u, v)
- betweenness / path distance: inverse frequency (1.0 / weight), reflecting that
  high-frequency communication indicates shorter investigative distance
- PageRank: weighted communication flow volume across directed edges
- community detection: Louvain modularity on undirected weighted projection,
  where bidirectional communication frequencies are summed

Strict Behavioral Boundaries:
- Zero Graph Neural Networks (GNN).
- Zero link prediction or edge speculation.
- Zero anomaly detection or statistical profiling.
- Zero kingpin, ringleader, or criminal labeling (neutral mathematical descriptions only).
- Zero CCC scoring modifications.
- Zero synthetic or demonstration data.
"""

import time
from datetime import datetime, timezone
from collections import Counter
from typing import Dict, List, Any, Optional, Set, Tuple
import networkx as nx


class NetworkGraphAnalytics:
    """
    Stateless, deterministic graph analytics calculator operating on case-isolated subgraphs.
    """

    @staticmethod
    def project_graph(case_graph: Dict[str, Any]) -> Tuple[nx.DiGraph, nx.Graph]:
        """
        Projects case-scoped nodes and edges into:
        1. Directed weighted graph (nx.DiGraph) where weight = observed communication count
           and dist = 1.0 / weight.
        2. Undirected weighted graph (nx.Graph) where bidirectional weights are summed.
        """
        G = nx.DiGraph()
        nodes = case_graph.get("nodes", [])
        edges = case_graph.get("edges", [])

        # Add all case-isolated nodes
        for node in nodes:
            nid = node.get("id")
            if not nid:
                continue
            G.add_node(
                nid,
                label=node.get("label", nid),
                canonical_name=node.get("canonical_name", nid),
                entity_type=node.get("entity_type", "Unknown"),
                observed_count=node.get("observed_count", 0),
                is_anchor=node.get("is_anchor", False),
            )

        # Aggregate edges into weighted directed multigraph projection
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if not src or not tgt:
                continue
            if src not in G:
                G.add_node(src, label=src, entity_type="Unknown", is_anchor=False)
            if tgt not in G:
                G.add_node(tgt, label=tgt, entity_type="Unknown", is_anchor=False)

            ev_id = edge.get("evidence_id")
            edge_id = edge.get("id")
            rel_type = edge.get("relationship", edge.get("relationship_type", "COMMUNICATED_WITH"))

            if G.has_edge(src, tgt):
                G[src][tgt]["weight"] += 1
                if ev_id:
                    G[src][tgt]["evidence_ids"].add(ev_id)
                if edge_id:
                    G[src][tgt]["edge_ids"].append(edge_id)
            else:
                G.add_edge(
                    src,
                    tgt,
                    weight=1,
                    relationship_type=rel_type,
                    evidence_ids={ev_id} if ev_id else set(),
                    edge_ids=[edge_id] if edge_id else [],
                )

        # Invert weight for distance-based algorithms (betweenness & shortest path)
        for u, v, d in G.edges(data=True):
            d["dist"] = 1.0 / max(d["weight"], 1)

        # Undirected weighted projection for Louvain community detection
        undirected_G = nx.Graph()
        for n, attrs in G.nodes(data=True):
            undirected_G.add_node(n, **attrs)

        for u, v, d in G.edges(data=True):
            w = d["weight"]
            if undirected_G.has_edge(u, v):
                undirected_G[u][v]["weight"] += w
            else:
                undirected_G.add_edge(u, v, weight=w)

        return G, undirected_G

    def compute_analytics(
        self,
        case_graph: Dict[str, Any],
        temporal_timestamps: Optional[List[int]] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes all 9 forensic graph analytics algorithms on the provided case graph.
        Measures and returns benchmark execution timings for each algorithm.
        """
        case_id = case_graph.get("case_id", "UNKNOWN_CASE")
        nodes = case_graph.get("nodes", [])
        edges = case_graph.get("edges", [])

        benchmarks: Dict[str, float] = {}
        total_start = time.perf_counter()

        # Handle empty case graph
        if not nodes or not edges:
            total_duration_ms = (time.perf_counter() - total_start) * 1000
            return {
                "case_id": case_id,
                "is_empty": True,
                "summary": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "unique_directed_pairs": 0,
                },
                "semantics": {
                    "degree": "unique communicating neighbors",
                    "frequency": "observed communication count",
                    "betweenness_distance": "inverse frequency (1.0 / weight)",
                    "pagerank": "weighted communication graph",
                    "community_detection": "undirected weighted projection",
                },
                "degree_metrics": {},
                "weighted_frequency": {"unique_pairs": 0, "max_frequency": 0, "pairs": []},
                "betweenness_centrality": {},
                "pagerank": {},
                "connected_components": {
                    "weakly_connected_count": 0,
                    "strongly_connected_count": 0,
                    "components": [],
                },
                "community_detection": {"total_communities": 0, "communities": []},
                "shortest_path": {"path_exists": False, "path": [], "hop_count": 0, "total_cost": None},
                "neighbor_metrics": {"entity_id": None, "one_hop": [], "two_hop": []},
                "timestamp_patterns": {
                    "total_events": 0,
                    "earliest_timestamp": None,
                    "latest_timestamp": None,
                    "earliest_iso": None,
                    "latest_iso": None,
                    "monthly_distribution": [],
                    "hourly_distribution_utc": [],
                },
                "benchmark_timing_ms": {
                    "total_analytics_ms": round(total_duration_ms, 3)
                },
            }

        # Build in-memory graph projection
        t0 = time.perf_counter()
        G, undirected_G = self.project_graph(case_graph)
        benchmarks["projection_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 1. Degree (Unique Communicating Neighbors)
        t0 = time.perf_counter()
        in_deg = dict(G.in_degree())
        out_deg = dict(G.out_degree())
        undir_deg = dict(undirected_G.degree())
        degree_metrics = {}
        for n in G.nodes():
            degree_metrics[n] = {
                "in_degree": in_deg.get(n, 0),
                "out_degree": out_deg.get(n, 0),
                "unique_neighbors": undir_deg.get(n, 0),
                "total_degree": undir_deg.get(n, 0),
            }
        benchmarks["degree_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 2. Weighted Communication Frequency
        t0 = time.perf_counter()
        edge_data = []
        for u, v, d in G.edges(data=True):
            edge_data.append({
                "source": u,
                "target": v,
                "weight": d["weight"],
                "evidence_count": len(d.get("evidence_ids", set())),
                "sample_edge_id": d.get("edge_ids", [None])[0],
            })
        edge_data.sort(key=lambda x: x["weight"], reverse=True)
        max_freq = edge_data[0]["weight"] if edge_data else 0
        weighted_frequency = {
            "unique_pairs": len(edge_data),
            "max_frequency": max_freq,
            "pairs": edge_data,
        }
        benchmarks["weighted_frequency_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 3. Betweenness Centrality (Inverse frequency distance)
        t0 = time.perf_counter()
        try:
            betweenness_dict = nx.betweenness_centrality(G, weight="dist", normalized=True)
            betweenness_centrality = {k: round(v, 6) for k, v in betweenness_dict.items()}
        except Exception:
            betweenness_centrality = {k: 0.0 for k in G.nodes()}
        benchmarks["betweenness_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 4. PageRank (Weighted Communication Flow)
        t0 = time.perf_counter()
        try:
            pr_dict = nx.pagerank(G, weight="weight", alpha=0.85)
            pagerank = {k: round(v, 6) for k, v in pr_dict.items()}
        except Exception:
            num_nodes = max(G.number_of_nodes(), 1)
            pagerank = {k: round(1.0 / num_nodes, 6) for k in G.nodes()}
        benchmarks["pagerank_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 5. Connected Components (Weak & Strong)
        t0 = time.perf_counter()
        wcc_raw = list(nx.weakly_connected_components(G))
        scc_raw = list(nx.strongly_connected_components(G))

        components_list = []
        for idx, comp in enumerate(sorted(wcc_raw, key=len, reverse=True), start=1):
            components_list.append({
                "component_id": f"WCC-{idx:02d}",
                "type": "WEAKLY_CONNECTED",
                "size": len(comp),
                "member_node_ids": sorted(list(comp)),
            })
        connected_components = {
            "weakly_connected_count": len(wcc_raw),
            "strongly_connected_count": len(scc_raw),
            "largest_component_size": len(wcc_raw[0]) if wcc_raw else 0,
            "components": components_list,
        }
        benchmarks["connected_components_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 6. Community Detection (Louvain modularity on undirected weighted projection)
        t0 = time.perf_counter()
        communities_list = []
        if undirected_G.number_of_edges() > 0:
            try:
                louvain_comms = nx.community.louvain_communities(undirected_G, weight="weight", seed=42)
                for idx, comm in enumerate(sorted(louvain_comms, key=len, reverse=True), start=1):
                    communities_list.append({
                        "community_id": f"COMM-{idx:02d}",
                        "size": len(comm),
                        "member_node_ids": sorted(list(comm)),
                    })
            except Exception:
                communities_list = [{
                    "community_id": "COMM-01",
                    "size": len(undirected_G.nodes()),
                    "member_node_ids": sorted(list(undirected_G.nodes())),
                }]
        else:
            for idx, n in enumerate(sorted(list(undirected_G.nodes())), start=1):
                communities_list.append({
                    "community_id": f"COMM-{idx:02d}",
                    "size": 1,
                    "member_node_ids": [n],
                })
        community_detection = {
            "algorithm": "LOUVAIN_MODULARITY",
            "projection": "UNDIRECTED_WEIGHTED",
            "total_communities": len(communities_list),
            "communities": communities_list,
        }
        benchmarks["community_detection_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 7. Weighted Shortest Path (Inverse frequency distance)
        t0 = time.perf_counter()
        query_src = source_id
        query_tgt = target_id
        if not query_src or not query_tgt:
            sorted_pr = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_pr) >= 2:
                query_src = sorted_pr[0][0]
                query_tgt = sorted_pr[1][0]

        shortest_path_result = self.calculate_shortest_path(G, query_src, query_tgt)
        benchmarks["shortest_path_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 8. 1-Hop / 2-Hop Neighbors
        t0 = time.perf_counter()
        target_ego_id = entity_id or query_src or (list(G.nodes())[0] if G.nodes() else None)
        neighbor_metrics = self.calculate_k_hop_neighbors(G, target_ego_id, max_hops=2)
        benchmarks["neighbor_metrics_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        # 9. Descriptive Timestamp Patterns
        t0 = time.perf_counter()
        timestamp_patterns = self.calculate_timestamp_patterns(temporal_timestamps or [])
        benchmarks["temporal_patterns_ms"] = round((time.perf_counter() - t0) * 1000, 3)

        total_duration_ms = (time.perf_counter() - total_start) * 1000
        benchmarks["total_analytics_ms"] = round(total_duration_ms, 3)

        return {
            "case_id": case_id,
            "is_empty": False,
            "summary": {
                "total_nodes": G.number_of_nodes(),
                "total_raw_edges": len(edges),
                "unique_directed_pairs": G.number_of_edges(),
            },
            "semantics": {
                "degree": "unique communicating neighbors",
                "frequency": "observed communication count",
                "betweenness_distance": "inverse frequency (1.0 / weight)",
                "pagerank": "weighted communication graph",
                "community_detection": "undirected weighted projection",
            },
            "degree_metrics": degree_metrics,
            "weighted_frequency": weighted_frequency,
            "betweenness_centrality": betweenness_centrality,
            "pagerank": pagerank,
            "connected_components": connected_components,
            "community_detection": community_detection,
            "shortest_path": shortest_path_result,
            "neighbor_metrics": neighbor_metrics,
            "timestamp_patterns": timestamp_patterns,
            "benchmark_timing_ms": benchmarks,
        }

    @staticmethod
    def calculate_shortest_path(
        G: nx.DiGraph,
        source_id: Optional[str],
        target_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Calculates Dijkstra shortest path on inverted frequency distances (dist = 1.0 / weight).
        """
        if not source_id or not target_id or source_id not in G or target_id not in G:
            return {
                "source_id": source_id,
                "target_id": target_id,
                "path_exists": False,
                "path": [],
                "hop_count": 0,
                "total_cost": None,
            }

        try:
            path = nx.shortest_path(G, source_id, target_id, weight="dist")
            total_cost = nx.shortest_path_length(G, source_id, target_id, weight="dist")
            return {
                "source_id": source_id,
                "target_id": target_id,
                "path_exists": True,
                "path": path,
                "hop_count": len(path) - 1,
                "total_cost": round(total_cost, 6),
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return {
                "source_id": source_id,
                "target_id": target_id,
                "path_exists": False,
                "path": [],
                "hop_count": 0,
                "total_cost": None,
            }

    @staticmethod
    def calculate_k_hop_neighbors(
        G: nx.DiGraph,
        entity_id: Optional[str],
        max_hops: int = 2
    ) -> Dict[str, Any]:
        """
        Computes 1-hop and 2-hop neighbor reachability for a target entity.
        """
        if not entity_id or entity_id not in G:
            return {
                "entity_id": entity_id,
                "one_hop": [],
                "two_hop": [],
                "one_hop_count": 0,
                "two_hop_count": 0,
            }

        lengths = nx.single_source_shortest_path_length(G, entity_id, cutoff=max_hops)
        one_hop = sorted([n for n, d in lengths.items() if d == 1])
        two_hop = sorted([n for n, d in lengths.items() if d == 2])

        return {
            "entity_id": entity_id,
            "one_hop": one_hop,
            "two_hop": two_hop,
            "one_hop_count": len(one_hop),
            "two_hop_count": len(two_hop),
        }

    @staticmethod
    def calculate_timestamp_patterns(timestamps: List[int]) -> Dict[str, Any]:
        """
        Computes pure descriptive chronological patterns (histograms and time windows)
        from verified integer Unix timestamps.
        Zero forecasting, zero anomaly scoring.
        """
        valid_ts = [ts for ts in timestamps if isinstance(ts, (int, float)) and ts > 0]
        if not valid_ts:
            return {
                "total_events": 0,
                "earliest_timestamp": None,
                "latest_timestamp": None,
                "earliest_iso": None,
                "latest_iso": None,
                "monthly_distribution": [],
                "hourly_distribution_utc": [],
            }

        min_ts = int(min(valid_ts))
        max_ts = int(max(valid_ts))

        earliest_iso = datetime.fromtimestamp(min_ts, tz=timezone.utc).isoformat()
        latest_iso = datetime.fromtimestamp(max_ts, tz=timezone.utc).isoformat()

        # Monthly aggregation
        months = [datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m") for ts in valid_ts]
        month_counts = Counter(months)
        monthly_dist = [
            {"period": period, "count": month_counts[period]}
            for period in sorted(month_counts.keys())
        ]

        # Hourly UTC distribution (24-bucket fixed histogram)
        hours = [datetime.fromtimestamp(ts, tz=timezone.utc).hour for ts in valid_ts]
        hour_counts = Counter(hours)
        hourly_dist = [
            {"hour": h, "count": hour_counts.get(h, 0)}
            for h in range(24)
        ]

        return {
            "total_events": len(valid_ts),
            "earliest_timestamp": min_ts,
            "latest_timestamp": max_ts,
            "earliest_iso": earliest_iso,
            "latest_iso": latest_iso,
            "monthly_distribution": monthly_dist,
            "hourly_distribution_utc": hourly_dist,
        }
