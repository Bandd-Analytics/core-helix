# Bug & Edge Case Tracker

Each entry links to a detailed report with symptom, root cause, before/after code, and fix verification.

---

## Open

None.

---

## Fixed

| ID | Title | File | Severity | Fixed |
|----|-------|------|----------|-------|
| [BUG-001](BUG-001-MeanRevOscillator-ZeroDivide.md) | MeanRevOscillator zero divide on non-mean-reversion pairs | `V2/indicators/MeanRevOscillator.mq5`, `V2/ea/include/CSignalManager.mqh` | Medium | 2026-04-24 |

---

## Won't Fix / Acknowledged

| ID | Title | Reason |
|----|-------|--------|
| — | `CLogger: Cannot open log file` | Wine environment file path issue; doesn't affect trading or ZMQ |

---

## How to add a new entry

1. Create `BUG-NNN-short-title.md` in this directory using BUG-001 as a template
2. Add a row to the Open table above
3. Move to Fixed when resolved, with the fix date
