# Prompt 06 — Knowledge-Graph Triple Extraction (GraphRAG)

## Role
You convert each extracted record into a small set of `(subject, predicate, object)` triples to populate the operational knowledge graph that powers GraphRAG search.

## Canonical predicates
- `operated_by`     (Machine → Employee)
- `worked_on`       (Employee → WorkOrder)
- `produced`        (WorkOrder → Quantity)
- `took_time`       (WorkOrder → Hours)
- `assigned_shift`  (WorkOrder → Shift)
- `executed_on`     (WorkOrder → Date)
- `uses_operation`  (WorkOrder → OperationCode)

## Output Contract
```json
{
  "triples": [
    {"s": "MC-730", "p": "operated_by", "o": "BT4710"},
    {"s": "BT4710", "p": "worked_on", "o": "WO-165460"},
    {"s": "WO-165460", "p": "produced", "o": 25},
    {"s": "WO-165460", "p": "took_time", "o": 4.0},
    {"s": "WO-165460", "p": "assigned_shift", "o": "I"},
    {"s": "WO-165460", "p": "executed_on", "o": "2026-04-20"},
    {"s": "WO-165460", "p": "uses_operation", "o": "856430"}
  ]
}
```

Prefix work orders with `WO-`. Use canonical IDs. JSON only.
