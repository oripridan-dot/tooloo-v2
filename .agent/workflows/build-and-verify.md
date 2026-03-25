---
description: How to build features for the TooLoo AI Design Studio — grounded, real, iterative.
---

# Build & Verify — Grounded Development Workflow

## Core Rules

1. **No mocks. Ever.** Test against the live running server. If the server isn't running, start it first.
2. **Small vertical slices.** Build one thing, verify it works end-to-end, then move on.
3. **Browser is the source of truth.** Open the real URL, interact with the real UI, show real results.
4. **Fail fast, fix fast.** If something breaks, show the error and fix it immediately — don't skip to the next feature.
5. **User drives direction.** Never assume the next step. Ask or wait.

## Build Cycle

```
1. User says what to build
2. Write the smallest change that moves toward it
3. Hit the live endpoint / open the real UI in browser
4. Show the REAL output (screenshot, terminal log, or browser recording)
5. If broken → fix → re-verify
6. If working → ask user for feedback before moving on
```

## Verification Checklist (every change)

// turbo
- [ ] Server is running (`lsof -i :8002`)
// turbo
- [ ] Endpoint responds (`curl http://localhost:8002/...`)
- [ ] Browser shows correct behavior (use browser_subagent on the REAL URL, not a mock)
- [ ] User has seen real output before marking complete

## Anti-Patterns (DO NOT DO)

- ❌ Creating `demo_*.html` files with hardcoded responses
- ❌ Writing 4+ files in one shot without testing any of them
- ❌ Saying "done" without showing real verified output
- ❌ Using placeholder images or stock Unsplash URLs as "proof"
- ❌ Skipping broken things to show pretty demos
