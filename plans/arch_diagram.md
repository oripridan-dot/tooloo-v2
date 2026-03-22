# TooLoo V2 Architecture

```mermaid
graph LR
    router --> jit_booster
    router --> executor
    router --> graph
    jit_booster --> model_garden
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
    n_stroke --> branch_executor
    n_stroke --> mandate_executor
    supervisor --> conversation
    supervisor --> config
    supervisor --> branch_executor
    supervisor --> mandate_executor
    conversation --> branch_executor
    conversation --> mandate_executor
    config --> model_garden
    config --> vector_store
    config --> daemon
    psyche_bank --> vector_store
    psyche_bank --> daemon
    tribunal
```
