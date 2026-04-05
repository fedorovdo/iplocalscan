# iplocalscan

`iplocalscan` is a PySide6 desktop application for administrator-focused local network scanning. The project is Windows-first, keeps SQLite-based local history, and is structured so future Linux desktop support and deeper scan stages can be added without rewriting the UI layer.

## Project Structure

```text
iplocalscan/
|- iplocalscan/
|  |- application/      # Controller, worker thread, and orchestration
|  |- core/             # Domain entities, enums, and networking helpers
|  |- localization/     # English and Russian UI strings
|  |- persistence/      # SQLite schema and repositories
|  |- services/         # Discovery, resolvers, and service abstractions
|  |- ui/               # Main window, history dialog, and table models
|  |- __main__.py
|  |- app.py
|  `- config.py
|- pyproject.toml
`- README.md
```

## Current Features

- Main window with:
  - CIDR network input
  - Scan button
  - Stop button
  - History button
  - Search/filter field
  - Live-updating results table
  - Status bar messages
- Real IPv4 host discovery using parallel `ping` subprocess calls
- Best-effort reverse DNS lookup using `socket.gethostbyaddr`
- Best-effort MAC lookup using the Windows ARP table
- SQLite persistence for scan sessions and results
- Retention of the latest 3 scans
- History dialog that loads real stored results
- English and Russian localization scaffolding
- Structured JSON logging to stdout/stderr

## Setup

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m iplocalscan
```

## Windows Packaging

Use the top-level launcher as the PyInstaller entry point instead of
`iplocalscan/__main__.py`.

```powershell
pip install pyinstaller
pyinstaller --clean --noconfirm iplocalscan.spec
```

The packaged executable will be created at:

```text
dist/iplocalscan/iplocalscan.exe
```

Bundled data files such as `iplocalscan/services/data/oui.json` are included through
the spec file, and runtime resource resolution works in both source and frozen modes.

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m iplocalscan
```

## Discovery Notes

- CIDR input is required for this step, for example `192.168.1.0/24`.
- The current implementation only adds online hosts to the results table.
- Port scanning and service detection are intentionally still stubbed.
- MAC vendor lookup remains an abstraction and currently returns no vendor value when no provider is configured.

## Recommended Next Step

Implement common-port scanning and service detection as a second scan stage that runs only for already discovered online hosts, then stream enrichment updates back into the same table model with `upsert_result`.
