# iplocalscan

`iplocalscan` is a clean PySide6 desktop scaffold for a future administrator-focused local network scanner. This first step keeps the application runnable while deliberately avoiding real network probing so the UI, persistence, localization, and service boundaries are in place before discovery logic is added.

## Proposed Structure

```text
iplocalscan/
├── iplocalscan/
│   ├── application/      # UI-facing controller and scan orchestration
│   ├── core/             # Domain entities, enums, and network helpers
│   ├── localization/     # English/Russian translation layer
│   ├── persistence/      # SQLite schema, connection manager, repositories
│   ├── services/         # Scanner contracts and stub implementations
│   ├── ui/               # Main window, history dialog, Qt models
│   ├── __main__.py       # python -m iplocalscan entry point
│   ├── app.py            # Composition root and QApplication bootstrap
│   └── config.py         # Cross-platform app paths and app constants
├── pyproject.toml
└── README.md
```

## What Is Included

- Runnable PySide6 desktop application skeleton
- Main window with network input, scan/stop/history actions, filter input, results table, and status bar
- `QAbstractTableModel`-based results model ready for sorting and live row updates
- Shared results model design for both current scan results and historical scan previews
- SQLite database initialization with `scans` and `scan_results` tables
- Repository layer prepared for keeping the latest 3 scans
- English and Russian localization scaffolding
- Service abstraction and stub implementations for:
  - host discovery
  - hostname resolution
  - port scanning
  - service detection
  - MAC vendor lookup

## Setup

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m iplocalscan
```

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m iplocalscan
```

## Current Behavior

- The Scan button validates and normalizes an IPv4 network range.
- A scan session is written to SQLite and trimmed to the latest 3 sessions.
- Stub services run without performing any real network activity.
- The results table stays empty until real discovery is added.
- The History button opens a dialog backed by the same results model class used in the main window.

## Notes

- SQLite data is stored in the user application data directory:
  - Windows: `%LOCALAPPDATA%\\iplocalscan\\iplocalscan.db`
  - Linux: `~/.local/share/iplocalscan/iplocalscan.db`
- The architecture is intentionally split so scanning can later move into background workers without rewriting the UI layer.

## Recommended Next Step

Implement real host discovery behind the existing `HostDiscoveryService` contract, then run it from a background worker owned by the controller so the Qt event loop remains responsive while incremental results are pushed into the table model with `upsert_result`.
