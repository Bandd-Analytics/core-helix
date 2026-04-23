# BRDG-03 Gate Result

**Requirement:** BRDG-03 — mql-zmq DLL compatibility confirmed on IC Markets MT5 terminal
**Gate type:** go/no-go (pass unblocks Phase 10; fail requires fallback IPC choice)

---

## Environment

| Property | Value |
|----------|-------|
| Date run | TBD (fill in when spike is executed) |
| Platform | TBD (Windows native / Ubuntu + Wine) |
| OS version | TBD (e.g. Windows 11 23H2 / Ubuntu 24.04) |
| Wine version | TBD (N/A on Windows, e.g. `wine-11.7 (Staging)` on Ubuntu) |
| MT5 Build | TBD (from `TerminalInfoInteger(TERMINAL_BUILD)` in MT5 journal) |
| MT5 data folder | TBD (full path to the MQL5 parent directory) |
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

The spike runs identically on native Windows MT5 and Ubuntu MT5 under Wine — the MQL5 script is binary-compatible and the Python listener binds to a TCP socket the MT5 process can reach on `127.0.0.1`.

### Common steps (both platforms)

1. Download mql-zmq from https://github.com/dingmaotu/mql-zmq (fallback: https://github.com/coke5151/mql5-zmq)
2. Identify the MT5 data folder (File -> Open Data Folder, or read path from journal on first launch)
3. Copy DLLs to `<MT5_DATA>/MQL5/Libraries/`:
   - `libzmq.dll`
   - `libsodium.dll`
4. Copy header trees to `<MT5_DATA>/MQL5/Include/`:
   - `Zmq/`
   - `Mql/`
5. MT5: Tools -> Options -> Expert Advisors -> check "Allow DLL imports" -> OK -> restart MT5
6. Copy `brdg03_spike.mq5` to `<MT5_DATA>/MQL5/Scripts/`, compile in MetaEditor (F7, expect 0 errors)
7. Start the Python listener on the host:
   ```
   cd /home/user/Desktop/BA.ORG/Bandd-Analytics/helix/V2 && python -m bridge.spike.listen_spike --port 5599 --timeout 30
   ```
8. In MT5: Navigator (Ctrl+N) -> Scripts -> double-click `brdg03_spike`, keep defaults (`127.0.0.1`, port `5599`), click OK
9. Observe MT5 Experts tab for `SPIKE PASS: libzmq.dll loaded, test message sent, no crash` and Python terminal for `[SPIKE] PASS — BRDG-03 gate cleared`
10. Fill the Environment table and Outcome section above with actual values

### Platform-specific paths

**Windows native:**
- MT5 data folder: typically `%APPDATA%\MetaQuotes\Terminal\<hash>\MQL5\` (or the install dir if MT5 runs in portable mode — check for a `portable.txt` marker next to `terminal64.exe`)
- VC++ 2015 Redistributable (x64): install from Microsoft if `libzmq.dll` fails to load with error 126

**Ubuntu + Wine:**
- Default MT5 data folder (portable mode): `~/.mt5/drive_c/Program Files/MetaTrader 5/MQL5/`
- Default MT5 data folder (non-portable): `~/.mt5/drive_c/users/<user>/AppData/Roaming/MetaQuotes/Terminal/<hash>/MQL5/`
- VC++ runtime: install inside the Wine prefix with `WINEPREFIX=~/.mt5 winetricks vcrun2015` (or `vcrun2019` for newer) — MT5's installer usually pulls this in automatically; if not, `vcruntime140.dll` and `vcruntime140_1.dll` must be present in `~/.mt5/drive_c/windows/system32/`
- Wine prefix: set `WINEPREFIX=~/.mt5` in the same shell that launches `wine .../terminal64.exe`
- Networking: Wine uses the host network stack, so `127.0.0.1:5599` from inside MT5 reaches the Python listener on the Ubuntu host with no additional config

### Notes

- The MQL5 spike script, Python listener, and wire protocol are identical across platforms. Only the filesystem path to the MT5 data folder differs.
- If the spike passes on one platform, it's strong evidence the same binary will load on the other — but the gate is officially recorded per platform in the table above. Re-run on the second OS before Phase 10 if you plan to deploy there.
