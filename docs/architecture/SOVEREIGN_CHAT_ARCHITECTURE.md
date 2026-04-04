# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: SOVEREIGN_CHAT_ARCHITECTURE.MD | Version: 2.0.0
# WHERE: docs/architecture/SOVEREIGN_CHAT_ARCHITECTURE.md
# WHY: Rule 7 Definition & Enforcement to remediate the CHAT phase core integrity failure.
# HOW: Formalized boundaries, interfaces, and constraints.
# ==========================================================

# The Sovereign CHAT Core Architecture v2

## 1. The Core Mandate

The CHAT phase is the **Sovereign Core** mapping directly to the "Principal Architect <-> System" boundary. It must be physically decoupled (Rule 13), mathematically pure, and explicitly constrained (Rule 1).

## 2. Component Decoupling (Rule 13)

To resolve the entanglement and "integrity black hole," the architecture is strictly segmented into three zones:

### Zone 1: Chat Logic Spoke (Transport Layer)
**Owner**: `tooloo_v4_hub/organs/sovereign_chat/chat_logic.py`
**Responsibility**: WebSocket transport, bi-directional telemetry broadcast, user connection lifecycle.
**Constraint**: Must contain **ZERO** cognitive reasoning. Must interact with Zone 2 strictly via the `SovereignChatEngine` API. Must interact with Zone 3 strictly via the `IChatRepository` interface.

### Zone 2: Cognitive Kernel (Reasoning Layer)
**Owner**: `tooloo_v4_hub/kernel/cognitive/chat_engine.py`
**Responsibility**: Parallel Triangulation, JIT Context Injection, Consensus Validation, Response Generation.
**Constraint**: 
- Must contain **ZERO** persistence knowledge (no imports from `organs.memory_organ.sqlite_persistence`). 
- Must utilize constructor-injected `IChatRepository` for state operations. 
- Must enforce **VETO Blockade**: If `_perform_consensus_check` triggers a `[VETO]`, inference halts and throws a `SovereignConstitutionException`.

### Zone 3: Persistence Organ (State Layer)
**Owner**: `tooloo_v4_hub/organs/memory_organ/*_persistence.py`
**Responsibility**: Storing `SovereignMessage` objects physically.
**Contract**: Must implement `IChatRepository` defining `store_message(msg)` and `get_history()`.

## 3. The Contract Boundary (`IChatRepository`)

```python
from abc import ABC, abstractmethod
from typing import List
from tooloo_v4_hub.kernel.cognitive.protocols import SovereignMessage

class IChatRepository(ABC):
    @abstractmethod
    def store_message(self, message: SovereignMessage) -> None:
        """Persists a SovereignMessage to the physical layer."""
        pass
        
    @abstractmethod
    def get_history(self, limit: int = 100) -> List[SovereignMessage]:
        """Retrieves history up to limit."""
        pass
```

## 4. Rule 11 (Anti-Band-Aid) Enforcement Policy

- Broad `except Exception:` catches without re-raising or formal mitigation pipelines are statically forbidden within Zone 1 and 2.
- Known suppressed areas (e.g. `except: pass` around `_broadcast_thinking`) will be upgraded to explicit logging + typed non-critical exception absorption, or removed entirely and allowed to structurally fail.

## 5. Deployment Validation (Rule 18)

- **Target**: Cloud Run `me-west1` (`tooloo-v4-hub`)
- **Latency SLAs**: 
  - Cognitive Sync (WebSocket Acknowledgement): < 45ms 
  - Cognitive Resolution (Time-To-First-Token): < 450ms
- **Memory Tier**: The `SQLite` memory is intended *only* for the `cli/local` execution. The Cloud representation must securely boot `FirestoreRepository` or `GCSRepository` based on environment variables, preserving node synchrony.
