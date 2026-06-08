# Changelog — Version Duration Tracker

All notable changes to this project, in reverse chronological order.

---

## v1.8 (2026-06-08)

### Added
- **Decimal hours column** — daily summary now shows `🔢 DECIMAL HRS` with each day's total in decimal format (e.g. `3.18` for 03:11). Select and Ctrl+C the cell to paste directly into a spreadsheet.
- **Cell‑only clipboard copy** — Ctrl+C on the table now copies only the selected cell(s) without prepending column headers.

### Changed
- File naming: `VERSIONS_DURATION_TRACKER_v1.8.py` (previously `_V18`).

---

## v1.7 (2026-06-08)

### Fixed
- **`result_label` crash** — `AttributeError` on process because the label was created as a local variable instead of `self.result_label`. ([#1])
- **Explicit date parsing** — dates like `1 Jun, 23:58` and `31 May 16:24` were silently dropped, collapsing multi‑day version lists into 1–2 rows. Added a second regex to extract explicit month/day info and anchor it to the correct calendar date.

### Changed
- File naming: `VERSIONS_DURATION_TRACKER_v1.7.py` (previously `_V17`).

---

## v1.6 (2026-06-08)

### Added
- **Daily summary view** — primary view now shows a table with per‑day totals, day names, first and last version of each day. Days sorted newest‑first.
- **Midnight‑split logic** — intervals that cross midnight are split across the correct calendar days.
- View toggle cycles: Daily → Compact (work blocks) → Expanded (detailed intervals) → back to Daily.
- View‑adaptive CSV/TXT export — exports whatever view is currently displayed.

### Fixed
- Existing V15 features preserved: configurable max‑break filter, slider, 3‑state view toggle, keyboard shortcuts, clipboard, QSettings persistence.

---

## v1.5 (2025-07-27)

### Added
- Major UI overhaul with dark‑theme styling (QSS).
- **Max‑break slider** — configurable threshold (1–1440 min) to filter out pauses/interruptions between saves.
- **Short‑range / Long‑range** toggle for the slider (60 / 1440 min caps).
- **Compact view** — consolidated work blocks grouped by continuous sessions.
- **Expanded view** — every version transition with individual durations and ignored‑interval markers.
- **CSV / TXT export** with column‑width alignment.
- **QSettings persistence** — remembers window geometry, slider value, last export directory.
- **Clipboard** — copy total time or table selection.
- Keyboard shortcuts: Ctrl+P (process), Ctrl+E (export), Ctrl+T (toggle view), Ctrl+Q (quit).

---

## v1.4 (2025-07-04)

### Added
- Refined work‑block detection algorithm.
- Better handling of multi‑line version blocks.

---

## v1.3 (2025-07-04)

### Added
- First version with slider‑based gap filtering.
- Basic dark‑theme styling introduced.

---

## v1.2 (2025-06-30)

### Changed
- Improved parsing reliability for various version‑list formats.
- Minor bug fixes in time calculations.

---

## v1.1 (2025-06-30)

### Added
- Version number display in UI.
- Initial gap‑filtering logic (hard‑coded threshold).

---

## v1.0 (2025-06-29)

### Added
- Milestone release. Core calculation engine stable.
- Support for Blender version lists copied from Google Drive.
- Total active time display.

---

## v0.9 (2025-06-29)

### Changed
- Refined time‑format parsing.

---

## v0.8 (2025-06-29)

### Added
- Early gap detection.

---

## v0.7 (2025-06-29)

### Changed
- UI improvements, window title.

---

## v0.6 (2025-06-29)

### Added
- First table‑based results display.

---

## v0.5 (2025-06-29)

### Changed
- Better error handling for invalid input.

---

## v0.4 (2025-06-29)

### Added
- Copy‑to‑clipboard for total time.

---

## v0.3 (2025-06-29)

### Changed
- Basic time parsing and calculation.

---

## v0.2 (2025-06-29)

### Added
- Initial PySide6 GUI with input field and process button.

---

## v0.1 (2025-06-29)

### Added
- First working prototype. Python script that reads a pasted version list and calculates elapsed time between saves.
