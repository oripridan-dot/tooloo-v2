# 6W_STAMP
# WHO: Buddy (Forge)
# WHAT: Forge a new Python skill file (.py) based on a user's intent. This is a meta-skill that creates other skills.
# WHERE: tooloo_v4_hub/skills/forge_skill.py
# WHY: To enable the system to dynamically create and integrate new tools at runtime, expanding its own capabilities without manual intervention.
# WHEN: 2024-03-01
# HOW: By capturing a filename and a natural language intent, using the hub's internal 'FORGE_SKILL' tool to generate the Python code, writing that code to a new file in the skills directory, and then signaling the tool manager to reload its skill set.

import os
import aiofiles

# This special name is expected to be populated by the tooloo_v4_hub's exec environment.
# It provides access to the hub's internal functions.
# We'll use a placeholder for linting and type-hinting purposes.
try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        __internals__: dict = {}
except ImportError:
    pass

async def process(arguments: dict) -> str:
    """
    Dynamically forges a new Python skill file and loads it into the hub.

    This skill acts as a meta-tool, using the hub's own code generation
    capabilities to create new tools on the fly. It is invoked when the
    user's intent is to create a new skill.

    Args:
        arguments: A dictionary containing:
            - 'filename' (str): The desired filename for the new skill (e.g., 'my_tool.py').
            - 'intent' (str): A detailed description of what the new skill should do.

    Returns:
        A string indicating the result of the operation.
    """
    filename = arguments.get('filename')
    intent = arguments.get('intent')

    if not all([filename, intent]):
        return "Error: 'filename' and 'intent' are required arguments for forging a new skill."

    if not filename.endswith('.py'):
        filename += '.py'

    try:
        hub_root = __internals__['hub_root_path']
        tool_manager = __internals__['tool_manager']
    except (NameError, KeyError):
        return "Error: Could not access hub internals. This skill must run within the tooloo_v4_hub."

    # --- Security Check: Prevent path traversal ---
    skills_dir = os.path.join(hub_root, 'skills')
    # Sanitize filename to only allow a leaf filename, no directory components.
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
         return f"Error: Invalid filename '{filename}'. Filename cannot contain path separators."

    target_path = os.path.join(skills_dir, safe_filename)
    
    # Final check to ensure the resolved path is within the skills directory.
    if not os.path.abspath(target_path).startswith(os.path.abspath(skills_dir)):
        return f"Error: Security violation. Target path '{target_path}' is outside of the allowed skills directory."

    # Construct the detailed prompt for the underlying Sovereign Tool Forge
    forge_mandate = f"FORGE MANDATE: {safe_filename}\nINTENT: FORGE_SKILL\n\n{intent}"

    print(f"Forge Skill: Generating code for '{safe_filename}'...")

    try:
        # Use the internal, privileged 'FORGE_SKILL' tool to generate the code.
        generated_code = await tool_manager.execute_tool(
            'FORGE_SKILL',
            {'prompt': forge_mandate}
        )

        if not generated_code or not isinstance(generated_code, str):
            return "Error: Code generation failed. The forge returned an empty or invalid response."

    except Exception as e:
        return f"Error: An exception occurred while calling the internal forge: {e}"

    # Write the generated code to the new skill file asynchronously
    try:
        async with aiofiles.open(target_path, 'w', encoding='utf-8') as f:
            await f.write(generated_code)
    except IOError as e:
        return f"Error: Failed to write skill file to '{target_path}'. Details: {e}"

    # Signal the hub to reload its skills to include the new one
    try:
        reload_result = await tool_manager.load_skills()
        print(f"Forge Skill: Tool manager reload completed. Result: {reload_result}")
    except Exception as e:
        # This is a non-fatal warning; the file is created but not yet active.
        return f"Warning: Skill '{safe_filename}' was created, but failed to trigger a hub reload. A manual reload may be required. Error: {e}"

    return f"Successfully forged and loaded skill: {safe_filename}"