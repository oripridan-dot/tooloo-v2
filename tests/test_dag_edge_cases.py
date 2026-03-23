"""
tests/test_dag_edge_cases.py — Autonomous Edge-Case Explorer

Uses Hypothesis to continuously mutate the DAG topologies to ensure the
TopologicalSorter and Simulator handle property-based permutations without 
raising undocumented kernel breaks.
"""
from hypothesis import given, settings, strategies as st
import pytest
from engine.graph import TopologicalSorter, CycleDetectedError
from engine.simulation import BlastRadiusSimulator

# A strategy generating valid node IDs (alphanumeric slugs)
valid_node_id = st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')), min_size=1, max_size=12)

@st.composite
def dag_strategy(draw):
    """Generates a random acyclic DAG dependency list."""
    nodes = draw(st.lists(valid_node_id, min_size=1, max_size=20, unique=True))
    spec = []
    for i, node in enumerate(nodes):
        # Can only depend on previous nodes to guarantee no cycles
        if i == 0:
            deps = []
        else:
            deps = draw(st.lists(st.sampled_from(nodes[:i]), max_size=min(3, i), unique=True))
        spec.append((node, deps))
    return spec

@st.composite
def cycle_dag_strategy(draw):
    """Generates a DAG that is guaranteed to contain a cycle."""
    nodes = draw(st.lists(valid_node_id, min_size=2, max_size=10, unique=True))
    spec = [(node, []) for node in nodes]
    
    # Introduce a deterministic cycle
    n1 = nodes[0]
    n2 = nodes[1]
    
    # n1 depends on n2, and n2 depends on n1
    spec[0] = (n1, [n2])
    spec[1] = (n2, [n1])
    return spec

@given(dag_strategy())
@settings(max_examples=50)
def test_valid_topological_sort_never_crashes(spec):
    sorter = TopologicalSorter()
    waves = sorter.sort(spec)
    # The sum of all nodes in waves should equal the total number of unique nodes in spec
    node_set = {n for n, _ in spec}
    wave_nodes = {n for wave in waves for n in wave}
    assert node_set == wave_nodes

@given(cycle_dag_strategy())
@settings(max_examples=20)
def test_sorter_detects_cycles(spec):
    sorter = TopologicalSorter()
    with pytest.raises(CycleDetectedError):
        sorter.sort(spec)

@given(dag_strategy())
@settings(max_examples=10) # Heavy math, slower test
def test_blast_radius_simulator_handles_all_acyclic(spec):
    sorter = TopologicalSorter()
    simulator = BlastRadiusSimulator(sorter)
    result = simulator.simulate(spec)
    
    assert "status" in result
    assert result["status"] == "simulated"
    assert "safety_gate" in result
    assert "total_blast_radius" in result
    assert isinstance(result["prediction"], list)

