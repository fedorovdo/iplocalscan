# iplocalscan
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