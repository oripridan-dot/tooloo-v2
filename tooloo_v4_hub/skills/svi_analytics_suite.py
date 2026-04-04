# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: svi_analytics_suite.py
# WHERE: tooloo_v4_hub/skills/

import asyncio
import json
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

# --- Configuration ---
# Define the components of the Sovereign Vitality Index and their weights.
# These weights represent the relative importance of each component to overall system health.
SVI_COMPONENTS = {
    "coherence": {"weight": 0.25, "description": "Logical consistency and predictability."},
    "agency": {"weight": 0.15, "description": "Capacity for independent, goal-directed action."},
    "resilience": {"weight": 0.20, "description": "Ability to recover from perturbation and maintain function."},
    "creativity": {"weight": 0.10, "description": "Generation of novel and valuable outputs."},
    "integrity": {"weight": 0.30, "description": "Adherence to core principles and operational directives."}
}

# Thresholds for SVI interpretation.
SVI_THRESHOLDS = {
    0.95: "PEAK",
    0.90: "OPTIMAL",
    0.80: "STABLE",
    0.70: "NOMINAL",
    0.60: "DEGRADED",
    0.00: "CRITICAL"
}


# --- Helper Functions ---

def _parse_svi_data(raw_data: Any) -> List[Dict[str, Any]]:
    """
    Parses raw SVI data, which can be a JSON string or a Python list of dicts.
    Validates that each record contains the required SVI components.
    """
    if isinstance(raw_data, str):
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in svi_data: {e}")
    elif isinstance(raw_data, list):
        data = raw_data
    else:
        raise TypeError("svi_data must be a JSON string or a list of dictionaries.")

    if not data:
        raise ValueError("svi_data is empty. No data to analyze.")

    # Validate structure of the first record as a quick check
    first_record = data[0]
    if not isinstance(first_record, dict):
        raise ValueError("Data records must be dictionaries.")
        
    required_keys = set(SVI_COMPONENTS.keys())
    if 'timestamp' not in first_record or not required_keys.issubset(first_record.keys()):
        missing = required_keys - set(first_record.keys())
        raise ValueError(f"Data records are missing required keys. Missing: {missing or 'timestamp'}")

    return data

def _analyze_components(data: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Calculates statistical metrics for each SVI component across all data points.
    """
    analysis = {}
    for component in SVI_COMPONENTS.keys():
        values = [record[component] for record in data if component in record and isinstance(record[component], (int, float))]
        
        if not values:
            analysis[component] = {
                "mean": 0.0, "median": 0.0, "stdev": 0.0,
                "min": 0.0, "max": 0.0, "count": 0
            }
            continue

        analysis[component] = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }
    return analysis

def _calculate_svi(component_analysis: Dict[str, Dict[str, float]]) -> Tuple[float, Dict[str, float]]:
    """
    Calculates the overall SVI score as a weighted average of component means.
    """
    svi_score = 0.0
    mean_values = {}
    for component, details in SVI_COMPONENTS.items():
        weight = details["weight"]
        mean_val = component_analysis.get(component, {}).get("mean", 0.0)
        svi_score += mean_val * weight
        mean_values[component] = mean_val
    
    return svi_score, mean_values

def _interpret_svi(score: float) -> str:
    """Provides a qualitative interpretation of the SVI score."""
    for threshold, interpretation in sorted(SVI_THRESHOLDS.items(), reverse=True):
        if score >= threshold:
            return interpretation
    return "UNKNOWN"

def _generate_summary(svi_score: float, interpretation: str, component_analysis: Dict[str, Dict[str, float]]) -> str:
    """Generates a human-readable summary of the analysis."""
    strongest_component = max(component_analysis, key=lambda c: component_analysis[c]['mean'])
    weakest_component = min(component_analysis, key=lambda c: component_analysis[c]['mean'])
    
    summary = (
        f"Sovereign Vitality Index (SVI) is {svi_score:.3f}, indicating a '{interpretation}' state. "
        f"Analysis of {component_analysis[strongest_component]['count']} data points shows "
        f"the strongest contributing factor is '{strongest_component}' (mean: {component_analysis[strongest_component]['mean']:.3f}). "
        f"The weakest factor is '{weakest_component}' (mean: {component_analysis[weakest_component]['mean']:.3f}). "
    )
    
    # Check for high volatility
    volatile_components = [
        c for c, stats in component_analysis.items() if stats['stdev'] > 0.15
    ]
    if volatile_components:
        summary += f"High volatility detected in: {', '.join(volatile_components)}. "
    
    return summary

def _get_metadata(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extracts metadata from the dataset."""
    timestamps = [
        datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00'))
        for r in data if 'timestamp' in r
    ]
    
    return {
        "data_points": len(data),
        "start_time": min(timestamps).isoformat() if timestamps else None,
        "end_time": max(timestamps).isoformat() if timestamps else None,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat()
    }


async def process(arguments: dict) -> dict:
    """
    Parses, analyzes, and reports on the Sovereign Vitality Index (SVI).

    Args:
        arguments (dict): A dictionary containing:
            - 'svi_data': A list of dictionaries or a JSON string representing
                          SVI data points. Each point should have a 'timestamp'
                          and keys for each SVI component (e.g., 'coherence',
                          'agency').
            - 'mode' (str, optional): The analysis mode. Defaults to 'full'.
              'summary': Returns only the SVI score and interpretation.
              'full': Returns a comprehensive report.

    Returns:
        A dictionary containing the SVI analysis report.
    """
    try:
        raw_data = arguments.get("svi_data")
        if raw_data is None:
            raise ValueError("Missing 'svi_data' in arguments.")

        mode = arguments.get("mode", "full")

        # Simulate async work for environment compatibility
        await asyncio.sleep(0) 

        # 1. Parse and Validate Data
        data = _parse_svi_data(raw_data)

        # 2. Analyze Component Metrics
        component_analysis = _analyze_components(data)
        
        # 3. Calculate Overall SVI
        svi_score, mean_values = _calculate_svi(component_analysis)
        
        # 4. Interpret Score
        interpretation = _interpret_svi(svi_score)

        # 5. Generate Report based on mode
        if mode == "summary":
            return {
                "svi_score": svi_score,
                "interpretation": interpretation
            }
        
        # Default to 'full' report
        summary_text = _generate_summary(svi_score, interpretation, component_analysis)
        metadata = _get_metadata(data)

        return {
            "status": "success",
            "metadata": metadata,
            "report": {
                "svi_score": svi_score,
                "interpretation": interpretation,
                "summary": summary_text,
                "component_means": mean_values,
                "component_statistics": component_analysis
            }
        }

    except (ValueError, TypeError, KeyError) as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }
    except Exception as e:
        # Catch-all for unexpected errors
        return {
            "status": "error",
            "error_type": "InternalServerError",
            "message": f"An unexpected error occurred: {e}"
        }