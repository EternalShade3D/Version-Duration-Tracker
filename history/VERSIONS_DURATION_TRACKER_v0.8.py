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
from PySide6.QtCore import Qt, QSettings, QTimer
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

    # 🔠 Font sizes (Adjusted to be smaller)
    "font_size_small": 9,
    "font_size_medium": 11,
    "font_size_large": 13,
    "font_size_total": 14,
    "font_size_subtitle": 14,
    "font_size_title": 24,   # Título destacado, mas não exagerado


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
    "app_title": "▶ VERSION TIME TRACKER V7",
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
    "status_processing": "⏳ WORKING...",

    # 🧱 Table headers
    "col_version": "🔢 VERSION",
    "col_time": "⏱ TIME",
    "col_version_start": "🟩 START VERSION",
    "col_start_time": "🕒 START TIME",
    "col_version_end": "🏁 END VERSION",
    "col_end_time": "🕓 END TIME",
    "col_duration": "🕘 DURATION",

    # 🧮 Summary
    "total_label": "⏱ TOTAL ACTIVE TIME:",
    "history_file": "version_tracker_history.json",
    "max_break_label": "⏸ MAX BREAK (MINUTES):",
    "compact_view": "📦 COMPACT VIEW",
    "expanded_view": "📂 EXPANDED VIEW",

    # 💡 Tooltips — ADHD-friendly
    "tt_input_text": "📥 Paste your Blender version list here. Each item should include version title, filename, time (HH:MM), and author — all separated by blank lines.",
    "tt_process_btn": "⚙️ Process everything to calculate active work blocks. Shortcut: Ctrl+P",
    "tt_max_break_slider": "⏸ Set the max break allowed between versions (in minutes). Used to group versions into same block.",
    "tt_max_break_input": "⌨️ Type the max break manually (in minutes).",
    "tt_result_table": "📊 Shows the grouped work blocks. Compact = summary | Expanded = full version list.",
    "tt_export_btn": "📤 Export the table to CSV or TXT. Shortcut: Ctrl+E",
    "tt_copy_btn": "📋 Copy total active time to clipboard. Shortcut: Ctrl+Shift+C",
    "tt_toggle_view_btn": "🔄 Switch between compact/expanded view. Shortcut: Ctrl+T",
    "tt_total_label": "⏱ This is the total active time (skips long breaks).",
    "tt_exit_btn": "🚪 Close the program. Shortcut: Ctrl+Q",

    # New strings for QMessageBox titles/messages
    "EXPORT_SUCCESSFUL": "✅ EXPORT SUCCESSFUL",
    "EXPORT_FAILED": "❗ EXPORT FAILED",
}

# ==================== MAIN WINDOW ====================
class VersionTimeTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(STRINGS["app_title"])
        self.setMinimumSize(800, 600) # Reduced minimum size for more flexibility
        
        # Configurações
        self.settings = QSettings("VersionTimeTracker")
        self.max_break_minutes = 10  # default
        self.history_file = Path(STRINGS["history_file"])
        self.current_filename = ""
        self.compact_view = True
        self.work_blocks = []
        self.total_time = timedelta()
        self.all_versions = []  # Armazena todas as versões parseadas
        
        # Widgets principais
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(int(COLORS["margin_md"].replace('px','')))
        self.main_layout.setContentsMargins(int(COLORS["padding_lg"].replace('px','')), int(COLORS["padding_lg"].replace('px','')), int(COLORS["padding_lg"].replace('px','')), int(COLORS["padding_lg"].replace('px','')))
        
        # Cabeçalho com título e subtítulo
        self.create_header_section()
        
        # Timer para atualização automática
        self.auto_update_timer = QTimer()
        self.auto_update_timer.setSingleShot(True)
        self.auto_update_timer.timeout.connect(self.process_data)
        self.auto_update_timer.setInterval(1500)  # 1.5 segundos
        
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
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(STRINGS["status_ready"])
        
        # Aplicar estilo
        self.apply_dark_theme()
        self.load_history()
        
        # Configurar atalhos de teclado (novos e ajustados)
        self.setup_shortcuts()
    
    def create_header_section(self):
        """Cria a seção de cabeçalho com título e subtítulo"""
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            background-color: {COLORS['header_bg']};
            border-radius: {COLORS['border_radius_md']};
            border: none;
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(int(COLORS["padding_lg"].replace('px','')), int(COLORS["padding_lg"].replace('px','')), int(COLORS["padding_lg"].replace('px','')), int(COLORS["padding_lg"].replace('px','')))
        header_layout.setSpacing(int(COLORS["margin_sm"].replace('px','')))
        
        # Título principal
        title_label = QLabel(STRINGS["app_title"])
        title_label.setFont(QFont(COLORS["font_family"], COLORS["font_size_title"], QFont.Bold))
        title_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: {COLORS['font_size_title']}pt;")
        title_label.setAlignment(Qt.AlignLeft)
        
        # Subtítulo (para nome do arquivo) - Agora dentro de um QFrame para destaque
        self.subtitle_frame = QFrame()
        self.subtitle_frame.setStyleSheet(f"""
            background-color: {COLORS['table_header']}; /* Use a cor de cabeçalho da tabela para contraste */
            border-radius: {COLORS['border_radius_sm']};
            padding: {COLORS['padding_sm']} {COLORS['padding_md']}; /* Padding interno */
            margin-top: {COLORS['margin_sm']}; /* Espaçamento do título */
            border: none; /* REMOVED BORDER/OUTLINE AS REQUESTED */
        """)
        subtitle_layout = QHBoxLayout(self.subtitle_frame)
        subtitle_layout.setContentsMargins(0, 0, 0, 0) # Remover margens internas do layout
        
        self.subtitle_label = QLabel(STRINGS["app_subtitle"])
        self.subtitle_label.setFont(QFont(COLORS["font_family"], COLORS["font_size_subtitle"]))
        self.subtitle_label.setStyleSheet(f"color: #aaaaaa; font-size: {COLORS['font_size_subtitle']}pt;")
        self.subtitle_label.setAlignment(Qt.AlignLeft)
        
        subtitle_layout.addWidget(self.subtitle_label)
        subtitle_layout.addStretch() # Empurra o label para a esquerda

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.subtitle_frame) # Adiciona o frame do subtítulo
        
        self.main_layout.addWidget(header_frame)
    
    def create_input_section(self):
        """Cria a seção de entrada de dados (lado esquerdo)"""
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(int(COLORS["margin_md"].replace('px','')))
        
        # Label
        input_label = QLabel(STRINGS["label_input"])
        input_label.setFont(QFont(COLORS["font_family"], COLORS["font_size_large"], QFont.Bold))
        
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
        result_layout = QVBoxLayout(result_widget)
        result_layout.setSpacing(int(COLORS["margin_md"].replace('px','')))
        
        # Seletor de tempo máximo de pausa e botão de toggle (Layout ajustado)
        top_controls_layout = QHBoxLayout()
        
        break_label = QLabel(STRINGS["max_break_label"])
        break_label.setFont(QFont(COLORS["font_family"], COLORS["font_size_medium"]))
        
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
        top_controls_layout.addStretch() # Empurra o botão de toggle para a direita
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

        result_layout.addLayout(top_controls_layout) # Adiciona o layout com label, input e toggle
        result_layout.addWidget(self.max_break_slider) # Adiciona o slider abaixo

        # Work Blocks Label (movido para cá)
        result_label = QLabel(STRINGS["label_result"])
        result_label.setFont(QFont(COLORS["font_family"], COLORS["font_size_large"], QFont.Bold))
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
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setToolTip(STRINGS["tt_result_table"])
        
        # Botões (Process, Export, Copy, Exit)
        button_layout = QHBoxLayout()
        
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.copy_btn)
        button_layout.addWidget(self.exit_btn)
        button_layout.addStretch()
        
        # Label de total com destaque
        self.total_label = QLabel()
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setFont(QFont(COLORS["font_family"], COLORS["font_size_total"], QFont.Bold))
        self.total_label.setStyleSheet(f"""
            background-color: {COLORS['table_header']};
            padding: {COLORS['padding_lg']};
            border-radius: {COLORS['border_radius_md']};
            border: {COLORS['border_width_thick']} solid {COLORS['highlight']};
            color: {COLORS['highlight']};
            font-size: {COLORS['font_size_total']}pt;
        """)
        self.total_label.setToolTip(STRINGS["tt_total_label"])
        
        # Adicionar ao layout
        result_layout.addWidget(self.result_table, 1)
        result_layout.addLayout(button_layout)
        result_layout.addWidget(self.total_label)
        
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
        self.auto_update_timer.start()
    
    def apply_dark_theme(self):
        """Aplica o tema escuro personalizado"""
        # Background geral
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
                font-family: '{COLORS['font_family']}';
            }}
            QTextEdit {{
                background-color: {COLORS['table_header']};
                border: {COLORS['border_width_thick']} solid {COLORS['accent']}; /* Thicker border for input area */
                border-radius: {COLORS['border_radius_sm']};
                font-size: {COLORS['font_size_medium']}pt;
                padding: {COLORS['padding_md']} {COLORS['padding_lg']}; /* Added lateral padding */
            }}
            QTableWidget {{
                background-color: {COLORS['table_header']};
                border: {COLORS['border_width_thin']} solid {COLORS['accent']};
                border-radius: {COLORS['border_radius_sm']};
                font-size: {COLORS['font_size_medium']}pt;
            }}
            QHeaderView::section {{
                background-color: {COLORS['table_header']};
                padding: {COLORS['padding_sm']};
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: {COLORS['padding_sm']};
            }}
            QPushButton {{
                background-color: {COLORS['button']};
                border: none;
                border-bottom: {COLORS['border_width_thick']} solid {COLORS['accent']};
                border-radius: {COLORS['border_radius_sm']};
                padding: {COLORS['padding_md']} {COLORS['padding_lg']};
                font-weight: bold;
                min-width: 100px;
                font-size: {COLORS['font_size_medium']}pt;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['accent']};
                border-bottom: {COLORS['border_width_thin']} solid {COLORS['accent']};
                padding-top: {int(COLORS['padding_md'].replace('px','')) + 1}px;
                padding-bottom: {int(COLORS['padding_md'].replace('px','')) - 1}px;
                padding-left: {COLORS['padding_lg']};
                padding-right: {COLORS['padding_lg']};
            }}
            QLabel {{
                font-size: {COLORS['font_size_medium']}pt;
            }}
            QStatusBar {{
                font-size: {COLORS['font_size_small']}pt;
                color: #aaa;
            }}
            QSlider::groove:horizontal {{
                border: {COLORS['border_width_thin']} solid {COLORS['accent']};
                height: 8px;
                background: {COLORS['button']};
                margin: 2px 0;
                border-radius: {COLORS['border_radius_sm']};
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['accent']};
                border: {COLORS['border_width_thin']} solid {COLORS['text']};
                width: 18px;
                margin: -5px 0;
                border-radius: {COLORS['border_radius_lg']};
            }}
            QSlider::add-page:horizontal {{
                background: {COLORS['accent']};
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['button']};
            }}
            QLineEdit {{
                background-color: {COLORS['table_header']};
                border: {COLORS['border_width_thin']} solid {COLORS['accent']};
                border-radius: {COLORS['border_radius_sm']};
                padding: {COLORS['padding_sm']};
                font-size: {COLORS['font_size_medium']}pt;
                color: {COLORS['text']};
            }}
        """)
        
        # Estilo alternado para linhas da tabela
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setStyleSheet(f"""
            QTableWidget {{
                gridline-color: #444;
                alternate-background-color: {COLORS['table_row_even']};
            }}
        """)
    
    # ==================== CORE LOGIC ====================
    def process_data(self):
        """Processa os dados de entrada e calcula os blocos de trabalho"""
        self.status_bar.showMessage(STRINGS["status_processing"])
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        raw_text = self.input_text.toPlainText().strip()
        
        if not raw_text:
            self.clear_results()
            return
        
        try:
            # Parse das versões
            self.all_versions = self.parse_versions(raw_text)
            
            # Tentar extrair nome do arquivo
            filename = self.extract_filename(raw_text)
            if filename:
                self.current_filename = filename
                # Atualiza o texto do subtítulo dentro do frame
                self.subtitle_label.setText(f"WORKING ON: {filename.upper()}")
            
            # Agrupamento em blocos
            self.work_blocks, self.total_time = self.calculate_work_blocks()
            
            # Exibição dos resultados
            self.display_results()
            self.save_to_history(raw_text, self.work_blocks, self.total_time)
            
            self.status_bar.showMessage(STRINGS["msg_success"])
            self.export_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            
        except Exception as e:
            self.show_error(f"{STRINGS['msg_invalid']}: {str(e)}")
    
    def parse_versions(self, text):
        """Converte texto em lista de versões com timestamps"""
        versions = []
        blocks = text.split('\n\n')  # Separa por blocos vazios

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if len(lines) < 2:  # Pelo menos versão e hora
                continue
                
            # Identificar nome da versão (primeira linha que começa com "Version" ou "Current")
            version_name = None
            for line in lines:
                if line.lower().startswith("version") or line.lower().startswith("current"):
                    version_name = line
                    break
            
            if not version_name:
                continue
                
            # Procurar linha com formato de hora (HH:MM)
            time_str = None
            for line in lines:
                if len(line) == 5 and line[2] == ':':  # Formato básico de hora
                    try:
                        # Tenta converter para validar
                        datetime.strptime(line, "%H:%M")
                        time_str = line
                        break
                    except ValueError:
                        continue
                # Tenta também formatos com 4 dígitos (ex: 9:15 -> 09:15)
                elif len(line) == 4 and line[1] == ':':
                    try:
                        # Tenta converter, preenchendo com zero à esquerda
                        time_obj = datetime.strptime(f"0{line}", "%H:%M")
                        time_str = f"0{line}"
                        break
                    except ValueError:
                        continue
            
            if not time_str:
                continue
                
            try:
                # Se a string de tempo tem 4 caracteres, convertemos para 5 com zero à esquerda
                if len(time_str) == 4:
                    time_str = '0' + time_str
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                versions.append({
                    'name': version_name,
                    'time': time_obj
                })
            except ValueError:
                continue
        
        if not versions:
            raise ValueError("No valid versions found")
        
        return versions
    
    def extract_filename(self, text):
        """Tenta extrair o nome do arquivo do texto"""
        blocks = text.split('\n\n')
        if blocks:
            first_block = blocks[0]
            lines = first_block.splitlines()
            if len(lines) > 1:
                # Segunda linha é geralmente o nome do arquivo
                filename_line = lines[1].strip()
                if '.' in filename_line and 'blend' in filename_line: # Adicionado checagem por ".blend" para maior robustez
                    return filename_line.split('.')[0]
        return ""
    
    def calculate_work_blocks(self):
        """Agrupa versões em blocos de trabalho contínuos e calcula a duração total ativa."""
        if len(self.all_versions) < 2:
            raise ValueError("At least two versions needed")
        
        # Ordenar versões por tempo (mais antigo primeiro)
        # O dado de entrada é do mais novo para o mais antigo, então precisamos inverter
        # a ordem para processar do mais antigo para o mais novo
        sorted_versions = sorted(self.all_versions, key=lambda x: x['time'])
        
        work_blocks = []
        current_block_versions = []
        total_active_time = timedelta()
        
        if not sorted_versions:
            return [], timedelta()
        
        current_block_versions.append(sorted_versions[0])
        
        for i in range(1, len(sorted_versions)):
            prev_version = sorted_versions[i-1]
            curr_version = sorted_versions[i]
            
            prev_time_dt = datetime.combine(datetime.today(), prev_version['time'])
            curr_time_dt = datetime.combine(datetime.today(), curr_version['time'])
            
            # Se a versão atual é anterior à anterior (pulou a meia-noite), assume que é no dia seguinte
            # Isso é crucial para cálculos de duração que atravessam a meia-noite
            if curr_time_dt < prev_time_dt:
                curr_time_dt += timedelta(days=1)

            time_diff = curr_time_dt - prev_time_dt
            
            if time_diff.total_seconds() <= self.max_break_minutes * 60:
                current_block_versions.append(curr_version)
                total_active_time += time_diff # Adiciona a duração VÁLIDA
            else:
                # Intervalo grande, finaliza o bloco atual e inicia um novo
                if len(current_block_versions) > 0: # Garante que há versões para formar um bloco
                    # Usa a nova função para calcular a duração ativa do bloco
                    block_active_duration = self.calculate_block_duration(current_block_versions)
                    
                    work_blocks.append({
                        'start': current_block_versions[0],
                        'end': current_block_versions[-1],
                        'versions': current_block_versions[:],
                        'duration': block_active_duration # Agora é a duração ativa do bloco
                    })
                current_block_versions = [curr_version] # Inicia um novo bloco com a versão atual
        
        # Adiciona o último bloco após o loop
        if len(current_block_versions) > 0:
            # Usa a nova função para calcular a duração ativa do último bloco
            block_active_duration = self.calculate_block_duration(current_block_versions)
            work_blocks.append({
                'start': current_block_versions[0],
                'end': current_block_versions[-1],
                'versions': current_block_versions[:],
                'duration': block_active_duration # Agora é a duração ativa do bloco
            })
            
        return work_blocks, total_active_time
    
    def calculate_block_duration(self, block):
        """Calculates the total duration of a work block considering only valid intervals"""
        if len(block) < 2:
            return timedelta()
            
        total_duration = timedelta()
        sorted_block = sorted(block, key=lambda x: x['time']) # Ensures the block is sorted by time
        
        for i in range(1, len(sorted_block)):
            prev_time = datetime.combine(datetime.today(), sorted_block[i-1]['time'])
            curr_time = datetime.combine(datetime.today(), sorted_block[i]['time'])
            
            # Adjustment for midnight rollover within the block
            if curr_time < prev_time:
                curr_time += timedelta(days=1)

            time_diff = curr_time - prev_time
            
            # If the interval is valid (<= max_break), add to duration
            if time_diff.total_seconds() / 60 <= self.max_break_minutes:
                total_duration += time_diff
        
        return total_duration
    
    # ==================== UI UPDATES ====================
    def display_results(self):
        """Displays the results in the table with the selected view"""
        if self.compact_view:
            self.display_compact_view()
        else:
            self.display_expanded_view()
    
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
        self.status_bar.showMessage(STRINGS["msg_copied"])
    
    def copy_selection_to_clipboard(self):
        """Copies the table selection to the clipboard"""
        selected_ranges = self.result_table.selectedRanges()
        if not selected_ranges:
            return
        
        clipboard_text = ""
        
        # Get headers for copying (optional, but good for CSV/table)
        header_items = [self.result_table.horizontalHeaderItem(i).text() for i in range(self.result_table.columnCount())]
        clipboard_text += "\t".join(header_items) + "\n" # Add headers
        
        for r in range(selected_ranges[0].topRow(), selected_ranges[0].bottomRow() + 1):
            row_data = []
            for c in range(self.result_table.columnCount()): # Copy all columns of the selected row
                item = self.result_table.item(r, c)
                row_data.append(item.text() if item else "")
            clipboard_text += "\t".join(row_data) + "\n"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text.strip())
        self.status_bar.showMessage("📋 Selection copied to clipboard!")
    
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
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
    
    def show_error(self, message):
        """Displays an error message"""
        self.status_bar.showMessage(message)
        self.clear_results()
        
        # Temporary visual effect
        self.status_bar.setStyleSheet(f"color: {COLORS['error']};")
        QApplication.processEvents()
        QTimer.singleShot(3000, lambda: self.status_bar.setStyleSheet(""))
    
    def closeEvent(self, event):
        """Saves settings on close"""
        self.settings.setValue("window_size", self.size())
        self.settings.setValue("splitter_sizes", self.splitter.sizes())
        super().closeEvent(event)

# ==================== APPLICATION START ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = VersionTimeTracker()
    
    # Restore window size
    if window.settings.contains("window_size"):
        window.resize(window.settings.value("window_size"))
    
    # Restore splitter size
    if window.settings.contains("splitter_sizes"):
        sizes = window.settings.value("splitter_sizes")
        window.splitter.setSizes([int(size) for size in sizes])
    
    window.show()
    sys.exit(app.exec())
