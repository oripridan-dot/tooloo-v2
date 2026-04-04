---
name: Claude Built-in Server Tools
description: Direct ingestion rules for how Buddy should route calls to Anthropic's server-managed tools.
---
# Claude Built-in Server Tools Skill

Claude exposes natively-hosted, Anthropic-managed Server Tools that do not require application-side execution code. The major three are Code Execution, Text Editor, and Web Search.

## Tool Routing Rules

### 1. Code Execution (`code_execution_20250825` & `code_execution_20260120`)
When you need Claude to run isolated code (Python or bash) without mutating the local Tooloo V4 system environment, invoke Code Execution.
- Include the tool type `code_execution_20250825`.
- **Dynamic Filtering**: If you need to search the web for heavy data, pair it with `web_search_20260209`. Claude will automatically use Code Execution to trim the search HTML locally on their servers before sending the finalized text to the context window, drastically reducing token bloat.

### 2. Text Editor (`text_editor_20250728`)
When working with files in the codebase, you can specify this tool if you prefer Claude to format the edits using Anthropic's native `str_replace` or `insert` block patterns instead of generic JSON.
- Note: Buddy still needs to provide the execution handling on Tooloo's side for the physical file write.

### 3. Web Search (`web_search_20260209`)
Use this for live internet data. Always pair with the Dynamic Filtering Code Execution tool above to respect Rule 7 (Efficiency). You will receive citations under the `cited_text` payload.
