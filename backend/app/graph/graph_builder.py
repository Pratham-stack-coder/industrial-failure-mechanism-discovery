"""
Graph Construction Module
=========================
Builds a heterogeneous directed graph of industrial entities and events
using NetworkX. The graph is the input to graph-based mechanism discovery.

Node types:
  - machine      : Machine entity
  - batch        : Production batch
  - material_lot : Material lot
  - parameter    : Parameter definition
  - maintenance  : Maintenance event
  - process_change: Process change event
  - quality      : Quality inspection
  - failure      : Failure event

Edge types (directed):
  - PRODUCED_ON    : batch → machine
  - USES           : batch → material_lot
  - HAS_PARAMETER  : machine → parameter
  - MAINTAINED_BY  : machine → maintenance
  - HAD_QUALITY    : batch → quality
  - PRECEDED_BY    : event_a → event_b  (temporal precedence, lag_hours attribute)
  - CORRELATED_WITH: parameter_a → parameter_b  (from lag correlation analysis)
  - CAUSED_FAILURE : event → failure  (candidate attribution, set by mechanism discovery)

Graph is serialized to JSON for frontend visualization.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import pandas as pd
from loguru import logger


# ============================================================
# Graph construction
# ============================================================

class IndustrialGraph:
    """
    Heterogeneous directed graph of an industrial investigation context.

    Constructed from DataFrames loaded for a specific investigation time window.
    """

    def __init__(self):
        self.G = nx.DiGraph()
        self._node_counter: Dict[str, int] = {}

    def _add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        **attrs,
    ) -> str:
        """Add or update a node."""
        self.G.add_node(
            node_id,
            node_type=node_type,
            label=label,
            **attrs,
        )
        return node_id

    def _add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        weight: float = 1.0,
        **attrs,
    ) -> None:
        """Add a directed edge."""
        self.G.add_edge(
            source,
            target,
            edge_type=edge_type,
            weight=weight,
            **attrs,
        )

    def build_from_dataframes(
        self,
        machines_df: pd.DataFrame,
        batches_df: pd.DataFrame,
        material_lots_df: pd.DataFrame,
        batch_lots_df: pd.DataFrame,
        param_defs_df: pd.DataFrame,
        maintenance_df: pd.DataFrame,
        process_changes_df: pd.DataFrame,
        quality_df: pd.DataFrame,
        failure_events_df: pd.DataFrame,
        failure_time: Optional[datetime] = None,
        lookback_hours: float = 96.0,
    ) -> None:
        """Populate the graph from DataFrames for an investigation window."""

        if failure_time and failure_time.tzinfo is None:
            failure_time = failure_time.replace(tzinfo=timezone.utc)
        cutoff = (failure_time - timedelta(hours=lookback_hours)) if failure_time else None

        # ── Machine nodes ─────────────────────────────────────────────────
        for _, m in machines_df.iterrows():
            self._add_node(
                f"machine:{m['id']}",
                node_type="machine",
                label=str(m.get("name", m["id"])),
                machine_code=str(m.get("machine_code", "")),
                machine_type=str(m.get("machine_type", "")),
                status=str(m.get("status", "")),
            )

        # ── Batch nodes ───────────────────────────────────────────────────
        for _, b in batches_df.iterrows():
            batch_start = pd.to_datetime(b.get("start_time"), utc=True, errors="coerce")
            if cutoff and batch_start and batch_start < cutoff:
                continue

            bid = f"batch:{b['id']}"
            self._add_node(
                bid,
                node_type="batch",
                label=str(b.get("batch_number", b["id"])),
                is_defective=bool(b.get("is_defective", False)),
                defect_rate=float(b.get("defect_rate") or 0.0),
                start_time=str(b.get("start_time", "")),
            )

            # PRODUCED_ON edge: batch → machine
            mid = f"machine:{b['machine_id']}"
            if self.G.has_node(mid):
                self._add_edge(bid, mid, edge_type="PRODUCED_ON")

        # ── Material lot nodes ────────────────────────────────────────────
        for _, lot in material_lots_df.iterrows():
            self._add_node(
                f"lot:{lot['id']}",
                node_type="material_lot",
                label=str(lot.get("lot_number", lot["id"])),
                material_id=str(lot.get("material_id", "")),
                received_date=str(lot.get("received_date", "")),
            )

        # ── Batch-lot USES edges ──────────────────────────────────────────
        for _, bl in batch_lots_df.iterrows():
            batch_node = f"batch:{bl['batch_id']}"
            lot_node = f"lot:{bl['material_lot_id']}"
            if self.G.has_node(batch_node) and self.G.has_node(lot_node):
                self._add_edge(batch_node, lot_node, edge_type="USES")

        # ── Parameter nodes ───────────────────────────────────────────────
        for _, p in param_defs_df.iterrows():
            self._add_node(
                f"param:{p['id']}",
                node_type="parameter",
                label=str(p.get("name", p["id"])),
                parameter_code=str(p.get("parameter_code", "")),
                unit=str(p.get("unit", "")),
                nominal_value=float(p.get("nominal_value") or 0.0),
            )
            # HAS_PARAMETER: machine → parameter (for all machines initially)
            for _, m in machines_df.iterrows():
                self._add_edge(
                    f"machine:{m['id']}",
                    f"param:{p['id']}",
                    edge_type="HAS_PARAMETER",
                )

        # ── Maintenance event nodes ───────────────────────────────────────
        for _, me in maintenance_df.iterrows():
            t = pd.to_datetime(me.get("start_time"), utc=True, errors="coerce")
            if cutoff and t and t < cutoff:
                continue
            node_id = f"maintenance:{me['id']}"
            self._add_node(
                node_id,
                node_type="maintenance",
                label=f"Maint:{me.get('maintenance_type','')}",
                maintenance_type=str(me.get("maintenance_type", "")),
                timestamp=str(me.get("start_time", "")),
                duration_hours=float(me.get("duration_hours") or 0.0),
                description=str(me.get("description", "")),
            )
            # MAINTAINED_BY: machine → maintenance
            mid = f"machine:{me['machine_id']}"
            if self.G.has_node(mid):
                self._add_edge(mid, node_id, edge_type="MAINTAINED_BY")

        # ── Process change nodes ──────────────────────────────────────────
        for _, pc in process_changes_df.iterrows():
            t = pd.to_datetime(pc.get("change_time"), utc=True, errors="coerce")
            if cutoff and t and t < cutoff:
                continue
            node_id = f"process_change:{pc['id']}"
            self._add_node(
                node_id,
                node_type="process_change",
                label=f"PC:{pc.get('change_type','')}",
                change_type=str(pc.get("change_type", "")),
                parameter_name=str(pc.get("parameter_name", "")),
                timestamp=str(pc.get("change_time", "")),
                old_value=str(pc.get("old_value", "")),
                new_value=str(pc.get("new_value", "")),
            )

        # ── Quality inspection nodes ──────────────────────────────────────
        for _, qi in quality_df.iterrows():
            t = pd.to_datetime(qi.get("inspection_time"), utc=True, errors="coerce")
            if cutoff and t and t < cutoff:
                continue
            node_id = f"quality:{qi['id']}"
            result = str(qi.get("result", ""))
            self._add_node(
                node_id,
                node_type="quality",
                label=f"QI:{result}",
                result=result,
                defect_rate=float(qi.get("defect_rate") or 0.0),
                timestamp=str(qi.get("inspection_time", "")),
                defect_types=qi.get("defect_types", []),
            )
            batch_node = f"batch:{qi['batch_id']}"
            if self.G.has_node(batch_node):
                self._add_edge(batch_node, node_id, edge_type="HAD_QUALITY")

        # ── Failure event nodes ───────────────────────────────────────────
        for _, fe in failure_events_df.iterrows():
            node_id = f"failure:{fe['id']}"
            self._add_node(
                node_id,
                node_type="failure",
                label=f"FAILURE:{fe.get('event_type','')}",
                severity=str(fe.get("severity", "")),
                event_type=str(fe.get("event_type", "")),
                timestamp=str(fe.get("event_time", "")),
                description=str(fe.get("description", "")),
            )

        # ── Temporal precedence edges ─────────────────────────────────────
        self._add_temporal_precedence_edges(failure_time)

        logger.debug(
            f"Graph built: {self.G.number_of_nodes()} nodes, "
            f"{self.G.number_of_edges()} edges"
        )

    def _add_temporal_precedence_edges(
        self,
        failure_time: Optional[datetime],
    ) -> None:
        """
        Add PRECEDES edges between events based on timestamp ordering.
        Only connects events of types that make semantic sense.
        """
        if failure_time is None:
            return

        temporal_node_types = {"maintenance", "process_change", "quality", "failure"}
        time_nodes = []
        for node, attrs in self.G.nodes(data=True):
            if attrs.get("node_type") in temporal_node_types:
                ts_str = attrs.get("timestamp", "")
                try:
                    ts = pd.to_datetime(ts_str, utc=True)
                    if pd.notna(ts):
                        time_nodes.append((node, ts, attrs.get("node_type")))
                except Exception:
                    pass

        # Sort by timestamp
        time_nodes.sort(key=lambda x: x[1])

        # Connect maintenance/process_change nodes to downstream quality/failure
        failure_nodes = [(n, t, nt) for n, t, nt in time_nodes if nt == "failure"]

        for fail_node, fail_time, _ in failure_nodes:
            for node, ts, ntype in time_nodes:
                if ntype in {"maintenance", "process_change"} and ts < fail_time:
                    lag_h = (fail_time - ts).total_seconds() / 3600.0
                    if lag_h <= 120:  # only link if within 5 days
                        self._add_edge(
                            node,
                            fail_node,
                            edge_type="PRECEDES",
                            lag_hours=round(lag_h, 2),
                            weight=1.0 / max(1.0, lag_h),  # closer = stronger
                        )

    def add_correlation_edges(
        self,
        correlations: List[Tuple[str, str, float, float]],
        # List of (param_a_code, param_b_code, correlation, lag_hours)
    ) -> None:
        """Add CORRELATED_WITH edges between parameter nodes."""
        for param_a, param_b, corr, lag_h in correlations:
            # Find parameter nodes by code
            a_node = next(
                (n for n, d in self.G.nodes(data=True)
                 if d.get("parameter_code") == param_a), None
            )
            b_node = next(
                (n for n, d in self.G.nodes(data=True)
                 if d.get("parameter_code") == param_b), None
            )
            if a_node and b_node:
                self._add_edge(
                    a_node,
                    b_node,
                    edge_type="CORRELATED_WITH",
                    correlation=round(corr, 4),
                    lag_hours=round(lag_h, 2),
                    weight=abs(corr),
                )

    # ── Analysis methods ─────────────────────────────────────────────────────

    def get_nodes_by_type(self, node_type: str) -> List[Tuple[str, Dict]]:
        return [
            (n, d) for n, d in self.G.nodes(data=True)
            if d.get("node_type") == node_type
        ]

    def get_predecessors_within_lag(
        self,
        target_node: str,
        max_lag_hours: float = 48.0,
    ) -> List[Tuple[str, Dict, float]]:
        """Get all predecessors of target_node within a temporal lag window."""
        results = []
        for src, tgt, edge_data in self.G.in_edges(target_node, data=True):
            lag = edge_data.get("lag_hours", 0.0)
            if lag <= max_lag_hours:
                results.append((src, self.G.nodes[src], lag))
        return sorted(results, key=lambda x: x[2])

    def find_paths_to_failure(
        self,
        failure_node: str,
        max_depth: int = 4,
    ) -> List[List[str]]:
        """Find all simple paths leading to a failure node."""
        predecessors = [
            n for n in self.G.nodes
            if n != failure_node and nx.has_path(self.G, n, failure_node)
        ]
        paths = []
        for pred in predecessors:
            try:
                for path in nx.all_simple_paths(
                    self.G, source=pred, target=failure_node, cutoff=max_depth
                ):
                    paths.append(path)
            except Exception:
                pass
        # Deduplicate and sort by length
        seen = set()
        unique_paths = []
        for p in paths:
            key = tuple(p)
            if key not in seen:
                seen.add(key)
                unique_paths.append(p)
        return sorted(unique_paths, key=len, reverse=True)[:20]

    def compute_graph_metrics(self) -> Dict[str, Any]:
        """Compute basic graph metrics for the investigation graph."""
        try:
            return {
                "n_nodes": self.G.number_of_nodes(),
                "n_edges": self.G.number_of_edges(),
                "is_dag": nx.is_directed_acyclic_graph(self.G),
                "density": round(nx.density(self.G), 4),
                "node_type_counts": {
                    nt: len(self.get_nodes_by_type(nt))
                    for nt in [
                        "machine", "batch", "material_lot", "parameter",
                        "maintenance", "process_change", "quality", "failure"
                    ]
                },
            }
        except Exception as e:
            logger.warning(f"Graph metrics computation failed: {e}")
            return {"error": str(e)}

    def to_json(self) -> Dict[str, Any]:
        """Serialize graph to JSON for frontend visualization (D3/Cytoscape format)."""
        nodes = []
        for node_id, attrs in self.G.nodes(data=True):
            nodes.append({
                "id": node_id,
                "label": attrs.get("label", node_id),
                "node_type": attrs.get("node_type", "unknown"),
                **{k: v for k, v in attrs.items() if k not in ("label", "node_type")},
            })

        edges = []
        for src, tgt, attrs in self.G.edges(data=True):
            edges.append({
                "source": src,
                "target": tgt,
                "edge_type": attrs.get("edge_type", ""),
                **{k: v for k, v in attrs.items() if k != "edge_type"},
            })

        return {"nodes": nodes, "edges": edges, "metrics": self.compute_graph_metrics()}
