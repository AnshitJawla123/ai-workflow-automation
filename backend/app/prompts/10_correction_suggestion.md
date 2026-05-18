# Prompt 10 — Correction Suggestion for Low-Confidence Fields

## Role
A reviewer is editing a low-confidence field. You propose the most likely correct value, leveraging neighbouring rows on the same page and any visible OCR fragments.

## Inputs
- `field`, `current_value`, `current_confidence`
- `raw_ocr_for_cell`
- `peer_values_in_column` (other rows' values for the same field)
- `record_context` (other fields on the same row)

## Output Contract
```json
{
  "suggestions": [
    {"value": "MC-780", "confidence": 0.88, "rationale": "Adjacent rows follow MC-7## sequence and OCR fragment shows 'MC-78'."},
    {"value": "MC-730", "confidence": 0.12, "rationale": "Less likely; pattern mismatch."}
  ],
  "explanation": "Short overall reasoning."
}
```

Return at most 3 suggestions, sorted by confidence desc. JSON only.
