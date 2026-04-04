# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: .**.py
# WHERE: tooloo_v4_hub/skills/
# WHY: To provide a powerful, recursive file searching utility, interpreting the '**' from shell globbing as the core function of the skill.
# WHEN: 2023-11-20
# HOW: The skill uses Python's `pathlib` to perform a recursive glob (`rglob`). It's wrapped in `asyncio.to_thread` to ensure non-blocking execution in the async environment. It intelligently parses arguments for a search path and a pattern.

import asyncio
from pathlib import Path
from typing import List

async def process(arguments: dict) -> List[str]:
    """
    Recursively finds files matching a glob pattern in a specified directory.
    This skill acts as a powerful file searching utility, mirroring the '**' glob syntax.

    Usage:
        .**.py
            -> Lists all files recursively from the current directory.
        .**.py "*.py"
            -> Lists all files ending with .py recursively from the current directory.
        .**.py /path/to/dir "*.txt"
            -> Lists all files ending with .txt recursively from the specified directory.

    Args:
        arguments (dict): A dictionary containing command arguments.
                          Expected keys:
                          - 'args': A list of string arguments parsed from the command line.

    Returns:
        A list of strings, where each string is the path to a matched file, relative
        to the current working directory. On error or if no files are found, returns a
        list containing a single descriptive message string.
    """
    args = arguments.get("args", [])
    search_path_str = "."
    pattern = "*"

    if len(args) == 1:
        # If the single argument is a directory, assume it's the path and use default pattern.
        # Otherwise, assume it's the pattern in the current directory.
        if Path(args[0]).is_dir():
            search_path_str = args[0]
        else:
            pattern = args[0]
    elif len(args) >= 2:
        search_path_str = args[0]
        pattern = " ".join(args[1:])  # Allow patterns with spaces if quoted

    try:
        search_path = Path(search_path_str).resolve()
        if not search_path.is_dir():
            return [f"Error: Search path '{search_path_str}' is not a valid directory."]
    except Exception as e:
        return [f"Error resolving path '{search_path_str}': {e}"]

    def sync_rglob_worker(root: Path, glob_pattern: str) -> List[str]:
        """Synchronous globbing function to be run in a thread."""
        cwd = Path.cwd()
        # Use rglob for recursive searching, which fits the '**' name of the skill.
        return [str(p.relative_to(cwd)) for p in root.rglob(glob_pattern) if p.is_file()]

    try:
        # Run the synchronous, potentially slow file search in a separate thread
        # to avoid blocking the main asyncio event loop.
        file_list = await asyncio.to_thread(sync_rglob_worker, search_path, pattern)
        if not file_list:
            return [f"No files found matching pattern '{pattern}' in '{search_path_str}'."]
        return file_list
    except Exception as e:
        return [f"An error occurred during file search: {e}"]