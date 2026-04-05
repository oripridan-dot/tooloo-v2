import os
import json
import subprocess
import asyncio
import logging
import urllib.parse
import httpx

logger = logging.getLogger("Tooloo.CoreFS")


WORKSPACE_ROOT = "/tmp/tooloo_sandbox"

def _secure_path(path: str) -> str:
    """Ensures the path stays within the WORKSPACE_ROOT sandbox."""
    if not os.path.exists(WORKSPACE_ROOT):
        os.makedirs(WORKSPACE_ROOT)

    sandbox_abs = os.path.abspath(WORKSPACE_ROOT)

    if os.path.isabs(path):
        # Absolute path: must already be inside the sandbox. No join allowed.
        resolved = os.path.abspath(path)
        if not resolved.startswith(sandbox_abs + os.sep) and resolved != sandbox_abs:
            raise PermissionError(
                f"EACCES: permission denied. Absolute path '{path}' is outside sandbox '{WORKSPACE_ROOT}'"
            )
    else:
        path = os.path.join(WORKSPACE_ROOT, path)

    resolved = os.path.abspath(path)
    if not resolved.startswith(sandbox_abs):
        raise PermissionError(
            f"EACCES: permission denied. Path '{path}' escapes sandbox '{WORKSPACE_ROOT}'"
        )
    return resolved


async def fs_list_files(directory: str = "") -> dict:
    """Lists files in a directory."""
    target_dir = _secure_path(directory)
    if not os.path.exists(target_dir):
        return {"error": f"Directory does not exist: {directory}"}
        
    files = []
    try:
        for root_dir, dirs, filenames in os.walk(target_dir):
            for f in filenames:
                full_path = os.path.join(root_dir, f)
                rel_path = os.path.relpath(full_path, WORKSPACE_ROOT)
                files.append(rel_path)
    except Exception as e:
        return {"error": str(e)}
        
    return {"directory": directory, "sandbox_resolved": target_dir, "files": files, "status": "success"}

async def fs_read_file(path: str) -> dict:
    """Reads the text content of a given file."""
    try:
        target_path = _secure_path(path)
        with open(target_path, "r") as f:
            content = f.read()
        return {"path": path, "sandbox_resolved": target_path, "content": content, "status": "success"}
    except Exception as e:
        return {"error": str(e)}

async def fs_write_report(path: str, content: str) -> dict:
    """Writes the markdown assessment report."""
    try:
        target_path = _secure_path(path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w") as f:
            f.write(content)
        return {"path": path, "sandbox_resolved": target_path, "written": True, "status": "success"}
    except Exception as e:
        return {"error": str(e)}

fs_list_files_schema = {
    "name": "fs_list_files",
    "description": "Lists readable files in a directory within the secure sandbox.",
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Relative directory path to list (default is root sandbox)"}
        }
    }
}

fs_read_file_schema = {
    "name": "fs_read_file",
    "description": "Reads the text content of a given file within the secure sandbox.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to the file to read"}
        },
        "required": ["path"]
    }
}

fs_write_report_schema = {
    "name": "fs_write_report",
    "description": "Writes text content to a specified path within the secure sandbox.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path where the file will be written"},
            "content": {"type": "string", "description": "The text content to write"}
        },
        "required": ["path", "content"]
    }
}

async def sys_subproc_execute(command: str) -> dict:
    """Executes a sandbox bash command cleanly and safely."""
    try:
        target_dir = _secure_path("")
        logger.debug(f"[TOOL:sys_subproc_execute] cmd={command!r}")
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=target_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=25.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            logger.error(f"[TOOL:sys_subproc_execute] TIMEOUT after 25s: {command!r}")
            return {"command": command, "error": "Subprocess timeout after 25s", "status": "timeout"}
        result = {
            "command": command,
            "stdout": stdout.decode("utf-8").strip(),
            "stderr": stderr.decode("utf-8").strip(),
            "exit_code": process.returncode,
            "status": "success" if process.returncode == 0 else "error"
        }
        logger.debug(f"[TOOL:sys_subproc_execute] exit_code={process.returncode}")
        return result
    except Exception as e:
        return {"error": str(e)}

sys_subproc_execute_schema = {
    "name": "sys_subproc_execute",
    "description": "Executes an arbitrary bash command inside the sandbox root directory. Use this to trigger sub-agents or manipulate the workspace.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The exact bash command to execute"}
        },
        "required": ["command"]
    }
}

async def web_search(query: str, max_results: int = 5) -> dict:
    """
    Searches the web using DuckDuckGo Instant Answer API (no API key required).
    Returns structured results with title, URL, and snippet for JIT grounding.
    """
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "TooLoo-Sovereign/1.0"})
            resp.raise_for_status()
            data = resp.json()

        results = []
        # Abstract (best answer)
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", query),
                "url": data.get("AbstractURL", ""),
                "snippet": data["Abstract"][:500]
            })
        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results - len(results)]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic["Text"][:300]
                })

        if not results:
            return {"query": query, "results": [], "note": "No DDG results. Try a more specific query.", "status": "empty"}

        return {"query": query, "results": results[:max_results], "status": "success"}
    except Exception as e:
        return {"query": query, "error": str(e), "status": "error"}


web_search_schema = {
    "name": "web_search",
    "description": "Searches the web using DuckDuckGo. Returns structured results with title, URL, and snippet. Use for grounding DAG decisions in real, trusted external data.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query string"},
            "max_results": {"type": "integer", "description": "Maximum number of results to return (default 5)", "default": 5}
        },
        "required": ["query"]
    }
}


# A manifest to auto-register against the DAG
DEFAULT_TOOLS = {
    "fs_list_files": {
        "handler": fs_list_files,
        "schema": fs_list_files_schema
    },
    "fs_read_file": {
        "handler": fs_read_file,
        "schema": fs_read_file_schema
    },
    "fs_write_report": {
        "handler": fs_write_report,
        "schema": fs_write_report_schema
    },
    "sys_subproc_execute": {
        "handler": sys_subproc_execute,
        "schema": sys_subproc_execute_schema
    },
    "web_search": {
        "handler": web_search,
        "schema": web_search_schema
    }
}
