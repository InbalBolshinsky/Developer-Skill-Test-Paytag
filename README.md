# Developer-Skill-Test-Paytag

A hotkey-driven fast-checkout client for PayTag self-checkout machines: scans RFID-tagged items during a checkout session and neutralizes their security tags on close, persisting business and technical data to MongoDB.

📋 **[See PLAN.md](PLAN.md) for the full written design plan** — endpoints, hotkey architecture, MongoDB schema, error handling, terminal output, and alternatives considered.

## Prerequisites

- Python 3.x
- Docker (to run the provided PayTag simulator)
- A local MongoDB instance (native install or Docker)

## Running the PayTag simulator

```bash
docker load -i paytag-dev-test-20260827/paytag-demo-api.tar.gz
docker run -d -p 8765:5000 paytag-demo-api:latest
```

Note: the container listens internally on port `5000` (confirmed from its image config), so the `-p 8765:5000` mapping is required to make it reachable at `localhost:8765`, as the assignment expects — the two ports are *not* the same.

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

All tunables (hotkeys, poll interval, MongoDB URI, retry counts, etc.) load from a YAML config file rather than being hardcoded — see PLAN.md for the full design.

## Running the client

*Implementation in progress — this section will be filled in with the exact install/run steps once the client is built.*

## Status

Design and written plan complete (see `PLAN.md`); implementation in progress.
