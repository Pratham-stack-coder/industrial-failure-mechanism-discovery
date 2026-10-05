"""
Unit tests for Industrial Graph Construction
"""

import pytest
import pandas as pd
from datetime import datetime, timezone
from app.graph.graph_builder import IndustrialGraph


def test_graph_node_and_edge_addition():
    graph = IndustrialGraph()
    n1 = graph._add_node("m_1", "machine", "Milling Station 1")
    n2 = graph._add_node("b_1", "batch", "Batch-2024-001")

    assert graph.G.has_node("m_1")
    assert graph.G.has_node("b_1")

    graph._add_edge("b_1", "m_1", "PRODUCED_ON")
    assert graph.G.has_edge("b_1", "m_1")


def test_graph_metrics_and_json_serialization():
    graph = IndustrialGraph()
    graph._add_node("m_1", "machine", "Machine 1")
    graph._add_node("p_1", "parameter", "Coolant Flow")
    graph._add_edge("m_1", "p_1", "HAS_PARAMETER")

    metrics = graph.compute_graph_metrics()
    assert metrics["n_nodes"] == 2
    assert metrics["n_edges"] == 1

    json_data = graph.to_json()
    assert "nodes" in json_data
    assert "edges" in json_data
    assert len(json_data["nodes"]) == 2
    assert len(json_data["edges"]) == 1
    assert json_data["nodes"][0]["node_type"] in ["machine", "parameter"]
