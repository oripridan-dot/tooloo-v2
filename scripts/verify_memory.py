from engine.graph import CognitiveGraph
from engine.memory import memory_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MemoryVerification")

def run_verification():
    # 1. Create a graph
    graph = CognitiveGraph()
    graph.add_node("root", type="goal", status="planned")
    graph.add_node("child", type="task", status="pending")
    graph.add_edge("root", "child")
    
    logger.info("Created test graph with 2 nodes and 1 edge.")
    
    # 2. Save the graph
    graph_name = "test_continuity"
    memory_manager.save_graph(graph_name, graph)
    logger.info(f"Saved graph '{graph_name}'")
    
    # 3. Load the graph
    loaded_graph = memory_manager.load_graph(graph_name)
    if not loaded_graph:
        logger.error("Failed to load graph!")
        return
    
    # 4. Verify
    nodes = loaded_graph.nodes()
    edges = loaded_graph.edges()
    
    logger.info(f"Loaded nodes: {nodes}")
    logger.info(f"Loaded edges: {edges}")
    
    assert "root" in nodes
    assert "child" in nodes
    assert ("root", "child") in edges
    
    logger.info("✅ SUCCESS: Cross-session continuity verified!")

if __name__ == "__main__":
    run_verification()
