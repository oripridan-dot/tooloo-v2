# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: consensuscompliancedaemon.py
# WHERE: tooloo_v4_hub/skills/

import asyncio
import logging
from typing import List, Dict, Any, Coroutine

# Set up a logger for this skill for better diagnostics in a hub environment.
# This avoids polluting stdout which might be used for data piping.
logger = logging.getLogger(__name__)
# In a real hub, this would be configured by the hub's logging setup.
# For standalone testing, we can add a basic handler.
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

async def process(arguments: dict) -> Dict[str, Any]:
    """
    Monitors process interaction stages against a consensus protocol,
    identifies deviations, and recommends quarantine actions for rogue processes.

    This skill is designed to be called periodically by a scheduler within the
    tooloo_v4_hub. It is stateless and relies entirely on the 'arguments'
    for the current state of the system.

    Args:
        arguments (dict): A dictionary expected to contain:
            - 'processes' (List[Dict]): A list of active processes to audit.
              Each process dict must have:
                - 'id' (str): A unique process identifier.
                - 'stage_history' (List[str]): An ordered list of stages
                  the process has transitioned through.
            - 'consensus_protocol' (Dict[str, List[str]]): Defines the valid
              state machine. Keys are source stages, and values are lists of
              valid destination stages. A special '__initial__' key can define
              valid starting points.

    Returns:
        Dict[str, Any]: A report summarizing the audit, including:
            - 'status' (str): 'ok' for successful execution.
            - 'processes_audited' (int): The number of processes checked.
            - 'deviations_found' (int): The count of non-compliant processes.
            - 'quarantine_actions' (List[Dict]): A list of recommended actions
              for the hub to take against non-compliant processes.
    """
    logger.info("Consensus compliance daemon starting audit...")

    processes: List[Dict[str, Any]] = arguments.get('processes', [])
    protocol: Dict[str, List[str]] = arguments.get('consensus_protocol', {})

    if not processes or not protocol:
        logger.warning("Missing 'processes' or 'consensus_protocol' in arguments. Audit aborted.")
        return {
            "status": "error",
            "message": "Input 'processes' or 'consensus_protocol' not provided.",
            "processes_audited": 0,
            "deviations_found": 0,
            "quarantine_actions": [],
        }

    flagged_deviations: List[Dict[str, Any]] = []
    quarantine_actions: List[Dict[str, Any]] = []

    for process_data in processes:
        process_id = process_data.get('id', 'unknown_process')
        history = process_data.get('stage_history', [])

        if not history or len(history) < 2:
            # A process with 0 or 1 stage cannot have an invalid transition.
            continue

        # Check if the very first stage is a valid initial stage, if defined.
        initial_stages = protocol.get('__initial__')
        if initial_stages and history[0] not in initial_stages:
            reason = f"Invalid initial stage '{history[0]}'. Valid initial stages are: {initial_stages}."
            logger.warning(f"Process '{process_id}' flagged: {reason}")
            flagged_deviations.append({'process_id': process_id, 'reason': reason})
            quarantine_actions.append({'action': 'quarantine', 'target_pid': process_id, 'reason': reason})
            continue # Move to the next process once a deviation is found.

        # Check all subsequent stage transitions in the history.
        for i in range(len(history) - 1):
            current_stage = history[i]
            next_stage = history[i+1]

            valid_next_stages = protocol.get(current_stage, [])

            if next_stage not in valid_next_stages:
                reason = (f"Invalid stage transition from '{current_stage}' to '{next_stage}'. "
                          f"Valid next stages were: {valid_next_stages}.")
                logger.warning(f"Process '{process_id}' flagged: {reason}")
                
                flagged_deviations.append({
                    'process_id': process_id,
                    'reason': reason,
                    'invalid_transition': {
                        'from': current_stage,
                        'to': next_stage
                    }
                })
                
                quarantine_actions.append({
                    'action': 'quarantine',
                    'target_pid': process_id,
                    'reason': reason
                })
                # Once a deviation is found, we flag the process and move on.
                # No need to check for further deviations in the same process.
                break
    
    logger.info(f"Audit complete. Audited {len(processes)} processes, found {len(flagged_deviations)} deviations.")

    return {
        "status": "ok",
        "processes_audited": len(processes),
        "deviations_found": len(flagged_deviations),
        "quarantine_actions": quarantine_actions,
    }