# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: protocol_enforcer.py
# WHERE: tooloo_v4_hub/skills/
# WHY: Audits and terminates process threads that bypass consensus requirements.
# HOW: By inspecting process stage history and terminating violators via a process manager.

import asyncio
import logging

# Set up a logger for this skill's execution.
# This provides structured output without polluting stdout.
log = logging.getLogger(__name__)

# Define the canonical process stages and their sequence for protocol validation.
# In a larger system, these would likely be imported from a shared constants module.
CHAT_STAGE = "CHAT"
EXECUTE_STAGE = "EXECUTE"
STAGE_ORDER = ["INIT", "PLAN", "AWAIT_INPUT", CHAT_STAGE, EXECUTE_STAGE, "COMPLETE"]


async def process(arguments: dict) -> dict:
    """
    Audits active processes and terminates any that have bypassed the CHAT consensus protocol.

    This function expects a 'process_manager' object in the arguments, which provides
    an interface to query and terminate running processes. A process is considered
    in violation if it is in a stage that occurs after CHAT (e.g., EXECUTE) without
    having a record of achieving consensus in the CHAT stage.

    Args:
        arguments (dict): A dictionary containing necessary context, primarily:
            - 'process_manager': An object with async methods:
                - `get_active_processes()`: Returns a list of process-like objects.
                - `terminate_process(process_id)`: Terminates a process by its ID.
            Each process object is expected to have attributes:
            - `id` (str): Unique identifier.
            - `current_stage` (str): The name of the current stage.
            - `stage_history` (dict): A dictionary mapping stage names to their state data.

    Returns:
        dict: A summary of the audit and enforcement actions.
    """
    process_manager = arguments.get('process_manager')
    if not process_manager:
        log.error("`process_manager` not found in arguments. Cannot perform audit.")
        return {"status": "error", "message": "Missing 'process_manager' in arguments."}

    try:
        # Verify the process_manager has the methods we need to perform our function.
        if not all(hasattr(process_manager, attr) for attr in ['get_active_processes', 'terminate_process']):
            log.error("`process_manager` object is missing required methods ('get_active_processes', 'terminate_process').")
            return {"status": "error", "message": "Incompatible 'process_manager' object."}

        active_processes = await process_manager.get_active_processes()
    except Exception as e:
        log.exception(f"Failed to retrieve active processes via process_manager.")
        return {"status": "error", "message": f"Exception while getting processes: {e}"}

    terminated_processes = []
    audited_count = len(active_processes)
    log.info(f"Auditing {audited_count} active processes for protocol violations...")

    try:
        # Get the index of the CHAT stage to determine if a process has passed it.
        chat_stage_index = STAGE_ORDER.index(CHAT_STAGE)
    except ValueError:
        log.critical(f"Configuration error: '{CHAT_STAGE}' not in STAGE_ORDER. Audit aborted.")
        return {"status": "error", "message": "CHAT stage not defined in protocol."}

    for proc in active_processes:
        try:
            current_stage_index = STAGE_ORDER.index(proc.current_stage)
        except (ValueError, AttributeError):
            log.warning(f"Process {getattr(proc, 'id', 'UNKNOWN')} has an unknown or missing stage: '{getattr(proc, 'current_stage', 'MISSING')}'. Skipping.")
            continue

        # Violation check: Is the process in a stage that is ordered AFTER the CHAT stage?
        if current_stage_index > chat_stage_index:
            # It has passed the CHAT stage gate. Verify it did so legitimately.
            chat_history = proc.stage_history.get(CHAT_STAGE)

            # A violation occurs if there's no history for the CHAT stage,
            # or if the history exists but 'consensus_achieved' is not explicitly True.
            consensus_achieved = isinstance(chat_history, dict) and chat_history.get('consensus_achieved', False)

            if not consensus_achieved:
                proc_id = getattr(proc, 'id', 'UNIDENTIFIED')
                log.warning(
                    f"VIOLATION: Process {proc_id} in stage '{proc.current_stage}' "
                    f"without achieving consensus in '{CHAT_STAGE}'. Terminating."
                )
                try:
                    await process_manager.terminate_process(proc_id)
                    terminated_processes.append(proc_id)
                except Exception as e:
                    log.error(f"Failed to terminate violating process {proc_id}: {e}")

    summary = {
        "status": "success",
        "audited_processes": audited_count,
        "terminated_processes": terminated_processes,
        "violations_found": len(terminated_processes),
    }
    log.info(f"Protocol enforcement audit complete. Terminated {len(terminated_processes)} processes.")

    return summary