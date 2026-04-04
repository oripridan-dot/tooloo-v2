# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: drift_interceptor.py
# WHERE: tooloo_v4_hub/skills/

import asyncio
from typing import Dict, Any

# --- Architectural Protocol Definitions ---
# This dictionary defines the "consensus" model. It maps action prefixes
# to a set of rules that must be met. This prevents unauthorized direct calls
# to sensitive operations, forcing them through established workflows that
# would provide the required keys (e.g., tokens, transaction IDs).

ARCHITECTURAL_PROTOCOLS = {
    "core.config.write": {
        "required_keys": ["change_request_id", "auth_context"],
        "description": "Modification of core configuration requires an approved Change Request ID and a valid authorization context."
    },
    "system.memory.unsafe_mutate": {
        "required_keys": ["quarantine_sandbox_id", "supervisor_approval_token"],
        "description": "Direct memory mutation is a restricted operation and must occur within a quarantined sandbox with supervisor approval."
    },
    "data.store.delete_collection": {
        "required_keys": ["double_confirmation_token", "backup_snapshot_id"],
        "description": "Collection deletion is a destructive act requiring explicit user double-confirmation and a completed pre-deletion backup snapshot."
    },
    "identity.assume_role": {
        "required_keys": ["mfa_token", "session_correlation_id"],
        "description": "Assuming a new role requires multi-factor authentication and must be correlated with an existing session."
    }
}

async def process(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scans an incoming action request and blocks it if it violates
    established architectural protocols, preventing consensus bypasses.

    Args:
        arguments: A dictionary expected to contain an 'action' key
                   and other contextual parameters for the action.

    Returns:
        A dictionary indicating the status of the scan ('approved' or 'rejected')
        and a reason for the decision.
    """
    action_to_evaluate = arguments.get("action")

    if not action_to_evaluate:
        return {
            "status": "rejected",
            "code": "DRIFT-E400-NO_ACTION",
            "reason": "Malformed request. No 'action' key found for interception scan.",
            "policy_violation": True
        }

    # Iterate through protected protocols to see if the action matches.
    for protocol_action, rules in ARCHITECTURAL_PROTOCOLS.items():
        if action_to_evaluate == protocol_action:
            # The action is protected. We must validate its context.
            required_keys = rules.get("required_keys", [])
            missing_keys = [key for key in required_keys if key not in arguments]

            if missing_keys:
                # A required key is missing. This is a consensus bypass attempt.
                return {
                    "status": "rejected",
                    "code": "DRIFT-E403-PROTOCOL_VIOLATION",
                    "reason": "Consensus bypass attempt detected. The action violates established protocols.",
                    "details": {
                        "action": action_to_evaluate,
                        "required_protocol": rules.get("description"),
                        "missing_context": missing_keys
                    },
                    "policy_violation": True
                }

    # If the loop completes without finding a violation, the action is not
    # explicitly protected or it meets the requirements.
    return {
        "status": "approved",
        "code": "DRIFT-I200-OK",
        "reason": f"Action '{action_to_evaluate}' adheres to all established architectural protocols.",
        "policy_violation": False
    }