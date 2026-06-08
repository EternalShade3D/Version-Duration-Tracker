import sys
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QStatusBar, QFileDialog, QHeaderView, QMessageBox, QFrame,
    QSplitter, QSlider, QLineEdit
)
from PySide6.QtCore import Qt, QSettings, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QFont, QClipboard, QKeySequence, QShortcut, QColor, QIntValidator
import re

# ==================== CONSTANTS ====================
COLORS = {
    "bg": "#121212",
    "header_bg": "#1a1a1a",
    "text": "#e0e0e0",
    "accent": "#2979ff",
    "highlight": "#ffd600",
    "accent_dark": "#1a52cc",
    "button": "#2a2a2a",
    "button_hover": "#333333",
    "error": "#ff4c4c",
    "table_header": "#1f1f1f",
    "table_row_even": "#191919",
    "table_row_odd": "#151515",
    "font_family": "Segoe UI, sans-serif",
    "font_size_small": 9,
    "font_size_medium": 11,
    "font_size_large": 13,
    "font_size_total": 14,
    "font_size_subtitle": 14,
    "font_size_title": 24,
    "border_radius_sm": "6px",
    "border_radius_md": "10px",
    "border_radius_lg": "14px",
    "border_width_thin": "1px",
    "border_width_thick": "2px",
    "padding_sm": "6px",
    "padding_md": "12px",
    "padding_lg": "20px",
    "margin_sm": "6px",
    "margin_md": "12px",
}

DEFAULT_MAX_BREAK_MINUTES = 10
SHORT_RANGE_MAX = 60
MAX_BREAK_SLIDER_RANGE = 1440

STRINGS = {
    "app_title": "▶ VERSION DURATION TRACKER V16",
    "app_subtitle": "🧮 BLENDER VERSION TIME CALCULATOR",
    "label_input": "📥 PASTE YOUR VERSION LIST:",

    "btn_process": "⚙️ PROCESS",
    "btn_export": "📤 EXPORT",
    "btn_copy": "📋 COPY TOTAL",
    "btn_toggle_view": "🔄 TOGGLE VIEW",
    "btn_exit": "🚪 EXIT",
    "btn_toggle_range_short": "⏱ SHORT RANGE",
    "btn_toggle_range_long": "⏱ LONG RANGE",

    "label_result": "📊 DAILY SUMMARY",
    "msg_invalid": "❗ INVALID OR MISSING DATA FOUND",
    "msg_success": "✅ DONE! EVERYTHING PROCESSED",
    "msg_copied": "📋 TOTAL TIME COPIED!",

    "export_csv": "📄 CSV FILES (*.CSV)",
    "export_txt": "📄 TEXT FILES (*.TXT)",

    "status_ready": "🟢 READY",
    "status_processing": "⏳ WORKING",

    "col_date": "📅 DATE",
    "col_day": "📆 DAY",
    "col_total_hours": "⏱ TOTAL HOURS",
    "col_first_version": "🟩 FIRST VERSION",
    "col_last_version": "🏁 LAST VERSION",
    "col_version": "🔢 VERSION",
    "col_time": "⏱ TIME",
    "col_version_start": "🟩 START\nVERSION",
    "col_start_time": "🕒 START\nTIME",
    "col_version_end": "🏁 END\nVERSION",
    "col_end_time": "🕓 END\nTIME",
    "col_duration": "🕘 DURATION",

    "total_label": "⏱ TOTAL ACTIVE TIME:",
    "selected_duration_label": "∑ SELECTED DURATION:",
    "history_file": "version_tracker_history.json",
    "max_break_label": "⏸ MAX BREAK (MINUTES):",
    "daily_view": "📅 DAILY VIEW",
    "compact_view": "📦 COMPACT VIEW",
    "expanded_view": "📂 EXPANDED VIEW",

    "tt_input_text": "📥 Paste your Blender version list here. Each item should include version title, filename, time (HH:MM), and author — all separated by blank lines.",
    "tt_process_btn": "⚙️ Process everything to calculate active work blocks. Shortcut: Ctrl+P",
    "tt_max_break_slider": "⏸ Set the max break allowed between versions (in minutes). Used to group versions into same block.",
    "tt_max_break_input": "⌨️ Type the max break manually (in minutes).",
    "tt_result_table": "📊 Shows the daily summary with hours per day. Switch view to see work blocks.",
    "tt_export_btn": "📤 Export the current view to CSV or TXT. Shortcut: Ctrl+E",
    "tt_copy_btn": "📋 Copy total active time to clipboard. Shortcut: Ctrl+Shift+C",
    "tt_toggle_view_btn": "🔄 Cycle between Daily / Compact / Expanded views. Shortcut: Ctrl+T",
    "tt_total_label": "⏱ This is the total active time (skips long breaks).",
    "tt_exit_btn": "🚪 Close the program. Shortcut: Ctrl+Q",
    "tt_toggle_range_btn": "🔄 Toggle slider range between 60 minutes and 24 hours.",

    "EXPORT_SUCCESSFUL": "✅ EXPORT SUCCESSFUL",
    "EXPORT_FAILED": "❗ EXPORT FAILED",
    "EXPORT_DATA": "📤 EXPORT DATA",
}

# View mode constants
VIEW_DAILY = 0
VIEW_COMPACT = 1
VIEW_EXPANDED = 2


# ==================== WORKER THREAD FOR PROCESSING ====================
class VersionProcessorWorker(QObject):
    """
    Worker class to perform time-consuming data processing in a separate thread.
    Emits signals to communicate results or errors back to the main thread.
    """
    finished = Signal()
    error = Signal(str)
    results = Signal(dict)

    def __init__(self, raw_text, max_break_minutes):
        super().__init__()
        self._raw_text = raw_text
        self._max_break_minutes = max_break_minutes
        self._all_versions = []

    def run(self):
        """
        Main processing logic. This method runs in the separate thread.
        Attempts to parse as version blocks first, then as time ranges string.
        """
        try:
            try:
                self._all_versions = self._parse_versions(self._raw_text)
                current_filename = self._extract_filename(self._raw_text)
                work_blocks, total_time = self._calculate_work_blocks(
                    self._all_versions, self._max_break_minutes
                )
                daily_totals = self._calculate_daily_totals(
                    self._all_versions, self._max_break_minutes
                )
                self.results.emit({
                    'type': 'versions',
                    'data': work_blocks,
                    'total_time': total_time,
                    'filename': current_filename,
                    'daily_totals': daily_totals,
                })
            except ValueError as e:
                print(f"DEBUG: Version parsing failed: {e}. Attempting time range string parsing.")
                intervals, total_duration = self._parse_time_ranges_string(self._raw_text)
                self.results.emit({
                    'type': 'time_ranges',
                    'intervals': intervals,
                    'total_time': total_duration,
                })

        except Exception as e:
            print(f"DEBUG: General processing error: {e}")
            self.error.emit(f"{STRINGS['msg_invalid']}: {str(e)}")
        finally:
            self.finished.emit()

    def _parse_versions(self, text):
        """Converts text into a list of versions with full datetime objects.
        Handles:
          - Day-of-week format: "Sun 14:56" or bare "10:19"
          - Explicit date format: "1 Jun, 23:58" or "31 May 16:24"
        """
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        blocks = re.split(r'\n\s*\n', text)
        blocks = [block.strip() for block in blocks if block.strip()]
        print(f"DEBUG: _parse_versions - Raw text blocks: {len(blocks)}")

        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        day_map = {
            "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6
        }

        versions_temp_parsed = []

        for block_idx, block in enumerate(blocks):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if len(lines) < 2:
                print(f"DEBUG: _parse_versions - Skipping block {block_idx} due to insufficient lines: {lines}")
                continue

            version_name = None
            time_str = None
            day_of_week_str = None
            explicit_date_day = None
            explicit_date_month = None

            for i, line in enumerate(lines):
                if (line.lower().startswith("version") or line.lower().startswith("current")):
                    if line.lower() == "current version" and (i + 1) < len(lines):
                        version_name = lines[i+1]
                        day_of_week_str = "current"
                    else:
                        version_name = line

                # Try explicit date: "1 Jun, 23:58" or "31 May 16:24"
                date_match = re.search(
                    r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[,\s]+(\d{1,2}:\d{2})',
                    line, re.IGNORECASE
                )
                if date_match:
                    explicit_date_day = int(date_match.group(1))
                    explicit_date_month = date_match.group(2).lower()
                    time_str = date_match.group(3)
                else:
                    # Fall back: "Mon 14:56" or bare "10:19"
                    time_match = re.search(
                        r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\s*(\d{1,2}:\d{2})', line, re.IGNORECASE
                    )
                    if time_match:
                        found_day = time_match.group(1)
                        found_time = time_match.group(2)
                        if found_day:
                            day_of_week_str = found_day.lower()
                        time_str = found_time

            if version_name and time_str:
                try:
                    time_obj = datetime.strptime(time_str, "%H:%M").time()
                    versions_temp_parsed.append({
                        'name': version_name,
                        'time_obj': time_obj,
                        'day_of_week_str': day_of_week_str,
                        'explicit_date_day': explicit_date_day,
                        'explicit_date_month': explicit_date_month,
                    })
                    print(f"DEBUG: _parse_versions - Temp parsed: Name='{version_name}', Time='{time_obj}', "
                          f"Day='{day_of_week_str}', Explicit='{explicit_date_day} {explicit_date_month}'")
                except ValueError:
                    print(f"DEBUG: _parse_versions - Failed to parse time object for {time_str}")
                    continue
            else:
                print(f"DEBUG: _parse_versions - Block {block_idx} did not yield both version_name and time_str.")

        if not versions_temp_parsed:
            print("DEBUG: _parse_versions - No valid versions found after initial parsing.")
            raise ValueError("No valid versions found")

        versions_temp_parsed.reverse()
        print(f"DEBUG: _parse_versions - Reversed (oldest first): {[v['name'] for v in versions_temp_parsed]}")

        # --- Date inference ---
        final_versions = []
        now = datetime.now()

        # Anchor the oldest version
        first = versions_temp_parsed[0]
        if first['explicit_date_day'] is not None:
            target_month = month_map[first['explicit_date_month']]
            target_day = first['explicit_date_day']
            candidate = datetime(now.year, target_month, target_day,
                                 first['time_obj'].hour, first['time_obj'].minute)
            if candidate > now:
                candidate = candidate.replace(year=now.year - 1)
                print(f"DEBUG: _parse_versions - Oldest '{first['name']}' pushed to prev year (was future): {candidate}")
            current_version_datetime = candidate
            print(f"DEBUG: _parse_versions - Oldest '{first['name']}' anchored to explicit date: {current_version_datetime}")
        elif first['day_of_week_str'] and first['day_of_week_str'] != "current":
            current_version_datetime = datetime.combine(now.date(), first['time_obj'])
            target_weekday_num = day_map[first['day_of_week_str']]
            days_diff = (current_version_datetime.weekday() - target_weekday_num + 7) % 7
            current_version_datetime -= timedelta(days=days_diff)
            print(f"DEBUG: _parse_versions - Oldest '{first['name']}' anchored to day-of-week: {current_version_datetime}")
        else:
            current_version_datetime = datetime.combine(now.date(), first['time_obj'])
            if current_version_datetime > now:
                current_version_datetime -= timedelta(days=1)
                print(f"DEBUG: _parse_versions - Oldest '{first['name']}' pushed back (was future): {current_version_datetime}")

        final_versions.append({'name': first['name'], 'time': current_version_datetime})
        print(f"DEBUG: _parse_versions - Oldest datetime: {current_version_datetime}")

        # Forward-assign each subsequent version
        for i in range(1, len(versions_temp_parsed)):
            prev_v = final_versions[-1]
            curr = versions_temp_parsed[i]

            if curr['explicit_date_day'] is not None:
                target_month = month_map[curr['explicit_date_month']]
                target_day = curr['explicit_date_day']
                prev_year = prev_v['time'].year
                curr_dt = datetime(prev_year, target_month, target_day,
                                   curr['time_obj'].hour, curr['time_obj'].minute)
                if curr_dt <= prev_v['time']:
                    curr_dt = curr_dt.replace(year=prev_year + 1)
                    print(f"DEBUG: _parse_versions - '{curr['name']}' rolled to {curr_dt.year} (explicit date <= prev)")
                print(f"DEBUG: _parse_versions - '{curr['name']}' explicit date: {curr_dt}")
            elif curr['day_of_week_str'] and curr['day_of_week_str'] != "current":
                curr_dt = datetime.combine(prev_v['time'].date(), curr['time_obj'])
                target_weekday_num = day_map[curr['day_of_week_str']]
                days_to_advance = (target_weekday_num - curr_dt.weekday() + 7) % 7
                curr_dt += timedelta(days=days_to_advance)
                if curr_dt <= prev_v['time']:
                    curr_dt += timedelta(days=7)
                    print(f"DEBUG: _parse_versions - '{curr['name']}' week rollover (explicit day)")
                print(f"DEBUG: _parse_versions - '{curr['name']}' day-of-week aligned: {curr_dt} ({curr['day_of_week_str']})")
            else:
                curr_dt = datetime.combine(prev_v['time'].date(), curr['time_obj'])
                if curr_dt < prev_v['time']:
                    curr_dt += timedelta(days=1)
                    print(f"DEBUG: _parse_versions - '{curr['name']}' time rollover => next day")

            while curr_dt <= prev_v['time']:
                curr_dt += timedelta(days=1)
                print(f"DEBUG: _parse_versions - '{curr['name']}' safety +1d")

            final_versions.append({'name': curr['name'], 'time': curr_dt})
            print(f"DEBUG: _parse_versions - Final '{curr['name']}': {curr_dt}")

        self._all_versions = final_versions

        if not self._all_versions:
            print("DEBUG: _parse_versions - No valid versions after date inference.")
            raise ValueError("No valid versions found")

        print(f"DEBUG: _parse_versions - Done. {len(self._all_versions)} versions.")
        return self._all_versions

    def _parse_time_ranges_string(self, text):
        """Parses a string like '11h until 11h46 + 11h50 to 12h26 + ...'"""
        intervals = []
        total_duration = timedelta()
        print(f"DEBUG: _parse_time_ranges_string - Raw input text: {text}")

        time_ranges = [tr.strip() for tr in text.split('+') if tr.strip()]
        print(f"DEBUG: _parse_time_ranges_string - Individual time ranges: {time_ranges}")

        time_pattern = re.compile(r'(\d{1,2})h(?:(\d{2}))?\s*(?:until|to)\s*(\d{1,2})h(\d{2})')

        for tr_idx, tr in enumerate(time_ranges):
            match = time_pattern.search(tr)
            print(f"DEBUG: _parse_time_ranges_string - Processing '{tr}' (index {tr_idx})")
            if match:
                try:
                    start_hour = int(match.group(1))
                    start_minute = int(match.group(2)) if match.group(2) else 0
                    end_hour = int(match.group(3))
                    end_minute = int(match.group(4))

                    start_time = datetime.strptime(f"{start_hour:02d}:{start_minute:02d}", "%H:%M").time()
                    end_time = datetime.strptime(f"{end_hour:02d}:{end_minute:02d}", "%H:%M").time()

                    start_dt = datetime.combine(datetime.today(), start_time)
                    end_dt = datetime.combine(datetime.today(), end_time)

                    if end_dt < start_dt:
                        end_dt += timedelta(days=1)
                        print(f"DEBUG: _parse_time_ranges_string - Midnight rollover detected for '{tr}'. Adjusted end_dt: {end_dt}")

                    duration = end_dt - start_dt
                    intervals.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': duration,
                        'description': tr
                    })
                    total_duration += duration
                    print(f"DEBUG: _parse_time_ranges_string - Parsed interval: Start={start_time}, End={end_time}, Duration={duration}")
                except ValueError as ve:
                    print(f"DEBUG: _parse_time_ranges_string - Error parsing time range '{tr}': {ve}")
                    continue
            else:
                print(f"DEBUG: _parse_time_ranges_string - No regex match found for time range: '{tr}'")

        if not intervals:
            print("DEBUG: _parse_time_ranges_string - No valid time ranges found in the input string.")
            raise ValueError("No valid time ranges found in the input string.")

        print(f"DEBUG: _parse_time_ranges_string - Successfully parsed {len(intervals)} intervals. Total duration: {total_duration}")
        return intervals, total_duration

    def _extract_filename(self, text):
        """Attempts to extract the filename from the text."""
        blocks = text.split('\n\n')
        if blocks:
            first_block = blocks[0]
            lines = first_block.splitlines()
            if len(lines) > 1:
                filename_line = lines[1].strip()
                base_name, ext = Path(filename_line).stem, Path(filename_line).suffix
                if ext and base_name:
                    print(f"DEBUG: _extract_filename - Found filename: {filename_line}")
                    return filename_line
        print("DEBUG: _extract_filename - No filename found.")
        return ""

    def _calculate_work_blocks(self, all_versions, max_break_minutes):
        """Groups versions into continuous work blocks and calculates total active duration."""
        if len(all_versions) < 2:
            print("DEBUG: _calculate_work_blocks - Less than two versions, cannot calculate work blocks.")
            return [], timedelta()

        sorted_versions = all_versions
        print(f"DEBUG: _calculate_work_blocks - Sorted versions (oldest to newest): {[v['time'].strftime('%Y-%m-%d %H:%M') for v in sorted_versions]}")

        work_blocks = []
        current_block_versions = []

        current_block_versions.append(sorted_versions[0])
        print(f"DEBUG: _calculate_work_blocks - Starting first block with: {sorted_versions[0]['name']} at {sorted_versions[0]['time'].strftime('%Y-%m-%d %H:%M')}")

        for i in range(1, len(sorted_versions)):
            prev_version = sorted_versions[i-1]
            curr_version = sorted_versions[i]

            prev_time_dt = prev_version['time']
            curr_time_dt = curr_version['time']

            time_diff = curr_time_dt - prev_time_dt
            time_diff_minutes = time_diff.total_seconds() / 60

            print(f"DEBUG: _calculate_work_blocks - Between '{prev_version['name']}' ({prev_time_dt.strftime('%Y-%m-%d %H:%M')}) and '{curr_version['name']}' ({curr_time_dt.strftime('%Y-%m-%d %H:%M')}): Diff = {time_diff} ({time_diff_minutes:.2f} min)")

            if time_diff_minutes <= max_break_minutes:
                current_block_versions.append(curr_version)
                print(f"DEBUG: _calculate_work_blocks - Added '{curr_version['name']}' to current block. Time diff {time_diff_minutes:.2f} min <= {max_break_minutes} min.")
            else:
                if len(current_block_versions) > 1:
                    block_active_duration = self._calculate_block_duration(current_block_versions, max_break_minutes)
                    work_blocks.append({
                        'start': current_block_versions[0],
                        'end': current_block_versions[-1],
                        'versions': current_block_versions[:],
                        'duration': block_active_duration
                    })
                    print(f"DEBUG: _calculate_work_blocks - Finalized block: {current_block_versions[0]['name']} to {current_block_versions[-1]['name']}, Duration: {block_active_duration}")
                else:
                    print(f"DEBUG: _calculate_work_blocks - Skipping block with less than 2 versions: {current_block_versions[0]['name']}")

                current_block_versions = [curr_version]
                print(f"DEBUG: _calculate_work_blocks - Started new block with: {curr_version['name']} at {curr_version['time'].strftime('%Y-%m-%d %H:%M')}. Time diff {time_diff_minutes:.2f} min > {max_break_minutes} min (skipped).")

        if len(current_block_versions) > 1:
            block_active_duration = self._calculate_block_duration(current_block_versions, max_break_minutes)
            work_blocks.append({
                'start': current_block_versions[0],
                'end': current_block_versions[-1],
                'versions': current_block_versions[:],
                'duration': block_active_duration
            })
            print(f"DEBUG: _calculate_work_blocks - Finalized last block: {current_block_versions[0]['name']} to {current_block_versions[-1]['name']}, Duration: {block_active_duration}")
        else:
            print(f"DEBUG: _calculate_work_blocks - Last block has less than 2 versions, skipping: {current_block_versions[0]['name'] if current_block_versions else 'empty'}")

        total_active_time = sum((block['duration'] for block in work_blocks), timedelta())
        print(f"DEBUG: _calculate_work_blocks - Total active time calculated: {total_active_time}")

        return work_blocks, total_active_time

    def _calculate_block_duration(self, block, max_break_minutes):
        """Calculates the total duration of a work block considering only valid intervals."""
        if len(block) < 2:
            print(f"DEBUG: _calculate_block_duration - Block has less than 2 versions, returning 0 duration. Block: {[v['name'] for v in block]}")
            return timedelta()

        sorted_block = block
        print(f"DEBUG: _calculate_block_duration - Calculating duration for block starting {sorted_block[0]['name']} at {sorted_block[0]['time'].strftime('%Y-%m-%d %H:%M')}, ending {sorted_block[-1]['name']} at {sorted_block[-1]['time'].strftime('%Y-%m-%d %H:%M')}")

        total_duration = timedelta()

        for i in range(1, len(sorted_block)):
            prev_time = sorted_block[i-1]['time']
            curr_time = sorted_block[i]['time']

            time_diff = curr_time - prev_time

            if time_diff.total_seconds() / 60 <= max_break_minutes:
                total_duration += time_diff
                print(f"DEBUG: _calculate_block_duration - Adding time diff {time_diff} (within max break) to block total. Current block total: {total_duration}")
            else:
                print(f"DEBUG: _calculate_block_duration - Skipping time diff {time_diff} (exceeds max break) within block.")

        print(f"DEBUG: _calculate_block_duration - Final block duration: {total_duration}")
        return total_duration

    def _calculate_daily_totals(self, all_versions, max_break_minutes):
        """
        Calculates total active hours per calendar day, splitting intervals
        at midnight boundaries so time is attributed to the correct day.
        Only counts intervals where the gap between versions <= max_break_minutes.
        Tracks first and last version per day for display context.
        """
        from collections import defaultdict

        daily = {}  # date → {'total': timedelta, 'first_version': str or None, 'last_version': str or None}
        print(f"DEBUG: _calculate_daily_totals - Processing {len(all_versions)} versions with max_break={max_break_minutes} min.")

        for i in range(1, len(all_versions)):
            prev_v = all_versions[i-1]
            curr_v = all_versions[i]
            prev_dt = prev_v['time']
            curr_dt = curr_v['time']

            diff_minutes = (curr_dt - prev_dt).total_seconds() / 60
            if diff_minutes > max_break_minutes:
                print(f"DEBUG: _calculate_daily_totals - Skipping pair '{prev_v['name']}' -> '{curr_v['name']}' ({diff_minutes:.1f} min > {max_break_minutes})")
                continue

            print(f"DEBUG: _calculate_daily_totals - Counting pair '{prev_v['name']}' ({prev_dt}) -> '{curr_v['name']}' ({curr_dt}), diff={diff_minutes:.1f} min")

            # Split across midnight boundaries
            cursor = prev_dt
            while cursor.date() < curr_dt.date():
                # Next midnight
                next_midnight = datetime(cursor.year, cursor.month, cursor.day) + timedelta(days=1)
                chunk_end = min(next_midnight, curr_dt)
                chunk = chunk_end - cursor
                if chunk > timedelta():
                    date_key = cursor.date()
                    if date_key not in daily:
                        daily[date_key] = {'total': timedelta(), 'first_version': None, 'last_version': None}
                    daily[date_key]['total'] += chunk
                    if daily[date_key]['first_version'] is None:
                        daily[date_key]['first_version'] = prev_v['name']
                    daily[date_key]['last_version'] = curr_v['name']
                    print(f"DEBUG: _calculate_daily_totals -   -> {date_key}: +{chunk} (midnight split)")
                cursor = chunk_end

            # Remaining time on the final day
            if cursor < curr_dt:
                chunk = curr_dt - cursor
                date_key = cursor.date()
                if date_key not in daily:
                    daily[date_key] = {'total': timedelta(), 'first_version': None, 'last_version': None}
                daily[date_key]['total'] += chunk
                if daily[date_key]['first_version'] is None:
                    daily[date_key]['first_version'] = prev_v['name']
                daily[date_key]['last_version'] = curr_v['name']
                print(f"DEBUG: _calculate_daily_totals -   -> {date_key}: +{chunk} (final chunk)")

        # Debug summary
        for d in sorted(daily.keys()):
            entry = daily[d]
            print(f"DEBUG: _calculate_daily_totals - {d}: {entry['total']} (first: {entry['first_version']}, last: {entry['last_version']})")

        return daily


# ==================== MAIN WINDOW ====================
class VersionTimeTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(STRINGS["app_title"])
        self.setMinimumSize(600, 450)

        self.base_width = 1100
        self.base_height = 750

        self.settings = QSettings("Eternal 3D Solutions", "VersionsDurationTracker")
        self.max_break_minutes = DEFAULT_MAX_BREAK_MINUTES
        self.current_slider_range_max = SHORT_RANGE_MAX
        self.history_file = Path(STRINGS["history_file"])
        self.current_filename = ""
        self.compact_view = True
        self.work_blocks = []
        self.total_time = timedelta()
        self.all_versions = []
        self.is_processing = False

        # V16: Daily totals data and view mode
        self.daily_data = {}
        self.current_view = VIEW_DAILY  # Start with daily view

        self.worker_thread = None
        self.processor_worker = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px',''))
        )

        self.create_header_section()

        self.auto_update_timer = QTimer()
        self.auto_update_timer.setSingleShot(True)
        self.auto_update_timer.timeout.connect(self.process_data)
        self.auto_update_timer.setInterval(1000)

        self.loading_timer = QTimer(self)
        self.loading_timer.setInterval(300)
        self.loading_frame = 0
        self.loading_messages = [
            f"{STRINGS['status_processing']}.",
            f"{STRINGS['status_processing']}..",
            f"{STRINGS['status_processing']}...",
        ]
        self.loading_timer.timeout.connect(self._animate_loading_message)

        self.splitter = QSplitter(Qt.Horizontal)

        self.process_btn = QPushButton(STRINGS["btn_process"])
        self.process_btn.clicked.connect(self.process_data)
        self.process_btn.setToolTip(STRINGS["tt_process_btn"])

        self.export_btn = QPushButton(STRINGS["btn_export"])
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_data)
        self.export_btn.setToolTip(STRINGS["tt_export_btn"])

        self.copy_btn = QPushButton(STRINGS["btn_copy"])
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_total_to_clipboard)
        self.copy_btn.setToolTip(STRINGS["tt_copy_btn"])

        self.exit_btn = QPushButton(STRINGS["btn_exit"])
        self.exit_btn.clicked.connect(self.close)
        self.exit_btn.setToolTip(STRINGS["tt_exit_btn"])

        self.create_input_section()
        self.create_result_section()

        self.main_layout.addWidget(self.splitter, 1)

        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(STRINGS["status_ready"])

        self.apply_dark_theme()
        self.load_history()

        self.setup_shortcuts()

    def _scale_font_size(self, base_size, scaling_factor):
        effective_scaling_factor = max(0.7, min(scaling_factor, 1.5))
        return max(7, int(base_size * effective_scaling_factor))

    def _scale_px_value(self, px_str, scaling_factor):
        if 'px' in px_str:
            base_px = int(px_str.replace('px', ''))
            return f"{max(1, int(base_px * scaling_factor))}px"
        return px_str

    def _generate_stylesheet(self, scaling_factor):
        return f"""
            QWidget {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
                font-family: '{COLORS['font_family']}';
            }}
            QTextEdit {{
                background-color: {COLORS['table_header']};
                border: {self._scale_px_value(COLORS['border_width_thick'], scaling_factor)} solid {COLORS['accent']};
                border-radius: {self._scale_px_value(COLORS['border_radius_sm'], scaling_factor)};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
                padding: {self._scale_px_value(COLORS['padding_md'], scaling_factor)} {self._scale_px_value(COLORS['padding_lg'], scaling_factor)};
                color: {COLORS['text']};
            }}
            QTableWidget {{
                background-color: {COLORS['table_header']};
                border: {self._scale_px_value(COLORS['border_width_thin'], scaling_factor)} solid {COLORS['accent']};
                border-radius: {self._scale_px_value(COLORS['border_radius_sm'], scaling_factor)};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
            QHeaderView::section {{
                background-color: {COLORS['table_header']};
                padding: {self._scale_px_value(COLORS['padding_sm'], scaling_factor)};
                border: none;
                font-weight: bold;
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
            QTableWidget::item {{
                padding: {self._scale_px_value(COLORS['padding_sm'], scaling_factor)};
            }}
            QPushButton {{
                background-color: {COLORS['button']};
                border: none;
                border-bottom: {self._scale_px_value(COLORS['border_width_thick'], scaling_factor)} solid {COLORS['accent']};
                border-radius: {self._scale_px_value(COLORS['border_radius_sm'], scaling_factor)};
                padding: {self._scale_px_value(COLORS['padding_md'], scaling_factor)} {self._scale_px_value(COLORS['padding_lg'], scaling_factor)};
                font-weight: bold;
                min-width: {self._scale_px_value('100px', scaling_factor)};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['accent']};
                border-bottom: {self._scale_px_value(COLORS['border_width_thin'], scaling_factor)} solid {COLORS['accent']};
                padding-top: {int(self._scale_px_value(COLORS['padding_md'], scaling_factor).replace('px','')) + 1}px;
                padding-bottom: {int(self._scale_px_value(COLORS['padding_md'], scaling_factor).replace('px','')) - 1}px;
                padding-left: {self._scale_px_value(COLORS['padding_lg'], scaling_factor)};
                padding-right: {self._scale_px_value(COLORS['padding_lg'], scaling_factor)};
            }}
            QLabel {{
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
            QStatusBar {{
                font-size: {self._scale_font_size(COLORS['font_size_small'], scaling_factor)}pt;
                color: #aaa;
                padding: {self._scale_px_value('4px', scaling_factor)} {self._scale_px_value('8px', scaling_factor)};
            }}
            QSlider::groove:horizontal {{
                border: {self._scale_px_value(COLORS['border_width_thin'], scaling_factor)} solid {COLORS['accent']};
                height: {self._scale_px_value('8px', scaling_factor)};
                background: {COLORS['button']};
                margin: {self._scale_px_value('2px', scaling_factor)} 0;
                border-radius: {self._scale_px_value(COLORS['border_radius_sm'], scaling_factor)};
            }}
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COLORS['accent']}, stop:1 {COLORS['accent_dark']});
                border: {self._scale_px_value(COLORS['border_width_thin'], scaling_factor)} solid {COLORS['text']};
                width: {self._scale_px_value('16px', scaling_factor)};
                height: {self._scale_px_value('16px', scaling_factor)};
                margin: {self._scale_px_value('-4px', scaling_factor)} 0;
                border-radius: {self._scale_px_value('8px', scaling_factor)};
            }}
            QSlider::handle:horizontal:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COLORS['highlight']}, stop:1 {COLORS['accent']});
            }}
            QSlider::add-page:horizontal {{
                background: {COLORS['accent']};
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['button']};
            }}
            QLineEdit {{
                background-color: {COLORS['table_header']};
                border: {self._scale_px_value(COLORS['border_width_thin'], scaling_factor)} solid {COLORS['accent']};
                border-radius: {self._scale_px_value(COLORS['border_radius_sm'], scaling_factor)};
                padding: {self._scale_px_value(COLORS['padding_sm'], scaling_factor)};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
                color: {COLORS['text']};
            }}
            #title_label {{
                font-size: {self._scale_font_size(COLORS['font_size_title'], scaling_factor)}pt;
                color: {COLORS['accent']};
                margin-bottom: 4px;
            }}
            #subtitle_label {{
                font-size: {self._scale_font_size(COLORS['font_size_subtitle'], scaling_factor)}pt;
                color: #aaaaaa;
            }}
            #input_label {{
                font-size: {self._scale_font_size(COLORS['font_size_large'], scaling_factor)}pt;
            }}
            #result_label {{
                font-size: {self._scale_font_size(COLORS['font_size_large'], scaling_factor)}pt;
            }}
            #total_label {{
                background-color: {COLORS['table_header']};
                padding: {self._scale_px_value(COLORS['padding_lg'], scaling_factor)};
                border-radius: {self._scale_px_value(COLORS['border_radius_md'], scaling_factor)};
                border: {self._scale_px_value(COLORS['border_width_thick'], scaling_factor)} solid {COLORS['highlight']};
                color: {COLORS['highlight']};
                font-size: {self._scale_font_size(COLORS['font_size_total'], scaling_factor)}pt;
            }}
            #selected_duration_label {{
                background-color: {COLORS['table_header']};
                padding: {self._scale_px_value(COLORS['padding_md'], scaling_factor)};
                border-radius: {self._scale_px_value(COLORS['border_radius_sm'], scaling_factor)};
                border: {self._scale_px_value(COLORS['border_width_thin'], scaling_factor)} solid {COLORS['accent']};
                color: {COLORS['text']};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
                margin-top: {self._scale_px_value('6px', scaling_factor)};
            }}
            #break_label {{
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
        """

    def create_header_section(self):
        header_frame = QFrame()
        header_frame.setObjectName("header_frame")
        header_frame.setStyleSheet(f"""
            background-color: {COLORS['header_bg']};
            border-radius: {COLORS['border_radius_md']};
            border: none;
        """)

        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px',''))
        )
        header_layout.setSpacing(int(COLORS["margin_sm"].replace('px','')))

        title_label = QLabel(STRINGS["app_title"])
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignLeft)

        self.subtitle_frame = QFrame()
        self.subtitle_frame.setStyleSheet(f"""
            background-color: {COLORS['table_header']};
            border-radius: {COLORS['border_radius_sm']};
            padding: {COLORS['padding_sm']} {COLORS['padding_md']};
            margin-top: {COLORS['margin_sm']};
            border: none;
        """)
        subtitle_layout = QHBoxLayout(self.subtitle_frame)
        subtitle_layout.setContentsMargins(0, 0, 0, 0)

        self.subtitle_label = QLabel(STRINGS["app_subtitle"])
        self.subtitle_label.setObjectName("subtitle_label")
        self.subtitle_label.setAlignment(Qt.AlignLeft)

        subtitle_layout.addWidget(self.subtitle_label)
        subtitle_layout.addStretch()

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.subtitle_frame)

        self.main_layout.addWidget(header_frame)

    def create_input_section(self):
        input_widget = QWidget()
        input_widget.setObjectName("input_widget")
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(int(COLORS["margin_md"].replace('px','')))

        input_label = QLabel(STRINGS["label_input"])
        input_label.setObjectName("input_label")

        self.input_text = QTextEdit()
        self.input_text.setAcceptRichText(False)
        self.input_text.setPlaceholderText("Example:\nVersion 33\nfilename.blend\nThu 18:15\nAuthor\n\nVersion 32\nfilename.blend\nWed 18:10\nAuthor\n\nOR:\n11h until 11h46 + 11h50 to 12h26")
        self.input_text.textChanged.connect(self.schedule_auto_update)
        self.input_text.setToolTip(STRINGS["tt_input_text"])

        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_text, 1)

        self.splitter.addWidget(input_widget)

    def create_result_section(self):
        result_widget = QWidget()
        result_widget.setObjectName("result_widget")
        result_layout = QVBoxLayout(result_widget)
        result_layout.setSpacing(int(COLORS["margin_md"].replace('px','')))

        top_controls_layout = QHBoxLayout()

        break_label = QLabel(STRINGS["max_break_label"])
        break_label.setObjectName("break_label")

        self.max_break_input = QLineEdit()
        self.max_break_input.setValidator(QIntValidator(1, MAX_BREAK_SLIDER_RANGE))
        self.max_break_input.setText(str(self.max_break_minutes))
        self.max_break_input.setMaximumWidth(60)
        self.max_break_input.editingFinished.connect(self.on_manual_input_finished)
        self.max_break_input.setToolTip(STRINGS["tt_max_break_input"])

        self.toggle_range_btn = QPushButton(STRINGS["btn_toggle_range_long"])
        self.toggle_range_btn.clicked.connect(self._toggle_slider_range)
        self.toggle_range_btn.setToolTip(STRINGS["tt_toggle_range_btn"])

        self.toggle_view_btn = QPushButton(STRINGS["btn_toggle_view"])
        self.toggle_view_btn.clicked.connect(self.toggle_view)
        self.toggle_view_btn.setToolTip(STRINGS["tt_toggle_view_btn"])

        top_controls_layout.addWidget(break_label)
        top_controls_layout.addWidget(self.max_break_input)
        top_controls_layout.addStretch()
        top_controls_layout.addWidget(self.toggle_range_btn)
        top_controls_layout.addWidget(self.toggle_view_btn)

        self.max_break_slider = QSlider(Qt.Horizontal)
        self.max_break_slider.setRange(1, MAX_BREAK_SLIDER_RANGE)
        self.max_break_slider.setSingleStep(1)
        self.max_break_slider.setPageStep(5)
        self.max_break_slider.setTickPosition(QSlider.TicksBelow)
        self.max_break_slider.setTickInterval(5)
        self.max_break_slider.setValue(self.max_break_minutes)
        self.max_break_slider.valueChanged.connect(self.on_slider_value_changed)
        self.max_break_slider.setToolTip(STRINGS["tt_max_break_slider"])

        result_layout.addLayout(top_controls_layout)
        result_layout.addWidget(self.max_break_slider)

        self.result_label = QLabel(STRINGS["label_result"])
        self.result_label.setObjectName("result_label")
        result_layout.addWidget(self.result_label)

        self.result_table = QTableWidget()
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setSelectionBehavior(QTableWidget.SelectItems)
        self.result_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.result_table.itemSelectionChanged.connect(self._update_selected_duration_sum)
        self.result_table.setToolTip(STRINGS["tt_result_table"])

        button_layout = QHBoxLayout()

        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.copy_btn)
        button_layout.addWidget(self.exit_btn)
        button_layout.addStretch()

        self.total_label = QLabel()
        self.total_label.setObjectName("total_label")
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setToolTip(STRINGS["tt_total_label"])

        self.selected_duration_label = QLabel()
        self.selected_duration_label.setObjectName("selected_duration_label")
        self.selected_duration_label.setAlignment(Qt.AlignCenter)
        self.selected_duration_label.setText(f"{STRINGS['selected_duration_label']} <b>00:00</b>")

        result_layout.addWidget(self.result_table, 1)
        result_layout.addLayout(button_layout)
        result_layout.addWidget(self.total_label)
        result_layout.addWidget(self.selected_duration_label)

        self.splitter.addWidget(result_widget)
        self.splitter.setSizes([400, 600])

    def setup_shortcuts(self):
        self.copy_shortcut_table = QShortcut(QKeySequence.Copy, self.result_table)
        self.copy_shortcut_table.activated.connect(self.copy_selection_to_clipboard)

        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.process_btn.click)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.export_btn.click)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(self.copy_btn.click)
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self.toggle_view_btn.click)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.exit_btn.click)

    def on_slider_value_changed(self, value):
        self.max_break_input.setText(str(value))
        self.max_break_minutes = value
        self.process_data()

    def on_manual_input_finished(self):
        try:
            value = int(self.max_break_input.text())
            if value < self.max_break_slider.minimum():
                value = self.max_break_slider.minimum()
            elif value > self.max_break_slider.maximum():
                value = self.max_break_slider.maximum()

            self.max_break_slider.setValue(value)
            self.max_break_minutes = value
            self.process_data()
        except ValueError:
            self.max_break_input.setText(str(self.max_break_minutes))
            self.show_error("Invalid input for 'Max Break'. Please enter a number.")

    def _toggle_slider_range(self):
        if self.current_slider_range_max == SHORT_RANGE_MAX:
            self.current_slider_range_max = MAX_BREAK_SLIDER_RANGE
            self.toggle_range_btn.setText(STRINGS["btn_toggle_range_short"])
            print(f"DEBUG: _toggle_slider_range - Switched to LONG range ({MAX_BREAK_SLIDER_RANGE} min).")
        else:
            self.current_slider_range_max = SHORT_RANGE_MAX
            self.toggle_range_btn.setText(STRINGS["btn_toggle_range_long"])
            print(f"DEBUG: _toggle_slider_range - Switched to SHORT range ({SHORT_RANGE_MAX} min).")

        self.max_break_slider.setRange(1, self.current_slider_range_max)
        self.max_break_input.setValidator(QIntValidator(1, self.current_slider_range_max))

        if self.max_break_minutes > self.current_slider_range_max:
            self.max_break_minutes = self.current_slider_range_max
            self.max_break_slider.setValue(self.max_break_minutes)
            self.max_break_input.setText(str(self.max_break_minutes))
            print(f"DEBUG: _toggle_slider_range - Adjusted max_break_minutes to new range max: {self.max_break_minutes}")

        self.process_data()

    def toggle_view(self):
        """Cycles view mode: Daily → Compact blocks → Expanded blocks → Daily"""
        self.current_view = (self.current_view + 1) % 3

        # Update result label and toggle button text
        if self.current_view == VIEW_DAILY:
            self.result_label.setText("📊 DAILY SUMMARY")
            self.toggle_view_btn.setText(STRINGS["daily_view"])
        elif self.current_view == VIEW_COMPACT:
            self.result_label.setText("📊 WORK BLOCKS")
            self.toggle_view_btn.setText(STRINGS["compact_view"])
        else:  # VIEW_EXPANDED
            self.result_label.setText("📊 WORK BLOCKS (DETAILED)")
            self.toggle_view_btn.setText(STRINGS["expanded_view"])

        self.display_results()

    def schedule_auto_update(self):
        if self.input_text.toPlainText().strip():
            self.auto_update_timer.stop()
            self.auto_update_timer.start()
        else:
            self.auto_update_timer.stop()
            self.clear_results()
            self.status_bar.showMessage(STRINGS["status_ready"])
            self.subtitle_label.setText(STRINGS["app_subtitle"])

    def apply_dark_theme(self):
        self.setStyleSheet(self._generate_stylesheet(1.0))
        self.input_text.setTextColor(QColor(COLORS['text']))

        self.result_table.setAlternatingRowColors(True)
        self.result_table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: #444;
                alternate-background-color: {COLORS['table_row_even']};
            }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        current_width = self.width()
        current_height = self.height()

        scaling_factor = min(current_width / self.base_width, current_height / self.base_height)

        self.setStyleSheet(self._generate_stylesheet(scaling_factor))

        if self.main_layout:
            self.main_layout.setSpacing(int(self._scale_px_value(COLORS["margin_md"], scaling_factor).replace('px','')))
            self.main_layout.setContentsMargins(
                int(self._scale_px_value(COLORS["padding_lg"], scaling_factor).replace('px','')),
                int(self._scale_px_value(COLORS['padding_lg'], scaling_factor).replace('px','')),
                int(self._scale_px_value(COLORS["padding_lg"], scaling_factor).replace('px','')),
                int(COLORS["padding_lg"].replace('px',''))
            )

        header_frame = self.findChild(QFrame, "header_frame")
        if header_frame and header_frame.layout():
            header_frame.layout().setSpacing(int(self._scale_px_value(COLORS["margin_sm"], scaling_factor).replace('px','')))

        input_widget = self.findChild(QWidget, "input_widget")
        if input_widget and input_widget.layout():
            input_widget.layout().setSpacing(int(self._scale_px_value(COLORS["margin_md"], scaling_factor).replace('px','')))

        result_widget = self.findChild(QWidget, "result_widget")
        if result_widget and result_widget.layout():
            result_widget.layout().setSpacing(int(self._scale_px_value(COLORS["margin_md"], scaling_factor).replace('px','')))

        self.total_label.setStyleSheet(f"""
            background-color: {COLORS['table_header']};
            padding: {self._scale_px_value(COLORS['padding_lg'], scaling_factor)};
            border-radius: {self._scale_px_value(COLORS['border_radius_md'], scaling_factor)};
            border: {self._scale_px_value(COLORS['border_width_thick'], scaling_factor)} solid {COLORS['highlight']};
            color: {COLORS['highlight']};
            font-size: {self._scale_font_size(COLORS['font_size_total'], scaling_factor)}pt;
        """)

        self.selected_duration_label.setStyleSheet(f"""
            background-color: {COLORS['table_header']};
            padding: {self._scale_px_value(COLORS['padding_md'], scaling_factor)};
            border-radius: {self._scale_px_value(COLORS['border_radius_sm'], scaling_factor)};
            border: {self._scale_px_value(COLORS['border_width_thin'], scaling_factor)} solid {COLORS['accent']};
            color: {COLORS['text']};
            font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            margin-top: {self._scale_px_value('6px', scaling_factor)};
        """)

        self.subtitle_frame.setStyleSheet(f"""
            background-color: {COLORS['table_header']};
            border-radius: {self._scale_px_value(COLORS['border_radius_sm'], scaling_factor)};
            padding: {self._scale_px_value(COLORS['padding_sm'], scaling_factor)} {self._scale_px_value(COLORS['padding_md'], scaling_factor)};
            margin-top: {self._scale_px_value(COLORS['margin_sm'], scaling_factor)};
            border: none;
        """)

    # ==================== CORE LOGIC ====================
    def process_data(self):
        self.auto_update_timer.stop()

        if self.is_processing:
            return

        raw_text = self.input_text.toPlainText().strip()
        print(f"DEBUG: process_data - Input text length: {len(raw_text)}")

        if not raw_text:
            self.clear_results()
            self.status_bar.showMessage(STRINGS["status_ready"])
            self.subtitle_label.setText(STRINGS["app_subtitle"])
            self._reset_ui_state_immediate()
            print("DEBUG: process_data - Empty input, cleared results and reset UI.")
            return

        self.is_processing = True
        self.process_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.toggle_view_btn.setEnabled(False)
        self.max_break_slider.setEnabled(False)
        self.max_break_input.setEnabled(False)
        self.toggle_range_btn.setEnabled(False)
        print("DEBUG: process_data - UI elements disabled for processing.")

        self.loading_frame = 0
        self.status_bar.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        self.loading_timer.start()
        print("DEBUG: process_data - Loading animation started.")

        self.worker_thread = QThread()
        self.processor_worker = VersionProcessorWorker(raw_text, self.max_break_minutes)
        self.processor_worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.processor_worker.run)
        self.processor_worker.results.connect(self._handle_processing_results)
        self.processor_worker.error.connect(self._handle_processing_error)
        self.processor_worker.finished.connect(self._on_worker_finished)

        self.worker_thread.start()
        print("DEBUG: process_data - Worker thread started.")
        raw_text = self.input_text.toPlainText().strip()
        print(f"DEBUG: Texto bruto após colar: {repr(raw_text)}")

    def _handle_processing_results(self, result_dict):
        print(f"DEBUG: _handle_processing_results - Received result_dict: {result_dict.get('type')}")
        self.clear_results()

        result_type = result_dict.get('type')
        total_time = result_dict.get('total_time')

        if result_type == 'versions':
            self.work_blocks = result_dict.get('data', [])
            self.total_time = total_time
            self.all_versions = self.processor_worker._all_versions
            self.current_filename = result_dict.get('filename', "")
            self.daily_data = result_dict.get('daily_totals', {})

            if self.current_filename:
                self.subtitle_label.setText(f"WORKING ON: {self.current_filename.upper()}")
            else:
                self.subtitle_label.setText(STRINGS["app_subtitle"])

            # Default to daily view on new data
            self.current_view = VIEW_DAILY
            self.result_label.setText("📊 DAILY SUMMARY")
            self.toggle_view_btn.setText(STRINGS["daily_view"])

            self.display_results()
            self.save_to_history(self.input_text.toPlainText().strip(), self.work_blocks, self.total_time)

            self.export_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            self.toggle_view_btn.setEnabled(True)
            self.max_break_slider.setEnabled(True)
            self.max_break_input.setEnabled(True)
            self.toggle_range_btn.setEnabled(True)
            print("DEBUG: _handle_processing_results - Set UI for 'versions' mode.")

        elif result_type == 'time_ranges':
            intervals = result_dict.get('intervals', [])
            self.total_time = total_time
            self.work_blocks = []
            self.all_versions = []
            self.current_filename = ""
            self.daily_data = {}

            self.subtitle_label.setText("CALCULATING TIME RANGES")

            self.result_table.setColumnCount(3)
            self.result_table.setHorizontalHeaderLabels([
                "START TIME",
                "END TIME",
                "DURATION"
            ])
            self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.result_table.setRowCount(len(intervals))

            for row, interval in enumerate(intervals):
                start_time_str = interval['start_time'].strftime("%H:%M")
                end_time_str = interval['end_time'].strftime("%H:%M")
                duration_str = self.format_duration(interval['duration'])

                items = [
                    QTableWidgetItem(start_time_str),
                    QTableWidgetItem(end_time_str),
                    QTableWidgetItem(duration_str)
                ]
                for col, item in enumerate(items):
                    item.setTextAlignment(Qt.AlignCenter)
                    self.result_table.setItem(row, col, item)

            total_str = self.format_duration(self.total_time)
            self.total_label.setText(f"{STRINGS['total_label']} <b>{total_str}</b>")
            self.selected_duration_label.setText(f"{STRINGS['selected_duration_label']} <b>00:00</b>")

            self.export_btn.setEnabled(False)
            self.copy_btn.setEnabled(True)
            self.toggle_view_btn.setEnabled(False)
            self.max_break_slider.setEnabled(False)
            self.max_break_input.setEnabled(False)
            self.toggle_range_btn.setEnabled(False)
            print("DEBUG: _handle_processing_results - Set UI for 'time_ranges' mode.")

        self.status_bar.showMessage(STRINGS["msg_success"])

    def _handle_processing_error(self, message):
        print(f"DEBUG: _handle_processing_error - Error message: {message}")
        self.show_error(message)

    def _on_worker_finished(self):
        print("DEBUG: _on_worker_finished - Worker thread finished.")
        self.loading_timer.stop()
        self.status_bar.setStyleSheet("")
        self.status_bar.showMessage(STRINGS["status_ready"])

        self.process_btn.setEnabled(True)
        self.input_text.setEnabled(True)

        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.processor_worker.deleteLater()
            self.worker_thread.deleteLater()
            self.processor_worker = None
            self.worker_thread = None

        self.is_processing = False
        print("DEBUG: _on_worker_finished - UI state reset, worker/thread cleaned up.")

    def _reset_ui_state_immediate(self):
        print("DEBUG: _reset_ui_state_immediate - Resetting UI state immediately.")
        self.loading_timer.stop()
        self.status_bar.setStyleSheet("")
        self.process_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.toggle_view_btn.setEnabled(True)
        self.max_break_slider.setEnabled(True)
        self.max_break_input.setEnabled(True)
        self.toggle_range_btn.setEnabled(True)

    def _animate_loading_message(self):
        self.status_bar.showMessage(self.loading_messages[self.loading_frame % len(self.loading_messages)])
        self.loading_frame += 1

    def parse_versions(self, text):
        raise NotImplementedError("Parsing is now handled by the worker thread.")

    def extract_filename(self, text):
        raise NotImplementedError("Filename extraction is now handled by the worker thread.")

    def calculate_work_blocks(self):
        raise NotImplementedError("Work block calculation is now handled by the worker thread.")

    def calculate_block_duration(self, block):
        raise NotImplementedError("Block duration calculation is now handled by the worker thread.")

    # ==================== UI UPDATES ====================
    def display_results(self):
        """Displays results based on current view mode."""
        if self.current_view == VIEW_DAILY and self.daily_data:
            self.display_daily_view()
        elif self.current_view == VIEW_COMPACT and self.work_blocks:
            self.result_table.setColumnCount(5)
            self.result_table.setHorizontalHeaderLabels([
                STRINGS["col_version_start"],
                STRINGS["col_start_time"],
                STRINGS["col_version_end"],
                STRINGS["col_end_time"],
                STRINGS["col_duration"]
            ])
            self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.display_compact_view()
        elif self.current_view == VIEW_EXPANDED and self.work_blocks:
            self.result_table.setColumnCount(5)
            self.result_table.setHorizontalHeaderLabels([
                STRINGS["col_version_start"],
                STRINGS["col_start_time"],
                STRINGS["col_version_end"],
                STRINGS["col_end_time"],
                STRINGS["col_duration"]
            ])
            self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.display_expanded_view()
        else:
            # Fallback: if no data for current view, try others
            if self.daily_data:
                self.current_view = VIEW_DAILY
                self.display_daily_view()
            elif self.work_blocks:
                self.current_view = VIEW_COMPACT
                self.display_compact_view()

        self._update_selected_duration_sum()
        print(f"DEBUG: display_results - Called. View={self.current_view}, Daily data={bool(self.daily_data)}, Work blocks={bool(self.work_blocks)}")

    def display_daily_view(self):
        """Displays the daily summary table — newest day on top."""
        print("DEBUG: display_daily_view - Displaying daily summary.")

        # Set up 5-column layout for daily view
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels([
            STRINGS["col_date"],
            STRINGS["col_day"],
            STRINGS["col_total_hours"],
            STRINGS["col_first_version"],
            STRINGS["col_last_version"]
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Sort days newest to oldest
        sorted_dates = sorted(self.daily_data.keys(), reverse=True)
        self.result_table.setRowCount(len(sorted_dates))

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for row, date in enumerate(sorted_dates):
            entry = self.daily_data[date]
            day_name = day_names[date.weekday()]
            date_str = date.strftime("%Y-%m-%d")
            hours_str = self.format_duration(entry['total'])
            first_v = entry['first_version'] if entry['first_version'] else "—"
            last_v = entry['last_version'] if entry['last_version'] else "—"

            items = [
                QTableWidgetItem(date_str),
                QTableWidgetItem(day_name),
                QTableWidgetItem(hours_str),
                QTableWidgetItem(first_v),
                QTableWidgetItem(last_v),
            ]

            for item in items:
                item.setTextAlignment(Qt.AlignCenter)

            for col, item in enumerate(items):
                self.result_table.setItem(row, col, item)

        # Update total label (same total active time)
        total_str = self.format_duration(self.total_time)
        self.total_label.setText(f"{STRINGS['total_label']} <b>{total_str}</b>")

        # Update result label
        self.result_label.setText("📊 DAILY SUMMARY")
        print(f"DEBUG: display_daily_view - Total time displayed: {total_str}")

    def display_compact_view(self):
        """Displays only the work blocks (consolidated view) from most recent to oldest."""
        print("DEBUG: display_compact_view - Displaying compact view.")
        sorted_work_blocks_desc = sorted(self.work_blocks, key=lambda x: x['end']['time'], reverse=True)

        self.result_table.setRowCount(len(sorted_work_blocks_desc))

        for row, block in enumerate(sorted_work_blocks_desc):
            start_version = block['start']['name']
            start_time = block['start']['time'].strftime("%d %H:%M")

            end_version = block['end']['name']
            end_time = block['end']['time'].strftime("%d %H:%M")

            duration_str = self.format_duration(block['duration'])

            items = [
                QTableWidgetItem(start_version),
                QTableWidgetItem(start_time),
                QTableWidgetItem(end_version),
                QTableWidgetItem(end_time),
                QTableWidgetItem(duration_str)
            ]

            for item in items:
                item.setTextAlignment(Qt.AlignCenter)

            for col, item in enumerate(items):
                self.result_table.setItem(row, col, item)

        total_str = self.format_duration(self.total_time)
        self.total_label.setText(
            f"{STRINGS['total_label']} <b>{total_str}</b>"
        )
        print(f"DEBUG: display_compact_view - Total time displayed: {total_str}")

    def display_expanded_view(self):
        """Displays all version transitions with duration and indication of ignored intervals."""
        print("DEBUG: display_expanded_view - Displaying expanded view.")
        if not self.all_versions or len(self.all_versions) < 2:
            self.result_table.setRowCount(0)
            self.total_label.setText(f"{STRINGS['total_label']} <b>00:00</b>")
            print("DEBUG: display_expanded_view - Not enough versions for expanded view.")
            return

        self.result_table.setRowCount(len(self.all_versions) - 1)

        row_index = 0
        for i in range(len(self.all_versions) - 1, 0, -1):
            curr_version_data = self.all_versions[i]
            prev_version_data = self.all_versions[i-1]

            curr_time_dt = curr_version_data['time']
            prev_time_dt = prev_version_data['time']

            time_diff = curr_time_dt - prev_time_dt

            duration_str = self.format_duration(time_diff)

            if time_diff.total_seconds() / 60 > self.max_break_minutes:
                duration_str += f" (IGNORED - Break > {self.max_break_minutes} min)"

            items = [
                QTableWidgetItem(curr_version_data['name']),
                QTableWidgetItem(curr_time_dt.strftime("%d %H:%M")),
                QTableWidgetItem(prev_version_data['name']),
                QTableWidgetItem(prev_time_dt.strftime("%d %H:%M")),
                QTableWidgetItem(duration_str)
            ]

            for item in items:
                item.setTextAlignment(Qt.AlignCenter)
                if row_index % 2 == 0:
                    item.setBackground(QColor(COLORS['table_row_even']))
                else:
                    item.setBackground(QColor(COLORS['table_row_odd']))

            for col, item in enumerate(items):
                self.result_table.setItem(row_index, col, item)

            row_index += 1

        total_str = self.format_duration(self.total_time)
        self.total_label.setText(
            f"{STRINGS['total_label']} <b>{total_str}</b>"
        )
        print(f"DEBUG: display_expanded_view - Total time displayed: {total_str}")

    def format_duration(self, duration):
        """Formats timedelta to HH:MM"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{hours:02d}:{minutes:02d}"

    def _parse_duration_string(self, duration_str):
        """Parses a duration string (HH:MM) into a timedelta object."""
        try:
            clean_duration_str = duration_str.split(' (')[0].strip()
            parts = clean_duration_str.split(':')
            if len(parts) == 2:
                hours = int(parts[0])
                minutes = int(parts[1])
                return timedelta(hours=hours, minutes=minutes)
        except ValueError:
            print(f"DEBUG: _parse_duration_string - Failed to parse duration '{duration_str}'.")
            return timedelta(0)
        return timedelta(0)

    def _update_selected_duration_sum(self):
        """Calculates and displays the sum of durations from selected cells."""
        selected_items = self.result_table.selectedItems()
        sum_duration = timedelta()

        duration_col_index = -1
        for i in range(self.result_table.columnCount()):
            header_text = self.result_table.horizontalHeaderItem(i).text()
            # Support both daily (TOTAL HOURS) and work blocks (DURATION) columns
            if header_text == STRINGS["col_duration"] or header_text == STRINGS["col_total_hours"] or header_text == "DURATION":
                duration_col_index = i
                break

        if duration_col_index == -1:
            self.selected_duration_label.setText(f"{STRINGS['selected_duration_label']} <b>00:00</b>")
            print("DEBUG: _update_selected_duration_sum - Duration column not found.")
            return

        processed_rows = set()

        for item in selected_items:
            if item.column() == duration_col_index and item.row() not in processed_rows:
                duration_text = item.text()
                sum_duration += self._parse_duration_string(duration_text)
                processed_rows.add(item.row())

        self.selected_duration_label.setText(
            f"{STRINGS['selected_duration_label']} <b>{self.format_duration(sum_duration)}</b>"
        )
        if sum_duration == timedelta(0):
            self.selected_duration_label.setText(f"{STRINGS['selected_duration_label']} <b>00:00</b>")
        print(f"DEBUG: _update_selected_duration_sum - Selected duration sum: {self.format_duration(sum_duration)}")

    def copy_total_to_clipboard(self):
        """Copies the total time value to the clipboard (HH:MM only)"""
        total_text = self.total_label.text()
        if "<b>" in total_text:
            total_value = total_text.split("<b>")[1].split("</b>")[0]
        else:
            total_value = total_text.split(":")[-1].strip()

        clipboard = QApplication.clipboard()
        clipboard.setText(total_value)
        self.status_bar.showMessage(STRINGS["msg_copied"])
        print(f"DEBUG: copy_total_to_clipboard - Copied: {total_value}")

    def copy_selection_to_clipboard(self):
        """Copies the table selection to the clipboard"""
        selected_ranges = self.result_table.selectedRanges()
        if not selected_ranges:
            print("DEBUG: copy_selection_to_clipboard - No selection to copy.")
            return

        clipboard_text = ""
        header_items = [self.result_table.horizontalHeaderItem(i).text() for i in range(self.result_table.columnCount())]
        clipboard_text += "\t".join(header_items) + "\n"

        rows = sorted(list(set(item.row() for item in self.result_table.selectedItems())))
        cols = sorted(list(set(item.column() for item in self.result_table.selectedItems())))

        for r in rows:
            row_data = []
            for c in cols:
                item = self.result_table.item(r, c)
                row_data.append(item.text() if item else "")
            clipboard_text += "\t".join(row_data) + "\n"

        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text.strip())
        self.status_bar.showMessage("📋 Selection copied to clipboard!")
        print(f"DEBUG: copy_selection_to_clipboard - Copied selection:\n{clipboard_text.strip()}")

    # ==================== EXPORT/HISTORY ====================
    def export_data(self):
        """Exports data to CSV or TXT based on current view"""
        options = QFileDialog.Option()

        if self.current_view == VIEW_DAILY:
            default_name = f"{self.current_filename}_daily_summary" if self.current_filename else "daily_summary"
        else:
            default_name = f"{self.current_filename}_work_blocks" if self.current_filename else "work_blocks"

        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            STRINGS["EXPORT_DATA"],
            default_name,
            f"{STRINGS['export_csv']};;{STRINGS['export_txt']}",
            options=options
        )

        if not file_name:
            print("DEBUG: export_data - Export cancelled by user.")
            return

        if selected_filter == STRINGS["export_csv"]:
            self.export_to_csv(file_name)
        else:
            self.export_to_txt(file_name)
        print(f"DEBUG: export_data - Export initiated to {file_name} as {selected_filter}.")

    def export_to_csv(self, file_path):
        """Exports data to CSV format based on current view"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                col_count = self.result_table.columnCount()

                # Write headers from current table view
                headers = [self.result_table.horizontalHeaderItem(i).text() for i in range(col_count)]
                writer.writerow(headers)

                for row in range(self.result_table.rowCount()):
                    row_data = []
                    for col in range(col_count):
                        item = self.result_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

                # Add total
                total_text = self.total_label.text().split(">")[-1].replace("</b", "")
                writer.writerow([""] * (col_count - 1) + ["TOTAL", total_text.strip()])

            QMessageBox.information(
                self,
                STRINGS["EXPORT_SUCCESSFUL"],
                f"DATA EXPORTED TO CSV:\n{file_path}"
            )
            print(f"DEBUG: export_to_csv - Successfully exported to {file_path}")
        except Exception as e:
            self.show_error(f"{STRINGS['EXPORT_FAILED']}: {str(e)}")
            print(f"DEBUG: export_to_csv - Error during export: {e}")

    def export_to_txt(self, file_path):
        """Exports data to TXT format based on current view"""
        try:
            col_count = self.result_table.columnCount()
            # Approximate column widths (fixed-width text export)
            col_widths = []
            for c in range(col_count):
                header = self.result_table.horizontalHeaderItem(c).text()
                # Find max width in this column
                max_w = len(header)
                for r in range(self.result_table.rowCount()):
                    item = self.result_table.item(r, c)
                    if item and len(item.text()) > max_w:
                        max_w = len(item.text())
                col_widths.append(max(max_w + 2, 12))  # Min 12 chars wide

            with open(file_path, 'w', encoding='utf-8') as file:
                # Write headers
                header_line = ""
                for c in range(col_count):
                    header = self.result_table.horizontalHeaderItem(c).text()
                    header_line += header.ljust(col_widths[c])
                file.write(header_line + "\n")
                file.write("-" * sum(col_widths) + "\n")

                for row in range(self.result_table.rowCount()):
                    row_line = ""
                    for col in range(col_count):
                        item = self.result_table.item(row, col)
                        text = item.text() if item else ""
                        row_line += text.ljust(col_widths[col])
                    file.write(row_line + "\n")

                # Add total
                total_text = self.total_label.text().split(">")[-1].replace("</b", "").strip()
                file.write("\n" + "-" * sum(col_widths) + "\n")
                file.write(f"{'TOTAL':<{sum(col_widths) - 20}}{total_text:>20}")

            QMessageBox.information(
                self,
                STRINGS["EXPORT_SUCCESSFUL"],
                f"DATA EXPORTED TO TXT:\n{file_path}"
            )
            print(f"DEBUG: export_to_txt - Successfully exported to {file_path}")
        except Exception as e:
            self.show_error(f"{STRINGS['EXPORT_FAILED']}: {str(e)}")
            print(f"DEBUG: export_to_txt - Error during export: {e}")

    def save_to_history(self, raw_input, work_blocks, total_time):
        """Saves the current session to history"""
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as file:
                    history = json.load(file)
            except:
                history = []

        if len(history) >= 50:
            history = history[-49:]

        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": raw_input,
            "blocks": [
                {
                    "start": b['start']['name'],
                    "start_time": b['start']['time'].strftime("%Y-%m-%d %H:%M"),
                    "end": b['end']['name'],
                    "end_time": b['end']['time'].strftime("%Y-%m-%d %H:%M"),
                    "duration": str(b['duration'])
                } for b in work_blocks
            ],
            "total": str(total_time)
        }

        history.append(entry)

        try:
            with open(self.history_file, 'w', encoding='utf-8') as file:
                json.dump(history, file, indent=2)
            print("DEBUG: save_to_history - History saved.")
        except Exception as e:
            print(f"DEBUG: save_to_history - Failed to save history: {e}")
            pass

    def load_history(self):
        """Loads history from file"""
        if not self.history_file.exists():
            print("DEBUG: load_history - History file does not exist.")
            return

        try:
            with open(self.history_file, 'r', encoding='utf-8') as file:
                history = json.load(file)
                if history:
                    last_entry = history[-1]
                    self.input_text.setText(last_entry["input"])
                    print("DEBUG: load_history - Last entry loaded from history.")
        except Exception as e:
            print(f"DEBUG: load_history - Failed to load history: {e}")
            pass

    # ==================== UTILITIES ====================
    def clear_results(self):
        """Clears current results and resets to daily view defaults"""
        print("DEBUG: clear_results - Clearing results and resetting table headers.")
        self.result_table.setRowCount(0)
        # Reset to daily view headers
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels([
            STRINGS["col_date"],
            STRINGS["col_day"],
            STRINGS["col_total_hours"],
            STRINGS["col_first_version"],
            STRINGS["col_last_version"]
        ])
        self.total_label.clear()
        self.selected_duration_label.clear()
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.toggle_view_btn.setEnabled(True)
        self.max_break_slider.setEnabled(True)
        self.max_break_input.setEnabled(True)
        self.toggle_range_btn.setEnabled(True)

    def show_error(self, message):
        """Displays an error message"""
        print(f"DEBUG: show_error - Displaying error: {message}")
        self.loading_timer.stop()
        self.status_bar.setStyleSheet(f"color: {COLORS['error']};")
        self.status_bar.showMessage(message)
        self.clear_results()

        QApplication.processEvents()
        QTimer.singleShot(3000, lambda: self.status_bar.setStyleSheet(""))

    def closeEvent(self, event):
        """Saves settings on close"""
        print("DEBUG: closeEvent - Saving settings.")
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("splitter_sizes", self.splitter.sizes())

        super().closeEvent(event)
        print("DEBUG: closeEvent - Settings saved, closing application.")


# ==================== APPLICATION START ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = VersionTimeTracker()

    if window.settings.contains("window_geometry"):
        window.restoreGeometry(window.settings.value("window_geometry"))

    if window.settings.contains("splitter_sizes"):
        sizes = window.settings.value("splitter_sizes")
        window.splitter.setSizes([int(size) for size in sizes])

    window.show()
    sys.exit(app.exec())
