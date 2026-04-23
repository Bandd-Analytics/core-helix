"""BRDG-03 Python listener.

Binds a SUB socket to tcp://*:5599, subscribes to all topics, and prints
the first multipart message received. Exits with code 0 on receipt, code 1
on timeout (default 30 seconds).

Usage:
    python -m bridge.spike.listen_spike [--port 5599] [--timeout 30]

Run this BEFORE running brdg03_spike.mq5 on the MT5 terminal.
Output on PASS:
    [SPIKE] Listening on tcp://*:5599 (timeout=30s)
    [SPIKE] Received: topic=b'SPIKE' payload=b'BRDG03_SPIKE_OK'
    [SPIKE] PASS — BRDG-03 gate cleared
Output on FAIL:
    [SPIKE] Listening on tcp://*:5599 (timeout=30s)
    [SPIKE] TIMEOUT — no message received within 30s
    [SPIKE] FAIL — check MT5 Experts log for DLL errors (126, 998)
"""

from __future__ import annotations

import argparse
import sys

import zmq


def main() -> int:
    parser = argparse.ArgumentParser(description="BRDG-03 spike listener")
    parser.add_argument("--port", type=int, default=5599, help="Bind port (default 5599)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds (default 30)")
    args = parser.parse_args()

    ctx = zmq.Context()
    sock = ctx.socket(zmq.SUB)
    sock.bind(f"tcp://*:{args.port}")
    sock.setsockopt(zmq.SUBSCRIBE, b"")

    print(f"[SPIKE] Listening on tcp://*:{args.port} (timeout={args.timeout}s)", flush=True)

    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    events = dict(poller.poll(timeout=args.timeout * 1000))

    if sock not in events:
        print(f"[SPIKE] TIMEOUT — no message received within {args.timeout}s", flush=True)
        print("[SPIKE] FAIL — check MT5 Experts log for DLL errors (126, 998)", flush=True)
        sock.close()
        ctx.term()
        return 1

    frames = sock.recv_multipart()
    if len(frames) < 2:
        print(f"[SPIKE] Received unexpected frame count: {len(frames)} (expected 2)", flush=True)
        sock.close()
        ctx.term()
        return 1

    topic, payload = frames[0], frames[1]
    print(f"[SPIKE] Received: topic={topic!r} payload={payload!r}", flush=True)

    if payload == b"BRDG03_SPIKE_OK":
        print("[SPIKE] PASS — BRDG-03 gate cleared", flush=True)
        result = 0
    else:
        print(f"[SPIKE] FAIL — unexpected payload {payload!r}", flush=True)
        result = 1

    sock.close()
    ctx.term()
    return result


if __name__ == "__main__":
    sys.exit(main())
