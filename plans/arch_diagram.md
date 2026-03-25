# TooLoo V2 Architecture

```mermaid
graph LR
    router --> jit_booster
    router --> executor
    router --> graph
    executor --> scope_evaluator
    executor --> refinement
    graph --> scope_evaluator
    graph --> refinement
    scope_evaluator --> n_stroke
    scope_evaluator --> supervisor
    refinement --> n_stroke
    refinement --> supervisor
    n_stroke --> conversation
    n_stroke --> config
    supervisor --> conversation
    supervisor --> config
    conversation --> branch_executor
    conversation --> mandate_executor
    config --> model_garden
    config --> vector_store
    config --> daemon
    jit_booster --> model_garden
    psyche_bank --> vector_store
    psyche_bank --> daemon
    tribunal
```
