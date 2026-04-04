# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: :_verified_purge_protocol.**.py
# WHERE: tooloo_v4_hub/skills/
# WHY: To provide a safe, two-factor authenticated method for deleting files and directories.
# WHEN: 2023-10-27
# HOW: By requiring a specific confirmation string and performing rigorous safety checks before executing the deletion using pathlib and shutil.

import os
import shutil
import asyncio
from pathlib import Path

# The exact string required to authorize the destructive purge operation.
CONFIRMATION_PHRASE = "PURGE_SEQUENCE_AUTHORIZED_DESTRUCTIVE_ACTION"

async def process(arguments: dict) -> dict:
    """
    Securely and permanently deletes a file or directory after explicit verification.

    This is a destructive, non-recoverable operation. It includes several safety
    checks to prevent accidental deletion of critical system paths, the user's
    home directory, or the current working directory.

    Args:
        arguments (dict): A dictionary requiring the following keys:
            - 'path' (str): The relative or absolute path to the target
              file or directory that will be purged.
            - 'confirmation' (str): Must match the hardcoded CONFIRMATION_PHRASE
              to authorize the deletion.

    Returns:
        dict: A dictionary containing the 'status' ('success' or 'error')
              and a 'message' detailing the outcome.
    """
    path_str = arguments.get('path')
    confirmation = arguments.get('confirmation')

    if not path_str:
        return {'status': 'error', 'message': 'Missing required "path" argument.'}

    if confirmation != CONFIRMATION_PHRASE:
        return {
            'status': 'error',
            'message': f"Confirmation failed. The provided token does not authorize the purge operation.",
            'note': f"The required confirmation phrase is not returned for security."
        }

    try:
        # Resolve to an absolute path to make safety checks reliable
        target_path = Path(path_str).resolve()
        cwd = Path.cwd().resolve()
        home = Path.home().resolve()

        # --- SAFETY CHECKS ---
        if not target_path.exists():
            return {'status': 'error', 'message': f"Path does not exist: {target_path}"}

        critical_paths = {
            '/', '/etc', '/usr', '/bin', '/sbin', '/var', '/lib', '/boot', '/dev', '/proc', '/sys',
            str(home), str(cwd)
        }
        if str(target_path) in critical_paths:
            return {'status': 'error', 'message': f"CRITICAL: Deletion of protected path ('{target_path}') is forbidden."}

        # Prevent deleting a parent directory of the current working directory
        if cwd.is_relative_to(target_path) and cwd != target_path:
             return {'status': 'error', 'message': f"CRITICAL: Deletion of an ancestor of the current directory ('{target_path}') is forbidden."}

        # --- DELETION LOGIC ---
        # Run the blocking I/O operation in a separate thread
        def blocking_delete():
            if target_path.is_dir():
                shutil.rmtree(target_path)
                return f"Directory purged successfully: {target_path}"
            elif target_path.is_file() or target_path.is_symlink():
                target_path.unlink()
                return f"File/Link purged successfully: {target_path}"
            else:
                # Should be rare, but handles things like block devices, etc.
                raise OSError(f"Path is not a regular file or directory: {target_path}")

        loop = asyncio.get_running_loop()
        message = await loop.run_in_executor(None, blocking_delete)

        return {'status': 'success', 'message': message}

    except PermissionError:
        return {'status': 'error', 'message': f"Permission denied. Could not purge path: {path_str}"}
    except OSError as e:
        return {'status': 'error', 'message': f"OS error during purge: {e}"}
    except Exception as e:
        return {'status': 'error', 'message': f"An unexpected error occurred: {str(e)}"}