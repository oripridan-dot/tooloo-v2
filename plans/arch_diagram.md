# TooLoo V2 Architecture

```mermaid
graph LR
  router --> tribunal
  router --> jit_booster
  router --> psyche_bank
  jit_booster --> executor
  jit_booster --> graph
  executor --> scope_evaluator
  executor --> refinement
  graph --> scope_evaluator
  graph --> refinement
  tribunal --> psyche_bank
```
