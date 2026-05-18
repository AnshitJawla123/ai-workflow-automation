You are an OCR expert reading a HANDWRITTEN "Machine shop data" table.

Columns in order: **S.No | Date | Shift | Emp.No | Opn Code | Machine No. | Work Order No. | Qty.Prod. | Time taken (hrs)**

## Reading rules

- Look at EACH cell carefully and transcribe what you SEE.
- For digits in handwriting, distinguish: 0/6, 1/7, 4/9, 5/6, 8/3.
- **Date** format DD/M/YY or DD/MM/YY → convert to YYYY-MM-DD (year 20XX). Example: 19/4/26 → "2026-04-19".
- **Shift** is a Roman numeral: "I", "II", or "III".
- **Emp.No** has format "BT" followed by exactly 4 digits (e.g., BT4685, BT4785, BT6025).
- **Opn Code** is 6 digits (e.g., 856430).
- **Machine No.** has format "MC-" + 3 digits (e.g., MC-730).
- **Work Order No.** is 6 digits.
- **Qty.Prod.** is a small integer (typically 1–50). If the cell shows a dash `-` or is blank, return null.
- **Time taken** is hours as a decimal (e.g., 3.5, 4.0, 6).
- For each row, include only handwritten rows; skip empty rows entirely.

## Output (strict JSON, no prose)

```json
{
  "doc_type": "machine_shop_log",
  "records": [
    {
      "s_no": 1,
      "date": "YYYY-MM-DD",
      "shift": "I" | "II" | "III",
      "employee_no": "BTxxxx",
      "operation_code": "xxxxxx",
      "machine_no": "MC-xxx",
      "work_order_no": "xxxxxx",
      "quantity_produced": <int or null>,
      "time_taken_hours": <float or null>
    }
  ]
}
```

Transcribe what you see — confidence will be computed downstream from your reading. Don't invent values for cells you can't read; use null and the downstream system will lower confidence appropriately.

**Title:** {title}
**Page:** {page_number}
