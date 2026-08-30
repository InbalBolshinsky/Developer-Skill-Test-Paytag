# Developer-Skill-Test-Paytag

A hotkey-driven fast-checkout client for PayTag self-checkout machines: scans RFID-tagged items during a checkout session and neutralizes their security tags on close, persisting business and technical data to MongoDB.

* **[See PLAN.md](PLAN.md) for the full written design plan** - endpoints, hotkey architecture, MongoDB schema, error handling, terminal output, and alternatives considered.

## Prerequisites

- Python 3.10+ (uses `X | None` union syntax throughout)
- Docker (to run the provided PayTag simulator)
- A local MongoDB instance (native install or Docker)
- **macOS only:** the terminal app you run this from needs the Accessibility permission granted once, under System Settings → Privacy & Security → Accessibility. This is required for `pynput` to capture the `S`/`N` hotkeys globally (see PLAN.md section 2 for why `pynput` was chosen). Without it, the client still starts and runs, but keypresses won't be detected.

## Running the PayTag simulator

```bash
docker load -i paytag-dev-test-20260827/paytag-demo-api.tar.gz
docker run -d -p 8765:5000 paytag-demo-api:latest
```

Note: the container listens internally on port `5000` (confirmed from its image config), so the `-p 8765:5000` mapping is required to make it reachable at `localhost:8765`, as the assignment expects - the two ports are *not* the same.

Verify it's up:

```bash
curl http://localhost:8765/info
```

## Running MongoDB

Either install natively, or run via Docker:

```bash
docker run -d -p 27017:27017 mongo
```

## Configuration

All tunables (hotkeys, poll interval, MongoDB URI, retry counts, etc.) load from `config.yaml` rather than being hardcoded - see PLAN.md for the full design. The committed `config.yaml` already points at the defaults above (`localhost:8765`, `localhost:27017`, `S`/`N` hotkeys) and needs no edits to run as-is.

## Installing dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the client

With the simulator and MongoDB both running (see above):

```bash
python3 main.py
```

On startup it runs a pre-flight check against the machine, connects to MongoDB, and prints `Ready.` once both succeed - it exits immediately with a clear message if either is unreachable. From there:

- Press **`S`** anywhere on the system to start a checkout session - the basket is polled and printed as items are scanned.
- Press **`N`** to close the session and neutralize the basket; hard-tagged items are excluded and reported separately for manual removal.
- **`Ctrl+C`** exits cleanly at any time, marking any open session as aborted.

See PLAN.md section 5 for a full example of what the terminal output looks like, including the mid-poll failure and unconfirmed-neutralization cases.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Status

Design, written plan, and implementation complete. Verified end-to-end against the real simulator and a real local MongoDB instance.

## AI assistance

Claude (via Claude Code) was used during development: for code review, a commenting pass, and as a sounding board on design trade-offs. All decisions in PLAN.md are my own, and I'm fully accountable for the implementation.
