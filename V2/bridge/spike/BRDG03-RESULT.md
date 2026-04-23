# BRDG-03 Gate Result

**Requirement:** BRDG-03 — mql-zmq DLL compatibility confirmed on IC Markets MT5 terminal
**Gate type:** go/no-go (pass unblocks Phase 10; fail requires fallback IPC choice)

---

## Environment

| Property | Value |
|----------|-------|
| Date run | TBD (fill in when spike is executed) |
| MT5 Build | TBD (from `TerminalInfoInteger(TERMINAL_BUILD)` in MT5 journal) |
| IC Markets account type | TBD (Demo / Raw Spread / Standard) |
| Account login (last 4 digits) | TBD |
| mql-zmq fork used | TBD (dingmaotu or coke5151) |
| libzmq.dll version | TBD |
| libsodium.dll version | TBD |
| Visual C++ runtime | TBD (installed / not installed) |
| "Allow DLL imports" enabled | TBD (yes / no) |

---

## Outcome

**Outcome:** PENDING (set to PASS or FAIL after spike runs)

### If PASS
- MT5 journal line observed: `SPIKE PASS: libzmq.dll loaded, test message sent, no crash`
- Python listener line observed: `[SPIKE] PASS — BRDG-03 gate cleared`
- **Next action:** Proceed to Plan 04 (EA bar-close publisher using same DLL)

### If FAIL
- MT5 journal error code: TBD (e.g. error 126, error 998)
- MT5 journal message: TBD
- Fallback path assessment (from 06-RESEARCH.md Open Question 1):
  - [ ] Try coke5151/mql5-zmq fork (if dingmaotu compilation failed)
  - [ ] Try MetaTrader5 pip package (Windows-only, breaks D-02 cross-platform goal)
  - [ ] Try file-based IPC (breaks sub-10ms latency target)
- **Next action:** Update STATE.md blockers; open decision record for fallback IPC choice

---

## Reproducibility

To re-run the spike:
1. Start Python listener: `cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2 && python -m bridge.spike.listen_spike --port 5599 --timeout 30`
2. On the IC Markets MT5 terminal: Navigator -> Scripts -> drag `brdg03_spike.mq5` onto any chart
3. Inspect MT5 Experts/Journal tab for `SPIKE PASS` or `SPIKE FAIL` lines
4. Inspect Python terminal for `[SPIKE] PASS` or `[SPIKE] FAIL` lines
5. Update the "Outcome" section above with actual values
