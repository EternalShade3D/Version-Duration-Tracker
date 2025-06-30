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

# ==================== CONSTANTS ====================
COLORS = {
    # 🎨 Base layout
    "bg": "#121212",             # Main background
    "header_bg": "#1a1a1a",      # Header/nav bar
    "text": "#e0e0e0",           # Standard text
    "accent": "#2979ff",         # Main accent color (bright blue)
    "highlight": "#ffd600",      # Used for totals or alerts

    # 🔘 Buttons
    "button": "#2a2a2a",         # Default button background
    "button_hover": "#333333",   # Hover effect for buttons
    "error": "#ff4c4c",          # Error color (alerts, warnings)

    # 📋 Table colors
    "table_header": "#1f1f1f",
    "table_row_even": "#191919",
    "table_row_odd": "#151515",

    # 🧩 Typography
    "font_family": "Segoe UI, sans-serif",

    # 🔠 Base Font sizes (will be scaled dynamically)
    "font_size_small": 9,
    "font_size_medium": 11,
    "font_size_large": 13,
    "font_size_total": 14,
    "font_size_subtitle": 14,
    "font_size_title": 24,

    # 📐 Borders & Spacing
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

STRINGS = {
    # 🧠 App identity
    "app_title": "▶ VERSION TIME TRACKER V11",
    "app_subtitle": "🧮 BLENDER VERSION TIME CALCULATOR",

    # 🧾 Input
    "label_input": "📥 PASTE YOUR VERSION LIST:",

    # 🔘 Buttons
    "btn_process": "⚙️ PROCESS",
    "btn_export": "📤 EXPORT",
    "btn_copy": "📋 COPY TOTAL",
    "btn_toggle_view": "🔄 TOGGLE VIEW",
    "btn_exit": "🚪 EXIT",

    # 📊 Results
    "label_result": "📊 WORK BLOCKS",

    # ⚠️ Status & messages
    "msg_invalid": "❗ INVALID OR MISSING DATA FOUND",
    "msg_success": "✅ DONE! EVERYTHING PROCESSED",
    "msg_copied": "📋 TOTAL TIME COPIED!",

    # 💾 Export formats
    "export_csv": "📄 CSV FILES (*.CSV)",
    "export_txt": "📄 TEXT FILES (*.TXT)",

    # 🔄 Status display
    "status_ready": "🟢 READY",
    "status_processing": "⏳ WORKING", # Removed dots here, will be added by animation

    # 🧱 Table headers
    "col_version": "🔢 VERSION",
    "col_time": "⏱ TIME",
    "col_version_start": "🟩 START\nVERSION",
    "col_start_time": "🕒 START\nTIME",
    "col_version_end": "🏁 END\nVERSION",
    "col_end_time": "🕓 END\nTIME",
    "col_duration": "🕘 DURATION",

    # 🧮 Summary
    "total_label": "⏱ TOTAL ACTIVE TIME:",
    "selected_duration_label": "∑ SELECTED DURATION:", # New string for selected duration
    "history_file": "version_tracker_history.json",
    "max_break_label": "⏸ MAX BREAK (MINUTES):",
    "compact_view": "📦 COMPACT VIEW",
    "expanded_view": "📂 EXPANDED VIEW",

    # 💡 Tooltips — ADHD-friendly
    "tt_input_text": "📥 Paste your Blender version list here. Each item should include version title, filename, time (HH:MM), and author — all separated by blank lines.",
    "tt_process_btn": "⚙️ Process everything to calculate active work blocks. Shortcut: Ctrl+P",
    "tt_max_break_slider": "⏸ Set the max break allowed between versions (in minutes). Used to group versions into same block.",
    "tt_max_break_input": "⌨️ Type the max break manually (in minutes).",
    "tt_result_table": "📊 Shows the grouped work blocks. Compact = summary | Expanded = full version list. Select rows/cells to see sum of durations.",
    "tt_export_btn": "📤 Export the table to CSV or TXT. Shortcut: Ctrl+E",
    "tt_copy_btn": "📋 Copy total active time to clipboard. Shortcut: Ctrl+Shift+C",
    "tt_toggle_view_btn": "🔄 Switch between compact/expanded view. Shortcut: Ctrl+T",
    "tt_total_label": "⏱ This is the total active time (skips long breaks).",
    "tt_exit_btn": "🚪 Close the program. Shortcut: Ctrl+Q",

    # New strings for QMessageBox titles/messages
    "EXPORT_SUCCESSFUL": "✅ EXPORT SUCCESSFUL",
    "EXPORT_FAILED": "❗ EXPORT FAILED",
    "EXPORT_DATA": "📤 EXPORT DATA", # Added for QFileDialog title
}

# ==================== WORKER THREAD FOR PROCESSING ====================
class VersionProcessorWorker(QObject):
    """
    Worker class to perform time-consuming data processing in a separate thread.
    Emits signals to communicate results or errors back to the main thread.
    """
    finished = Signal()
    error = Signal(str)
    results = Signal(list, timedelta, str) # work_blocks, total_time, current_filename

    def __init__(self, raw_text, max_break_minutes):
        super().__init__()
        self._raw_text = raw_text
        self._max_break_minutes = max_break_minutes
        self._all_versions = [] # To store parsed versions
        
    def run(self):
        """
        Main processing logic. This method runs in the separate thread.
        """
        try:
            # 1. Parse versions
            self._all_versions = self._parse_versions(self._raw_text)
            
            # 2. Extract filename
            current_filename = self._extract_filename(self._raw_text)

            # 3. Calculate work blocks and total time
            work_blocks, total_time = self._calculate_work_blocks(
                self._all_versions, self._max_break_minutes
            )
            
            # Emit results back to the main thread
            self.results.emit(work_blocks, total_time, current_filename)
            
        except Exception as e:
            # Emit error message back to the main thread
            self.error.emit(f"{STRINGS['msg_invalid']}: {str(e)}")
        finally:
            # Always emit finished signal, regardless of success or failure
            self.finished.emit()

    def _parse_versions(self, text):
            """Converts text into a list of versions with timestamps."""
            versions = []
            blocks = text.split('\n\n')

            for block in blocks:
                lines = [line.strip() for line in block.splitlines() if line.strip()]
                if len(lines) < 2:
                    continue
                    
                version_name = None
                time_str = None
                
                # Iterate through lines to find both version name and time
                for i, line in enumerate(lines):
                    # Try to find the version name first
                    if (line.lower().startswith("version") or line.lower().startswith("current")):
                        # If it's "Current version", the actual name might be on the next line
                        if line.lower() == "current version" and (i + 1) < len(lines):
                            version_name = lines[i+1] # Take the next line as the version name
                        else:
                            version_name = line # Otherwise, the version name is on this line
                    
                    # Then try to find the time string
                    if len(line) == 5 and line[2] == ':':
                        try:
                            datetime.strptime(line, "%H:%M")
                            time_str = line
                        except ValueError:
                            continue
                    elif len(line) == 4 and line[1] == ':': # Handles 9:30 format
                        try:
                            datetime.strptime(f"0{line}", "%H:%M") # Prepend '0' for parsing
                            time_str = f"0{line}"
                        except ValueError:
                            continue
                
                # If both version_name and time_str are found, add to versions
                if version_name and time_str:
                    try:
                        time_obj = datetime.strptime(time_str, "%H:%M").time()
                        versions.append({
                            'name': version_name,
                            'time': time_obj
                        })
                    except ValueError:
                        continue # Skip if time parsing fails even after initial check
            
            if not versions:
                raise ValueError("No valid versions found")
            
            return versions
    
    def _extract_filename(self, text):
        """Attempts to extract the filename from the text, including extension."""
        blocks = text.split('\n\n')
        if blocks:
            first_block = blocks[0]
            lines = first_block.splitlines()
            if len(lines) > 1:
                filename_line = lines[1].strip()
                # Check if it looks like a filename with an extension (e.g., .blend)
                # Use os.path.splitext to correctly get the base name and extension
                base_name, ext = Path(filename_line).stem, Path(filename_line).suffix
                if ext and base_name: # Ensure both exist
                    return filename_line # Return the full filename with extension
        return ""
    
    def _calculate_work_blocks(self, all_versions, max_break_minutes):
        """Groups versions into continuous work blocks and calculates total active duration."""
        if len(all_versions) < 2:
            raise ValueError("At least two versions needed")
        
        sorted_versions = sorted(all_versions, key=lambda x: x['time'])
        
        work_blocks = []
        current_block_versions = []
        # total_active_time = timedelta() # REMOVED THIS LINE

        if not sorted_versions:
            return [], timedelta()
        
        current_block_versions.append(sorted_versions[0])
        
        for i in range(1, len(sorted_versions)):
            prev_version = sorted_versions[i-1]
            curr_version = sorted_versions[i]
            
            prev_time_dt = datetime.combine(datetime.today(), prev_version['time'])
            curr_time_dt = datetime.combine(datetime.today(), curr_version['time'])
            
            # This handles cases where time rolls over midnight (e.g., 23:59 -> 00:01)
            # by assuming the later time is on the next day if it's chronologically smaller.
            if curr_time_dt < prev_time_dt:
                curr_time_dt += timedelta(days=1)

            time_diff = curr_time_dt - prev_time_dt
            
            # If the time difference is within the allowed max break, add to current block
            if time_diff.total_seconds() / 60 <= max_break_minutes:
                current_block_versions.append(curr_version)
                # total_active_time += time_diff # REMOVED THIS LINE
            else:
                # If break is too long, finalize the current block and start a new one
                if len(current_block_versions) > 0:
                    block_active_duration = self._calculate_block_duration(current_block_versions, max_break_minutes)
                    
                    work_blocks.append({
                        'start': current_block_versions[0],
                        'end': current_block_versions[-1],
                        'versions': current_block_versions[:], # Store a copy of versions in this block
                        'duration': block_active_duration
                    })
                current_block_versions = [curr_version] # Start new block with current version
        
        # After loop, add the last remaining block
        if len(current_block_versions) > 0:
            block_active_duration = self._calculate_block_duration(current_block_versions, max_break_minutes)
            work_blocks.append({
                'start': current_block_versions[0],
                'end': current_block_versions[-1],
                'versions': current_block_versions[:],
                'duration': block_active_duration
            })
            
        # Calculate total_active_time by summing the duration of all completed work blocks
        total_active_time = sum((block['duration'] for block in work_blocks), timedelta())
            
        return work_blocks, total_active_time
    
    def _calculate_block_duration(self, block, max_break_minutes):
        """Calculates the total duration of a work block considering only valid intervals."""
        if len(block) < 2:
            return timedelta()
            
        total_duration = timedelta()
        sorted_block = sorted(block, key=lambda x: x['time'])
        
        for i in range(1, len(sorted_block)):
            prev_time = datetime.combine(datetime.today(), sorted_block[i-1]['time'])
            curr_time = datetime.combine(datetime.today(), sorted_block[i]['time'])
            
            if curr_time < prev_time:
                curr_time += timedelta(days=1)

            time_diff = curr_time - prev_time
            
            if time_diff.total_seconds() / 60 <= max_break_minutes:
                total_duration += time_diff
        
        return total_duration

# ==================== MAIN WINDOW ====================
class VersionTimeTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(STRINGS["app_title"])
        self.setMinimumSize(600, 450) # Reduced minimum size for more flexibility
        
        # Reference size for font scaling
        self.base_width = 1100 # Original width used for initial design
        self.base_height = 750 # Original height used for initial design

        # Configurações
        self.settings = QSettings("DeepSeek", "VersionTimeTracker")
        self.max_break_minutes = 10  # default
        self.history_file = Path(STRINGS["history_file"])
        self.current_filename = ""
        self.compact_view = True
        self.work_blocks = []
        self.total_time = timedelta()
        self.all_versions = []  # Armazena todas as versões parseadas
        self.is_processing = False # Flag to indicate if processing is ongoing
        
        # Worker thread and processor worker will be instantiated in process_data
        self.worker_thread = None 
        self.processor_worker = None 

        # Widgets principais
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        # Margins and spacing will be handled by the dynamic stylesheet
        # Initial margins, will be scaled in resizeEvent
        self.main_layout.setContentsMargins(
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px','')),
            int(COLORS["padding_lg"].replace('px',''))
        )
        
        # Cabeçalho com título e subtítulo
        self.create_header_section()
        
        # Timer para atualização automática
        self.auto_update_timer = QTimer()
        self.auto_update_timer.setSingleShot(True)
        self.auto_update_timer.timeout.connect(self.process_data)
        self.auto_update_timer.setInterval(1000)  # Changed to 1 second
        
        # Loading animation timer
        self.loading_timer = QTimer(self)
        self.loading_timer.setInterval(300) # Update every 300ms
        self.loading_frame = 0
        self.loading_messages = [
            f"{STRINGS['status_processing']}.",
            f"{STRINGS['status_processing']}..",
            f"{STRINGS['status_processing']}...",
        ]
        self.loading_timer.timeout.connect(self._animate_loading_message)

        # Splitter para áreas redimensionáveis
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Inicializa os botões aqui para que sejam acessíveis em create_result_section
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

        # Área de input (esquerda)
        self.create_input_section()
        
        # Área de resultados (direita)
        self.create_result_section()
        
        # Adicionar ao layout principal
        self.main_layout.addWidget(self.splitter, 1)
        
        # Barra de status
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False) # Remove resize grip
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(STRINGS["status_ready"]) # Initial message
        
        # Apply initial theme
        self.apply_dark_theme()
        self.load_history()
        
        # Set up shortcuts
        self.setup_shortcuts()
    
    def _scale_font_size(self, base_size, scaling_factor):
        """Helper to scale font sizes with minimum and maximum limits."""
        # Ensure a reasonable range for scaling
        effective_scaling_factor = max(0.7, min(scaling_factor, 1.5)) # Scale between 70% and 150%
        return max(7, int(base_size * effective_scaling_factor)) # Minimum font size of 7pt

    def _scale_px_value(self, px_str, scaling_factor):
        """Helper to scale pixel values from string (e.g., '12px') with minimum limit."""
        if 'px' in px_str:
            base_px = int(px_str.replace('px', ''))
            return f"{max(1, int(base_px * scaling_factor))}px"
        return px_str # Return as is if not px

    def _generate_stylesheet(self, scaling_factor):
        """Generates the dynamic stylesheet based on the scaling factor."""
        
        # Helper to scale pixel values for stylesheet strings
        # This function now correctly closes over 'scaling_factor'
        def get_scaled_px(px_str_val):
            return self._scale_px_value(px_str_val, scaling_factor)

        return f"""
            QWidget {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
                font-family: '{COLORS['font_family']}';
            }}
            QTextEdit {{
                background-color: {COLORS['table_header']};
                border: {get_scaled_px(COLORS['border_width_thick'])} solid {COLORS['accent']};
                border-radius: {get_scaled_px(COLORS['border_radius_sm'])};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
                padding: {get_scaled_px(COLORS['padding_md'])} {get_scaled_px(COLORS['padding_lg'])};
                color: {COLORS['text']}; /* Explicitly set text color */
            }}
            QTableWidget {{
                background-color: {COLORS['table_header']};
                border: {get_scaled_px(COLORS['border_width_thin'])} solid {COLORS['accent']};
                border-radius: {get_scaled_px(COLORS['border_radius_sm'])};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
            QHeaderView::section {{
                background-color: {COLORS['table_header']};
                padding: {get_scaled_px(COLORS['padding_sm'])};
                border: none;
                font-weight: bold;
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
            QTableWidget::item {{
                padding: {get_scaled_px(COLORS['padding_sm'])};
            }}
            QPushButton {{
                background-color: {COLORS['button']};
                border: none;
                border-bottom: {get_scaled_px(COLORS['border_width_thick'])} solid {COLORS['accent']};
                border-radius: {get_scaled_px(COLORS['border_radius_sm'])};
                padding: {get_scaled_px(COLORS['padding_md'])} {get_scaled_px(COLORS['padding_lg'])};
                font-weight: bold;
                min-width: {get_scaled_px('100px')};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['accent']};
                border-bottom: {get_scaled_px(COLORS['border_width_thin'])} solid {COLORS['accent']};
                padding-top: {int(get_scaled_px(COLORS['padding_md']).replace('px','')) + 1}px;
                padding-bottom: {int(get_scaled_px(COLORS['padding_md']).replace('px','')) - 1}px;
                padding-left: {get_scaled_px(COLORS['padding_lg'])};
                padding-right: {get_scaled_px(COLORS['padding_lg'])};
            }}
            QLabel {{
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
            QStatusBar {{
                font-size: {self._scale_font_size(COLORS['font_size_small'], scaling_factor)}pt;
                color: #aaa;
                padding: {get_scaled_px('4px')} {get_scaled_px('8px')}; /* Adjusted padding for status bar */
            }}
            QSlider::groove:horizontal {{
                border: {get_scaled_px(COLORS['border_width_thin'])} solid {COLORS['accent']};
                height: {get_scaled_px('8px')};
                background: {COLORS['button']};
                margin: {get_scaled_px('2px')} 0;
                border-radius: {get_scaled_px(COLORS['border_radius_sm'])};
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['accent']};
                border: {get_scaled_px(COLORS['border_width_thin'])} solid {COLORS['text']};
                width: {get_scaled_px('18px')};
                margin: {get_scaled_px('-5px')} 0;
                border-radius: {get_scaled_px(COLORS['border_radius_lg'])};
            }}
            QSlider::add-page:horizontal {{
                background: {COLORS['accent']};
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['button']};
            }}
            QLineEdit {{
                background-color: {COLORS['table_header']};
                border: {get_scaled_px(COLORS['border_width_thin'])} solid {COLORS['accent']};
                border-radius: {get_scaled_px(COLORS['border_radius_sm'])};
                padding: {get_scaled_px(COLORS['padding_sm'])};
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
                padding: {get_scaled_px(COLORS['padding_lg'])};
                border-radius: {get_scaled_px(COLORS['border_radius_md'])};
                border: {get_scaled_px(COLORS['border_width_thick'])} solid {COLORS['highlight']}; /* Re-added yellow border */
                color: {COLORS['highlight']};
                font-size: {self._scale_font_size(COLORS['font_size_total'], scaling_factor)}pt;
            }}
            #selected_duration_label {{ /* New style for selected duration */
                background-color: {COLORS['table_header']};
                padding: {get_scaled_px(COLORS['padding_md'])};
                border-radius: {get_scaled_px(COLORS['border_radius_sm'])};
                border: {get_scaled_px(COLORS['border_width_thin'])} solid {COLORS['accent']};
                color: {COLORS['text']};
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
                margin-top: {get_scaled_px('6px')}; /* Small margin above it */
            }}
            #break_label {{
                font-size: {self._scale_font_size(COLORS['font_size_medium'], scaling_factor)}pt;
            }}
        """

    def create_header_section(self):
        """Cria a seção de cabeçalho com título e subtítulo"""
        header_frame = QFrame()
        header_frame.setObjectName("header_frame") # Added object name
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
        
        # Título principal (ID para stylesheet)
        title_label = QLabel(STRINGS["app_title"])
        title_label.setObjectName("title_label") # Set object name for stylesheet targeting
        title_label.setAlignment(Qt.AlignLeft) # Alinhado à esquerda
        
        # Subtítulo (para nome do arquivo) - Agora dentro de um QFrame para destaque
        self.subtitle_frame = QFrame()
        self.subtitle_frame.setStyleSheet(f"""
            background-color: {COLORS['table_header']};
            border-radius: {COLORS['border_radius_sm']};
            padding: {COLORS['padding_sm']} {COLORS['padding_md']};
            margin-top: {COLORS['margin_sm']};
            border: none; /* REMOVED BORDER/OUTLINE AS REQUESTED */
        """)
        subtitle_layout = QHBoxLayout(self.subtitle_frame)
        subtitle_layout.setContentsMargins(0, 0, 0, 0)
        
        self.subtitle_label = QLabel(STRINGS["app_subtitle"])
        self.subtitle_label.setObjectName("subtitle_label") # Set object name for stylesheet targeting
        self.subtitle_label.setAlignment(Qt.AlignLeft) # Alinhado à esquerda
        
        subtitle_layout.addWidget(self.subtitle_label)
        subtitle_layout.addStretch() # Re-added stretch to push content to left
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.subtitle_frame)
        
        self.main_layout.addWidget(header_frame)
    
    def create_input_section(self):
        """Cria a seção de entrada de dados (lado esquerdo)"""
        input_widget = QWidget()
        input_widget.setObjectName("input_widget") # Added object name
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(int(COLORS["margin_md"].replace('px','')))
        
        # Label (ID para stylesheet)
        input_label = QLabel(STRINGS["label_input"])
        input_label.setObjectName("input_label") # Set object name for stylesheet targeting
        
        # Campo de texto
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Example:\nVersion 33\nfilename.blend\n18:15\nAuthor\n\nVersion 32\nfilename.blend\n18:10\nAuthor")
        self.input_text.textChanged.connect(self.schedule_auto_update)
        self.input_text.setToolTip(STRINGS["tt_input_text"])
        
        # Adicionar ao layout
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_text, 1)
        
        self.splitter.addWidget(input_widget)
    
    def create_result_section(self):
        """Cria a seção de resultados (lado direito)"""
        result_widget = QWidget()
        result_widget.setObjectName("result_widget") # Added object name
        result_layout = QVBoxLayout(result_widget)
        result_layout.setSpacing(int(COLORS["margin_md"].replace('px','')))
        
        # Seletor de tempo máximo de pausa e botão de toggle (Layout ajustado)
        top_controls_layout = QHBoxLayout()
        
        break_label = QLabel(STRINGS["max_break_label"])
        break_label.setObjectName("break_label") # Set object name for stylesheet targeting
        
        self.max_break_input = QLineEdit()
        self.max_break_input.setValidator(QIntValidator(1, 999))
        self.max_break_input.setText(str(self.max_break_minutes))
        self.max_break_input.setMaximumWidth(60)
        self.max_break_input.editingFinished.connect(self.on_manual_input_finished)
        self.max_break_input.setToolTip(STRINGS["tt_max_break_input"])
        
        self.toggle_view_btn = QPushButton(STRINGS["btn_toggle_view"])
        self.toggle_view_btn.clicked.connect(self.toggle_view)
        self.toggle_view_btn.setToolTip(STRINGS["tt_toggle_view_btn"])

        top_controls_layout.addWidget(break_label)
        top_controls_layout.addWidget(self.max_break_input)
        top_controls_layout.addStretch()
        top_controls_layout.addWidget(self.toggle_view_btn)

        self.max_break_slider = QSlider(Qt.Horizontal)
        self.max_break_slider.setRange(1, 120)
        self.max_break_slider.setSingleStep(1)
        self.max_break_slider.setPageStep(5)
        self.max_break_slider.setTickPosition(QSlider.TicksBelow)
        self.max_break_slider.setTickInterval(5)
        self.max_break_slider.setValue(self.max_break_minutes)
        self.max_break_slider.valueChanged.connect(self.on_slider_value_changed)
        self.max_break_slider.setToolTip(STRINGS["tt_max_break_slider"])

        result_layout.addLayout(top_controls_layout)
        result_layout.addWidget(self.max_break_slider)

        # Work Blocks Label (ID para stylesheet)
        result_label = QLabel(STRINGS["label_result"])
        result_label.setObjectName("result_label") # Set object name for stylesheet targeting
        result_layout.addWidget(result_label)
        
        # Tabela de resultados
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels([
            STRINGS["col_version_start"],
            STRINGS["col_start_time"],
            STRINGS["col_version_end"],
            STRINGS["col_end_time"],
            STRINGS["col_duration"]
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setSelectionBehavior(QTableWidget.SelectItems) # Changed to SelectItems for flexible selection
        self.result_table.setSelectionMode(QTableWidget.ExtendedSelection) # Allow multiple item selection
        self.result_table.itemSelectionChanged.connect(self._update_selected_duration_sum) # Connect selection change signal
        self.result_table.setToolTip(STRINGS["tt_result_table"])
        
        # Botões (Process, Export, Copy, Exit)
        button_layout = QHBoxLayout()
        
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.copy_btn)
        button_layout.addWidget(self.exit_btn)
        button_layout.addStretch()
        
        # Label de total com destaque (ID para stylesheet)
        self.total_label = QLabel()
        self.total_label.setObjectName("total_label") # Set object name for stylesheet targeting
        self.total_label.setAlignment(Qt.AlignCenter)
        # Style will be applied by _generate_stylesheet
        self.total_label.setToolTip(STRINGS["tt_total_label"])

        # New label for selected duration sum
        self.selected_duration_label = QLabel()
        self.selected_duration_label.setObjectName("selected_duration_label")
        self.selected_duration_label.setAlignment(Qt.AlignCenter)
        self.selected_duration_label.setText(f"{STRINGS['selected_duration_label']} <b>00:00</b>") # Initial text
        
        # Adicionar ao layout
        result_layout.addWidget(self.result_table, 1)
        result_layout.addLayout(button_layout)
        result_layout.addWidget(self.total_label)
        result_layout.addWidget(self.selected_duration_label) # Add the new label
        
        self.splitter.addWidget(result_widget)
        self.splitter.setSizes([400, 600])  # Proporção inicial
    
    def setup_shortcuts(self):
        """Configura os atalhos de teclado para os botões."""
        # Atalho Ctrl+C para tabela (já existente)
        self.copy_shortcut_table = QShortcut(QKeySequence.Copy, self.result_table)
        self.copy_shortcut_table.activated.connect(self.copy_selection_to_clipboard)

        # Atalhos para os botões
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.process_btn.click)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.export_btn.click)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(self.copy_btn.click)
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self.toggle_view_btn.click)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.exit_btn.click)

    def on_slider_value_changed(self, value):
        """Atualiza o campo de texto quando o slider muda e processa os dados."""
        self.max_break_input.setText(str(value))
        self.max_break_minutes = value
        self.process_data()

    def on_manual_input_finished(self):
        """Atualiza o slider quando a entrada manual é finalizada e processa os dados."""
        try:
            value = int(self.max_break_input.text())
            # Limita o valor do input manual ao range do slider para sincronização visual
            if value < self.max_break_slider.minimum():
                value = self.max_break_slider.minimum()
            elif value > self.max_break_slider.maximum():
                value = self.max_break_slider.maximum()

            self.max_break_slider.setValue(value) # Atualiza o slider
            self.max_break_minutes = value
            self.process_data()
        except ValueError:
            # Se a entrada não for um número válido, reverte para o valor atual
            self.max_break_input.setText(str(self.max_break_minutes))
            self.show_error("Invalid input for 'Max Break'. Please enter a number.")
    
    def toggle_view(self):
        """Alterna entre visualização compacta e expandida"""
        self.compact_view = not self.compact_view
        if self.compact_view:
            self.toggle_view_btn.setText(STRINGS["compact_view"])
        else:
            self.toggle_view_btn.setText(STRINGS["expanded_view"])
        self.display_results()
    
    def schedule_auto_update(self):
        """Agenda uma atualização automática após alterações no texto"""
        # Verifica se há dados suficientes para processar
        # Apenas inicia o timer se o texto tiver pelo menos 3 linhas (para evitar processar entradas vazias ou incompletas)
        if self.input_text.toPlainText().strip().count('\n') >= 2:
            self.auto_update_timer.start()
        else:
            self.clear_results() # Clear results if input is too short/empty
            self.status_bar.showMessage(STRINGS["status_ready"])
            self.subtitle_label.setText(STRINGS["app_subtitle"]) # Reset subtitle when input is cleared
    
    def apply_dark_theme(self):
        """Aplica o tema escuro personalizado (chamado uma vez na inicialização)"""
        # O stylesheet será atualizado dinamicamente em resizeEvent
        self.setStyleSheet(self._generate_stylesheet(1.0)) # Initial scale factor of 1.0
        
        # Explicitly set text color for input_text to ensure consistency
        self.input_text.setTextColor(QColor(COLORS['text']))

        # Estilo alternado para linhas da tabela
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: #444;
                alternate-background-color: {COLORS['table_row_even']};
            }}
        """)

    def resizeEvent(self, event):
        """Overrides resize event to dynamically adjust font sizes and layout."""
        super().resizeEvent(event)
        current_width = self.width()
        current_height = self.height() # Get current height as well
        
        # Calculate scaling factor based on the smaller dimension to ensure elements fit
        # Using min ensures scaling is based on the more restrictive dimension
        scaling_factor = min(current_width / self.base_width, current_height / self.base_height)
        
        # Apply stylesheet immediately
        self.setStyleSheet(self._generate_stylesheet(scaling_factor))

        # Update main layout spacing based on scaled margin_md
        if self.main_layout: # Check if layout exists
            self.main_layout.setSpacing(int(self._scale_px_value(COLORS["margin_md"], scaling_factor).replace('px','')))
            # Scale main layout contents margins as well
            self.main_layout.setContentsMargins(
                int(self._scale_px_value(COLORS["padding_lg"], scaling_factor).replace('px','')),
                int(self._scale_px_value(COLORS['padding_lg'], scaling_factor).replace('px','')),
                int(COLORS["padding_lg"].replace('px','')),
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

        # Update specific widget styles that have unique background/border properties
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
        
        # The status bar message style is handled by the general QStatusBar rule in _generate_stylesheet
    
    # ==================== CORE LOGIC ====================
    def process_data(self):
        """
        Initiates data processing in a separate thread to prevent UI freezing.
        Manages UI state (disabling buttons, showing status).
        """
        # Stop any pending auto-update timer before starting new processing
        self.auto_update_timer.stop()

        # Prevent starting new processing if one is already ongoing
        if self.is_processing:
            return

        raw_text = self.input_text.toPlainText().strip()

        # If input is invalid or empty, handle immediately without starting a thread
        if not raw_text or raw_text.count('\n') < 2: # Check for at least 3 lines for a valid entry
            self.clear_results()
            self.status_bar.showMessage(STRINGS["status_ready"])
            self.subtitle_label.setText(STRINGS["app_subtitle"]) # Reset subtitle when input is cleared or invalid
            self._reset_ui_state_immediate() # Enable UI immediately
            return

        # Set processing flag and disable UI elements (except input_text)
        self.is_processing = True
        self.process_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.toggle_view_btn.setEnabled(False) # Disable toggle during processing
        self.max_break_slider.setEnabled(False)
        self.max_break_input.setEnabled(False)
        # self.input_text.setEnabled(True) # Keep input_text enabled

        # Start loading animation and update status bar style
        self.loading_frame = 0
        self.status_bar.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        self.loading_timer.start()

        # Only create and start worker if input is valid
        self.worker_thread = QThread()
        self.processor_worker = VersionProcessorWorker(raw_text, self.max_break_minutes)
        self.processor_worker.moveToThread(self.worker_thread)

        # Connect signals and slots
        self.worker_thread.started.connect(self.processor_worker.run)
        self.processor_worker.results.connect(self._handle_processing_results)
        self.processor_worker.error.connect(self._handle_processing_error)
        self.processor_worker.finished.connect(self._on_worker_finished) # Connect to unified finished handler

        # Start the thread
        self.worker_thread.start()

    def _handle_processing_results(self, work_blocks, total_time, current_filename):
        """
        Slot to receive and display processing results from the worker thread.
        """
        self.work_blocks = work_blocks
        self.total_time = total_time
        self.all_versions = self.processor_worker._all_versions # Get all parsed versions from worker
        self.current_filename = current_filename

        if self.current_filename:
            # Separate "WORKING ON:" from the filename
            self.subtitle_label.setText(f"WORKING ON: {self.current_filename.upper()}")
        else:
            self.subtitle_label.setText(STRINGS["app_subtitle"]) # Reset to default if no filename

        self.display_results()
        self.save_to_history(self.input_text.toPlainText().strip(), self.work_blocks, self.total_time)
        
        self.status_bar.showMessage(STRINGS["msg_success"])

    def _handle_processing_error(self, message):
        """
        Slot to handle errors reported by the worker thread.
        """
        self.show_error(message)

    def _on_worker_finished(self):
        """
        Unified handler for when the worker thread finishes, regardless of success or error.
        Ensures UI elements are re-enabled and resources are cleaned up.
        """
        self.loading_timer.stop() # Stop the loading animation
        self.status_bar.setStyleSheet("") # Reset status bar style
        self.status_bar.showMessage(STRINGS["status_ready"]) # Reset status message to ready or success

        self.process_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.toggle_view_btn.setEnabled(True)
        self.max_break_slider.setEnabled(True)
        self.max_break_input.setEnabled(True)
        self.input_text.setEnabled(True) # Ensure input text is always re-enabled
        
        # Clean up worker and thread resources
        # It's important to quit the thread before deleting the worker.
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait() # Wait for the thread to finish its event loop
            self.processor_worker.deleteLater()
            self.worker_thread.deleteLater()
            self.processor_worker = None
            self.worker_thread = None
        
        self.is_processing = False # Reset processing flag

    def _reset_ui_state_immediate(self):
        """
        Helper method to immediately re-enable UI elements without waiting for a thread.
        Used when input is invalid and no processing thread is started.
        """
        self.loading_timer.stop() # Ensure loading animation is stopped
        self.status_bar.setStyleSheet("") # Reset status bar style
        self.process_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.toggle_view_btn.setEnabled(True)
        self.max_break_slider.setEnabled(True)
        self.max_break_input.setEnabled(True)
        self.input_text.setEnabled(True)
        self.is_processing = False # Reset processing flag
        self.processor_worker = None
        self.worker_thread = None # Ensure these are explicitly None if no thread was started
    
    def _animate_loading_message(self):
        """Animates the loading message in the status bar."""
        self.status_bar.showMessage(self.loading_messages[self.loading_frame % len(self.loading_messages)])
        self.loading_frame += 1

    def parse_versions(self, text):
        """
        This method is now part of the worker. Calling it here is an error.
        It's kept as a placeholder but should not be directly called from main thread.
        """
        raise NotImplementedError("Parsing is now handled by the worker thread.")
    
    def extract_filename(self, text):
        """
        This method is now part of the worker. Calling it here is an error.
        It's kept as a placeholder but should not be directly called from main thread.
        """
        raise NotImplementedError("Filename extraction is now handled by the worker thread.")
    
    def calculate_work_blocks(self):
        """
        This method is now part of the worker. Calling it here is an error.
        It's kept as a placeholder but should not be directly called from main thread.
        """
        raise NotImplementedError("Work block calculation is now handled by the worker thread.")
    
    def calculate_block_duration(self, block):
        """
        This method is now part of the worker. Calling it here is an error.
        It's kept as a placeholder but should not be directly called from main thread.
        """
        raise NotImplementedError("Block duration calculation is now handled by the worker thread.")
    
    # ==================== UI UPDATES ====================
    def display_results(self):
        """Displays the results in the table with the selected view"""
        if self.compact_view:
            self.display_compact_view()
        else:
            self.display_expanded_view()
        self._update_selected_duration_sum() # Update selected sum after table content changes
    
    def display_compact_view(self):
        """Displays only the work blocks (consolidated view) from most recent to oldest."""
        # Sort work blocks from most recent to oldest
        # The most recent block is the one with the latest 'end' time.
        # Since work_blocks is already generated in chronological ascending order, just reverse the list.
        sorted_work_blocks_desc = sorted(self.work_blocks, key=lambda x: x['end']['time'], reverse=True)

        self.result_table.setRowCount(len(sorted_work_blocks_desc))
        
        for row, block in enumerate(sorted_work_blocks_desc):
            # Start version
            start_version = block['start']['name']
            start_time = block['start']['time'].strftime("%H:%M")
            
            # End version
            end_version = block['end']['name']
            end_time = block['end']['time'].strftime("%H:%M")
            
            # Formatted duration (of the complete block)
            duration_str = self.format_duration(block['duration'])
            
            # Create items
            items = [
                QTableWidgetItem(start_version),
                QTableWidgetItem(start_time),
                QTableWidgetItem(end_version),
                QTableWidgetItem(end_time),
                QTableWidgetItem(duration_str)
            ]
            
            # Centralizar conteúdo
            for item in items:
                item.setTextAlignment(Qt.AlignCenter)
            
            # Insere na tabela
            for col, item in enumerate(items):
                self.result_table.setItem(row, col, item)
        
        # Atualiza total
        total_str = self.format_duration(self.total_time)
        self.total_label.setText(
            f"{STRINGS['total_label']} <b>{total_str}</b>"
        )
    
    def display_expanded_view(self):
        """Displays all version transitions with duration and indication of ignored intervals."""
        if not self.all_versions or len(self.all_versions) < 2:
            self.result_table.setRowCount(0)
            self.total_label.setText(f"{STRINGS['total_label']} <b>00:00</b>")
            return

        # Sort versions from newest to oldest to match the desired output format
        sorted_versions_desc = sorted(self.all_versions, key=lambda x: x['time'], reverse=True)
        
        self.result_table.setRowCount(len(sorted_versions_desc) - 1) # One row for each transition
        
        row_index = 0
        for i in range(len(sorted_versions_desc) - 1):
            curr_version = sorted_versions_desc[i]
            prev_version = sorted_versions_desc[i+1] # The chronologically previous version

            curr_time_dt = datetime.combine(datetime.today(), curr_version['time'])
            prev_time_dt = datetime.combine(datetime.today(), prev_version['time'])

            # Adjustment for midnight rollover (if the previous version is "after" the current one on the same day)
            if prev_time_dt > curr_time_dt:
                prev_time_dt -= timedelta(days=1) # Assume it's from the previous day

            time_diff = curr_time_dt - prev_time_dt
            
            duration_str = self.format_duration(time_diff)
            
            # Add "IGNORED" indication if the interval is too large
            if time_diff.total_seconds() / 60 > self.max_break_minutes:
                duration_str += f" (IGNORED - Break > {self.max_break_minutes} min)"
            
            items = [
                QTableWidgetItem(curr_version['name']),
                QTableWidgetItem(curr_version['time'].strftime("%H:%M")),
                QTableWidgetItem(prev_version['name']),
                QTableWidgetItem(prev_version['time'].strftime("%H:%M")),
                QTableWidgetItem(duration_str)
            ]
            
            for item in items:
                item.setTextAlignment(Qt.AlignCenter)
                # Apply alternating colors for rows
                if row_index % 2 == 0:
                     item.setBackground(QColor(COLORS['table_row_even']))
                else:
                    item.setBackground(QColor(COLORS['table_row_odd']))
            
            for col, item in enumerate(items):
                self.result_table.setItem(row_index, col, item)
            
            row_index += 1
        
        # Update total (the active total is the same for both views)
        total_str = self.format_duration(self.total_time)
        self.total_label.setText(
            f"{STRINGS['total_label']} <b>{total_str}</b>"
        )
    
    def format_duration(self, duration):
        """Formats timedelta to HH:MM"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{hours:02d}:{minutes:02d}"

    def _parse_duration_string(self, duration_str):
        """Parses a duration string (HH:MM) into a timedelta object."""
        try:
            # Remove any " (IGNORED - ...)" part if present
            clean_duration_str = duration_str.split(' (')[0].strip()
            
            parts = clean_duration_str.split(':')
            if len(parts) == 2:
                hours = int(parts[0])
                minutes = int(parts[1])
                return timedelta(hours=hours, minutes=minutes)
        except ValueError:
            return timedelta(0) # Return zero timedelta for invalid formats
        return timedelta(0)
    
    def _update_selected_duration_sum(self):
        """
        Calculates and displays the sum of durations from selected cells in the result table.
        """
        selected_items = self.result_table.selectedItems()
        sum_duration = timedelta()
        
        # Find the column index for 'DURATION'
        duration_col_index = -1
        for i in range(self.result_table.columnCount()):
            if self.result_table.horizontalHeaderItem(i).text() == STRINGS["col_duration"]:
                duration_col_index = i
                break

        if duration_col_index == -1: # Should not happen if headers are set correctly
            self.selected_duration_label.setText(f"{STRINGS['selected_duration_label']} <b>00:00</b>")
            return

        processed_rows = set() # To avoid double-counting if an entire row is selected

        for item in selected_items:
            if item.column() == duration_col_index and item.row() not in processed_rows:
                duration_text = item.text()
                sum_duration += self._parse_duration_string(duration_text)
                processed_rows.add(item.row()) # Mark row as processed

        self.selected_duration_label.setText(
            f"{STRINGS['selected_duration_label']} <b>{self.format_duration(sum_duration)}</b>"
        )
        if sum_duration == timedelta(0):
            self.selected_duration_label.setText(f"{STRINGS['selected_duration_label']} <b>00:00</b>")

    def copy_total_to_clipboard(self):
        """Copies the total time value to the clipboard (HH:MM only)"""
        total_text = self.total_label.text()
        # Extract only the HH:MM value
        if "<b>" in total_text:
            total_value = total_text.split("<b>")[1].split("</b>")[0]
        else:
            # Fallback if format changes (less robust, but tries to get the last field)
            total_value = total_text.split(":")[-1].strip()
        
        clipboard = QApplication.clipboard()
        clipboard.setText(total_value)
        self.status_bar.showMessage(STRINGS["msg_copied"]) # Use status_bar directly
    
    def copy_selection_to_clipboard(self):
        """Copies the table selection to the clipboard"""
        selected_ranges = self.result_table.selectedRanges()
        if not selected_ranges:
            return
        
        clipboard_text = ""
        
        # Get headers for copying (optional, but good for CSV/table)
        header_items = [self.result_table.horizontalHeaderItem(i).text() for i in range(self.result_table.columnCount())]
        clipboard_text += "\t".join(header_items) + "\n" # Add headers
        
        # Get selected cells content
        rows = sorted(list(set(item.row() for item in self.result_table.selectedItems())))
        cols = sorted(list(set(item.column() for item in self.result_table.selectedItems())))

        for r in rows:
            row_data = []
            for c in cols: # Only copy selected columns within the selected rows
                item = self.result_table.item(r, c)
                row_data.append(item.text() if item else "")
            clipboard_text += "\t".join(row_data) + "\n"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text.strip())
        self.status_bar.showMessage("📋 Selection copied to clipboard!") # Use status_bar directly
    
    # ==================== EXPORT/HISTORY ====================
    def export_data(self):
        """Exports data to CSV or TXT"""
        options = QFileDialog.Option()
        default_name = f"{self.current_filename}_work_blocks" if self.current_filename else "work_blocks"
        
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            STRINGS["EXPORT_DATA"], # Uppercase
            default_name,
            f"{STRINGS['export_csv']};;{STRINGS['export_txt']}",
            options=options
        )
        
        if not file_name:
            return
        
        if selected_filter == STRINGS["export_csv"]:
            self.export_to_csv(file_name)
        else:
            self.export_to_txt(file_name)
    
    def export_to_csv(self, file_path):
        """Exports data to CSV format"""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    STRINGS["col_version_start"],
                    STRINGS["col_start_time"],
                    STRINGS["col_version_end"],
                    STRINGS["col_end_time"],
                    STRINGS["col_duration"]
                ])
                
                for row in range(self.result_table.rowCount()):
                    row_data = []
                    for col in range(5):
                        item = self.result_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
                
                # Add total
                total_text = self.total_label.text().split(">")[-1].replace("</b", "")
                writer.writerow(["", "", "", "TOTAL", total_text.strip()])
                
            QMessageBox.information(
                self,
                STRINGS["EXPORT_SUCCESSFUL"],
                f"DATA EXPORTED TO CSV:\n{file_path}"
            )
        except Exception as e:
            self.show_error(f"{STRINGS['EXPORT_FAILED']}: {str(e)}")
    
    def export_to_txt(self, file_path):
        """Exports data to TXT format"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(f"{STRINGS['col_version_start']:<25}{STRINGS['col_start_time']:<10}{STRINGS['col_version_end']:<25}{STRINGS['col_end_time']:<10}{STRINGS['col_duration']:>10}\n")
                file.write("-" * 80 + "\n")
                
                for row in range(self.result_table.rowCount()):
                    row_data = []
                    for col in range(5):
                        item = self.result_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    file.write(f"{row_data[0]:<25}{row_data[1]:<10}{row_data[2]:<25}{row_data[3]:<10}{row_data[4]:>10}\n")
                
                # Add total
                total_text = self.total_label.text().split(">")[-1].replace("</b", "").strip()
                file.write("\n" + "-" * 80 + "\n")
                file.write(f"{'TOTAL':<60}{total_text:>20}")
                
            QMessageBox.information(
                self,
                STRINGS["EXPORT_SUCCESSFUL"],
                f"DATA EXPORTED TO TXT:\n{file_path}"
            )
        except Exception as e:
            self.show_error(f"{STRINGS['EXPORT_FAILED']}: {str(e)}")
    
    def save_to_history(self, raw_input, work_blocks, total_time):
        """Saves the current session to history"""
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as file:
                    history = json.load(file)
            except:
                history = []
        
        # Limit history to 50 entries
        if len(history) >= 50:
            history = history[-49:]
        
        # Add new entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": raw_input,
            "blocks": [
                {
                    "start": b['start']['name'],
                    "start_time": b['start']['time'].strftime("%H:%M"),
                    "end": b['end']['name'],
                    "end_time": b['end']['time'].strftime("%H:%M"),
                    "duration": str(b['duration'])
                } for b in work_blocks
            ],
            "total": str(total_time)
        }
        
        history.append(entry)
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as file:
                json.dump(history, file, indent=2)
        except:
            pass
    
    def load_history(self):
        """Loads history from file"""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as file:
                history = json.load(file)
                if history:
                    # Load the last item
                    last_entry = history[-1]
                    self.input_text.setText(last_entry["input"])
        except:
            pass
    
    # ==================== UTILITIES ====================
    def clear_results(self):
        """Clears current results"""
        self.result_table.setRowCount(0)
        self.total_label.clear()
        self.selected_duration_label.clear() # Clear the new label as well
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
    
    def show_error(self, message):
        """Displays an error message"""
        self.loading_timer.stop() # Stop animation on error
        self.status_bar.setStyleSheet(f"color: {COLORS['error']};") # Style status_bar directly
        self.status_bar.showMessage(message) 
        self.clear_results()
        
        # Temporary visual effect
        QApplication.processEvents()
        QTimer.singleShot(3000, lambda: self.status_bar.setStyleSheet("")) # Reset style after 3 seconds
    
    def closeEvent(self, event):
        """Saves settings on close"""
        self.settings.setValue("window_geometry", self.saveGeometry()) # Save window position and size
        self.settings.setValue("splitter_sizes", self.splitter.sizes())
        
        # The worker and thread are scheduled for deletion via deleteLater()
        # when processing finishes. During application shutdown, PySide's
        # event loop cleanup generally handles remaining QObjects.
        # Explicitly quitting/waiting here can lead to race conditions or
        # accessing already deleted C++ objects, causing RuntimeErrors.
        # Therefore, this block is removed for safer shutdown.
        
        super().closeEvent(event)

# ==================== APPLICATION START ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = VersionTimeTracker()
    
    # Restore window geometry (position and size)
    if window.settings.contains("window_geometry"):
        window.restoreGeometry(window.settings.value("window_geometry"))
    
    # Restore splitter size
    if window.settings.contains("splitter_sizes"):
        sizes = window.settings.value("splitter_sizes")
        window.splitter.setSizes([int(size) for size in sizes])
    
    window.show()
    sys.exit(app.exec())
