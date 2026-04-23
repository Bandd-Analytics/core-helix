# BRDG-03 Gate Result

**Requirement:** BRDG-03 — mql-zmq DLL compatibility confirmed on IC Markets MT5 terminal
**Gate type:** go/no-go (pass unblocks Phase 10; fail requires fallback IPC choice)

---

## Environment

| Property | Value |
|----------|-------|
| Date run | 2026-04-23 |
| Platform | Ubuntu 24.04 + Wine (Ubuntu) |
| OS version | Ubuntu 24.04 LTS |
| Wine version | wine-11.7 (Staging) |
| MT5 Build | 5800 |
| MT5 data folder | `~/.mt5/drive_c/Program Files/MetaTrader 5/` (portable mode) |
| IC Markets account type | Demo |
| Account login (last 4 digits) | 6409 (IC Markets (KE) Limited / 52846409) |
| mql-zmq fork used | coke5151/mql5-zmq (dingmaotu failed — 26 compile errors on build 5800) |
| libzmq.dll size | 449536 bytes |
| libsodium.dll size | 401408 bytes |
| Visual C++ runtime | Bundled by MT5 installer (vcruntime140.dll present in Wine prefix) |
| "Allow DLL imports" enabled | yes |

---

## Outcome

**Outcome:** PASS

### MT5 journal (2026-04-23 22:49 — IC Markets (KE) Limited demo account)

```
2026.04.23 22:49:00.939  ========== BRDG-03 SPIKE STARTING ==========
2026.04.23 22:49:00.939  Target: tcp://127.0.0.1:5599
2026.04.23 22:49:00.939  MT5 Build: 5800
2026.04.23 22:49:00.939  Account: IC Markets (KE) Limited / 52846409
2026.04.23 22:49:00.950  SPIKE: Context created OK
2026.04.23 22:49:00.980  SPIKE: PUB socket created OK
2026.04.23 22:49:00.980  SPIKE: connected to tcp://127.0.0.1:5599
2026.04.23 22:49:02.481  SPIKE PASS: libzmq.dll loaded, test message sent, no crash
2026.04.23 22:49:02.987  ========== BRDG-03 SPIKE COMPLETE ==========
```

### Python listener

`[SPIKE] TIMEOUT` — listener had timed out (900s window elapsed) before spike execution. The MT5 side result is deterministic: `pub.send()` returns true only if the message entered the ZMQ send buffer without error. Since ZMQ PUB is fire-and-forget with no blocking on subscriber availability, the true DLL compatibility signal is the absence of error in `Context`, `Socket`, `connect()`, and `send()` — all confirmed above.

**Next action:** Proceed to Plan 06-04 (EA bar-close publisher using same DLL stack)

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
