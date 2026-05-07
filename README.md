# iplocalscan

`iplocalscan` is a Windows-first desktop application for administrator-focused local network scanning. It provides fast local subnet discovery, practical host and service visibility, scan-to-scan change tracking, and lightweight local history storage in a clean PySide6 interface backed by SQLite.

## Download

Download the latest Windows release from:

[Latest Release](https://github.com/fedorovdo/iplocalscan/releases/latest)

Current public release: `v0.4.0`

## Features

- CIDR-based local network scanning
- Host discovery for online devices
- TCP port scanning with basic service detection
- Scan diffing: `New`, `Missing`, `Changed`, `Unchanged`
- Local scan history stored in SQLite
- English and Russian localization
- About dialog with system and version information
- CSV export from the main results view
- CSV export from the history view
- Excel-friendly CSV export for localized Windows systems

## Screenshots

Screenshots will be added to the repository as the UI is finalized.

## How to Use

1. Start `iplocalscan`.
2. Enter a CIDR range such as `192.168.1.0/24`.
3. Run a scan and watch results appear progressively.
4. Sort or filter the table to focus on the hosts you need.
5. Review changes between scans and open scan history when needed.
6. Export the current view or a historical view to CSV for reporting.

## Build From Source

### Run in development mode

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
python -m iplocalscan
```

You can also launch the app with:

```powershell
python run_app.py
```

### Build a Windows executable with PyInstaller

```powershell
.\.venv\Scripts\pyinstaller --clean --noconfirm IPLocalScan.spec
```

Build output:

```text
dist\iplocalscan\iplocalscan.exe
```

### Build a Windows installer with Inno Setup

```powershell
ISCC installer\IPLocalScan.iss
```

## Project Structure

```text
iplocalscan/
|- iplocalscan/
|  |- application/    # Controller, worker thread, orchestration
|  |- core/           # Domain models, enums, helpers
|  |- localization/   # EN/RU strings and localization manager
|  |- persistence/    # SQLite layer and repositories
|  |- services/       # Discovery, resolution, scanning services
|  |- ui/             # Main window, dialogs, table models
|  |- app.py
|  `- version.py
|- installer/         # Inno Setup packaging
|- IPLocalScan.spec   # PyInstaller build spec
|- pyproject.toml
|- run_app.py
`- README.md
```

## Roadmap

- richer service identification and banner grabbing
- configurable scan profiles
- improved device identification and vendor coverage
- installer and release polish for wider deployment
- future Linux desktop support
