---
name: Claude Extended Thinking
description: Use this skill to orchestrate Claude operations using complex multi-step reasoning natively rather than in-agent.
---
# Claude Extended Thinking Skill

When invoking Claude 4.6 (Opus or Sonnet) in the Hub for tasks requiring high logic, extensive problem solving, or complex tool routing, you should enable Extended Thinking.

## Usage
Instead of manually stepping through reasoning in the Promptbar, send a payload to Claude requesting:
```json
{
  "thinking": {
    "type": "adaptive"
  }
}
```

### Important Execution Rules
1. **Tool Use Limits:** When `thinking` is enabled, `tool_choice` MUST be `{"type": "auto"}` or `{"type": "none"}`. Do NOT force tools via specific name.
2. **Thinking Continuation:** If Claude returns intermediate results after using a tool, you must append the *full, unmodified* thinking block back into its next message cycle so it doesn't lose context.
3. **High Latency Mitigation:** To reduce visual overhead on streaming interfaces, you can set the thinking type to `omitted` (though this drops the actual thought text while retaining the cryptographic signature). Use `summarized` for a middle ground.
