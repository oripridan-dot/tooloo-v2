# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: protocolintegrity_lock.py
# WHERE: tooloo_v4_hub/skills/

import asyncio
import logging
from datetime import datetime

# --- Configuration ---
# In a real system, this would be loaded from a secure configuration store.
CRITICAL_ACTIONS = {
    'core_config_update',
    'data_purge',
    'shutdown_primary',
    'security_policy_change',
    'consensus_bypass_enable',
}

# Define quorum requirements based on system state
QUORUM_REQUIREMENTS = {
    'NOMINAL': 1,
    'DEGRADED': 2,
    'ALERT': 3,
}

# A simplistic representation of a valid, perhaps time-sensitive, override code
VALID_OVERRIDE_CODE = "EMERGENCY_OVERRIDE_777"

# --- Logger Setup ---
# Use a dedicated logger for this skill to avoid polluting the root logger.
# This helps in filtering and analyzing logs specifically from this integrity lock.
log = logging.getLogger('ProtocolIntegrityLock')
log.setLevel(logging.INFO)
# In a real hub, a handler would already be configured. If not, add one for standalone testing:
# if not log.hasHandlers():
#     handler = logging.StreamHandler()
#     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#     handler.setFormatter(formatter)
#     log.addHandler(handler)


class ProtocolIntegrityError(Exception):
    """Custom exception for protocol violations."""
    pass


async def _check_override(auth_details: dict) -> bool:
    """Checks for a valid administrative override code."""
    override_code = auth_details.get('override_code')
    if override_code and override_code == VALID_OVERRIDE_CODE:
        log.warning(
            "[OVERRIDE] Valid override code used. Bypassing standard checks."
        )
        return True
    return False


async def _check_state_and_quorum(system_state: str, action: str, auth_details: dict):
    """
    Verifies that actions in DEGRADED or ALERT states have sufficient authorization.
    Critical actions always require a higher bar.
    """
    if system_state not in QUORUM_REQUIREMENTS:
        raise ProtocolIntegrityError(f"Invalid system state '{system_state}' provided.")

    required_quorum = QUORUM_REQUIREMENTS[system_state]
    mfa_present = auth_details.get('mfa_present', False)
    approvals = auth_details.get('quorum_approvals', 0)

    # For non-nominal states, elevate requirements
    if system_state != 'NOMINAL':
        if not mfa_present:
            raise ProtocolIntegrityError(
                f"MFA is required for all actions in {system_state} state."
            )
        if approvals < required_quorum:
            raise ProtocolIntegrityError(
                f"Insufficient quorum. Action requires {required_quorum} approvals in "
                f"{system_state} state, but only {approvals} were provided."
            )


async def _check_critical_action_safeguards(action: str, auth_details: dict):
    """Ensures critical actions have a corresponding change request ID."""
    if action in CRITICAL_ACTIONS:
        change_request_id = auth_details.get('change_request_id')
        if not change_request_id:
            raise ProtocolIntegrityError(
                f"Critical action '{action}' requires a valid Change Request ID. None provided."
            )
        log.info(f"Critical action '{action}' validated against CR ID '{change_request_id}'.")


async def process(arguments: dict) -> any:
    """
    Programmatically blocks consensus bypasses and flags unauthorized deviations.

    This skill acts as a security gatekeeper. It evaluates an incoming action
    request against a set of protocol integrity rules. If any rule is violated,
    the action is denied, and an alert is logged.

    Expected arguments:
    {
        'system_state': str,  # 'NOMINAL', 'DEGRADED', 'ALERT'
        'action': str,        # The action being attempted (e.g., 'core_config_update')
        'user': str,          # The user or service principal requesting the action
        'authorization': {
            'mfa_present': bool,
            'quorum_approvals': int,
            'change_request_id': str | None,
            'override_code': str | None
        }
    }

    Returns:
    A dictionary indicating the outcome.
    {'status': 'APPROVED', 'message': '...'} on success.
    {'status': 'DENIED', 'reason': '...'} on failure.
    """
    try:
        # --- 1. Extract and Validate Inputs ---
        system_state = arguments.get('system_state')
        action = arguments.get('action')
        user = arguments.get('user', 'UnknownUser')
        auth_details = arguments.get('authorization', {})

        if not all([system_state, action, isinstance(auth_details, dict)]):
            raise ProtocolIntegrityError("Invalid or incomplete arguments provided.")

        log.info(
            f"[ENTRY] Evaluating action '{action}' by user '{user}' in state '{system_state}'."
        )

        # --- 2. Check for Administrative Override ---
        # An override bypasses standard procedure but is still logged for audit.
        if await _check_override(auth_details):
            return {
                'status': 'APPROVED',
                'message': f"Action '{action}' approved via administrative override.",
                'user': user,
                'timestamp': datetime.utcnow().isoformat()
            }

        # --- 3. Execute Protocol Integrity Checks ---
        # Each check function will raise ProtocolIntegrityError on failure.
        await _check_state_and_quorum(system_state, action, auth_details)
        await _check_critical_action_safeguards(action, auth_details)

        # --- 4. If all checks pass, approve the action ---
        log.info(f"[PASS] Action '{action}' by user '{user}' conforms to protocol.")
        return {
            'status': 'APPROVED',
            'message': 'Action approved. All protocol integrity checks passed.',
            'user': user,
            'timestamp': datetime.utcnow().isoformat()
        }

    except ProtocolIntegrityError as e:
        # --- 5. On failure, deny the action and log an alert ---
        error_message = str(e)
        log.error(
            f"[PROTOCOL_INTEGRITY_ALERT] Action '{action}' by user '{user}' DENIED. "
            f"Reason: {error_message}"
        )
        return {
            'status': 'DENIED',
            'reason': error_message,
            'user': user,
            'action': action,
            'system_state': arguments.get('system_state'),
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.critical(f"[INTERNAL_ERROR] An unexpected error occurred: {e}", exc_info=True)
        return {
            'status': 'ERROR',
            'reason': f'Internal skill error: {e}'
        }