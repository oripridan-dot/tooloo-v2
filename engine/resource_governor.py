"""
engine/resource_governor.py — Hardware-Aware Resource Throttling

Monitors real-time RAM/CPU pressure. On heavy load (e.g. M1 with 8GB RAM),
it dynamically downshifts the N-Stroke Engine's max_strokes and regulates concurrency.
"""
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    psutil = None
    _HAS_PSUTIL = False

import logging

logger = logging.getLogger(__name__)

class ResourceGovernor:
    @staticmethod
    def get_recommended_strokes(default_strokes: int = 7) -> int:
        """Returns the recommended max strokes based on system memory pressure."""
        if not _HAS_PSUTIL:
            return default_strokes

        try:
            mem = psutil.virtual_memory()
            mem_usage_percent = mem.percent
            
            if mem_usage_percent > 85.0:
                logger.warning(f"High memory usage ({mem_usage_percent}%). Throttling strokes to 2.")
                return min(2, default_strokes)
            if mem_usage_percent > 70.0:
                logger.warning(f"Moderate memory usage ({mem_usage_percent}%). Throttling strokes to 4.")
                return min(4, default_strokes)
                
            return default_strokes
        except Exception as e:
            logger.error(f"ResourceGovernor failed to read memory: {e}")
            return default_strokes
            
    @staticmethod
    def get_throttle_log_entry() -> dict:
        """Fetch current hardware stats for logging."""
        if not _HAS_PSUTIL:
            return {}

        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "ram_percent": psutil.virtual_memory().percent
            }
        except:
            return {}

