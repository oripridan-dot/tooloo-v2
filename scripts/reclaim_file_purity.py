import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tooloo_v4_hub.kernel.governance.living_map import get_living_map
from tooloo_v4_hub.kernel.governance.stamping import StampingEngine, SixWProtocol

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("PurityReclamation")

def reclaim_purity():
    logger.info("Sovereign Pulse: Initiating Global Purity Reclamation...")
    living_map = get_living_map()
    
    reclaimed_count = 0
    total_nodes = len(living_map.nodes)
    
    for node_id in living_map.nodes:
        path = Path(node_id)
        if not path.exists() or not path.is_file():
            continue
            
        if path.suffix not in [".py", ".md", ".json", ".js", ".css", ".html"]:
            continue

        try:
            content = path.read_text(errors="ignore")
            if not StampingEngine.is_stamped(content):
                logger.info(f"  -> Reclaiming Purity for: {node_id}")
                
                # Create a fresh 1.00 Purity 6W Protocol
                protocol = SixWProtocol(
                    who="Sovereign-Purity-Reclamation",
                    what=f"AUTONOMOUS_PURITY_RESTORATION: {path.name}",
                    where=str(path.relative_to(os.getcwd()) if os.getcwd() in str(path) else path.name),
                    why="Rule 10 Constitutional Accountability Enforcement",
                    how="Autonomous Ouroboros Pulse"
                )
                
                if path.suffix == ".py":
                    stamp = f"# {protocol.to_stamp()}"
                elif path.suffix in [".js", ".css"]:
                    stamp = f"/* {protocol.to_stamp()} */"
                elif path.suffix in [".html", ".md"]:
                    stamp = f"<!-- {protocol.to_stamp()} -->"
                else:
                    stamp = f"# {protocol.to_stamp()}" # Default to hash
                
                # Prepend stamp to content
                new_content = f"{stamp}\n{content}"
                path.write_text(new_content)
                reclaimed_count += 1
        except Exception as e:
            logger.error(f"  !! Failed to reclaim {node_id}: {e}")

    logger.info(f"Reclamation Complete: {reclaimed_count}/{total_nodes} nodes restored to 1.00 Purity.")

if __name__ == "__main__":
    reclaim_purity()
