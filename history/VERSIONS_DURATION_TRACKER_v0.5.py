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
    "bg": "#1e1e1e",
    "text": "#ffffff",
    "accent": "#00adb5",
    "button": "#393e46",
    "error": "#ff2e63",
    "table_header": "#252525",
    "table_row_even": "#2a2a2a",
    "table_row_odd": "#242424",
    "header_bg": "#151515",
    "highlight": "#ffcc00",

    # Global styles
    "font_family": "Segoe UI", # Consistent font family
    "font_size_small": "11px",
    "font_size_medium": "12px",
    "font_size_large": "14px",
    "font_size_title": "28px",
    "font_size_subtitle": "14px",
    "font_size_total": "16px",
    "border_radius_sm": "4px",
    "border_radius_md": "8px",
    "border_radius_lg": "9px", # For slider handle
    "border_width_thin": "1px",
    "border_width_thick": "2px",
}

STRINGS = {
    "app_title": "🧮 Version Time Tracker",
    "app_subtitle": "Blender Version Time Calculator",
    "label_input": "📋 Paste your version list:",
    "btn_process": "⚙️ Process",
    "btn_export": "💾 Export",
    "btn_copy": "📋 Copy Total",
    "btn_toggle_view": "🔍 Toggle View",
    "label_result": "📊 Work Blocks",
    "msg_invalid": "⚠️ Invalid or incomplete data detected",
    "msg_success": "✅ Processed successfully!",
    "msg_copied": "📋 Total copied to clipboard!",
    "export_csv": "CSV Files (*.csv)",
    "export_txt": "Text Files (*.txt)",
    "status_ready": "Ready",
    "status_processing": "Processing...",
    "col_version": "Version",
    "col_time": "Time",
    "col_version_start": "Start Version",
    "col_start_time": "Start Time",
    "col_version_end": "End Version",
    "col_end_time": "End Time",
    "col_duration": "Duration",
    "total_label": "TOTAL ACTIVE TIME:",
    "history_file": "version_tracker_history.json",
    "max_break_label": "Max Break (minutes):",
    "compact_view": "Compact View",
    "expanded_view": "Expanded View",
    # Tooltips
    "tt_input_text": "Cole aqui a lista de versões do Blender. Cada versão deve ter 'Version X', nome do arquivo, hora (HH:MM) e autor, separados por linhas em branco.",
    "tt_process_btn": "Processa os dados de versão colados para calcular os blocos de tempo ativo.",
    "tt_max_break_slider": "Defina o tempo máximo de pausa (em minutos) entre as versões para que sejam consideradas parte do mesmo bloco de trabalho.",
    "tt_max_break_input": "Insira manualmente o tempo máximo de pausa (em minutos).",
    "tt_result_table": "Exibe os blocos de trabalho calculados. Use a visualização compacta para um resumo ou expandida para detalhes.",
    "tt_export_btn": "Exporta os resultados da tabela para um arquivo CSV ou TXT.",
    "tt_copy_btn": "Copia o tempo total ativo para a área de transferência.",
    "tt_toggle_view_btn": "Alterna entre a visualização compacta (blocos consolidados) e a visualização expandida (todas as versões com marcações de bloco).",
    "tt_total_label": "O tempo total ativo, excluindo pausas maiores que o limite definido."
}

# ==================== MAIN WINDOW ====================
class VersionTimeTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(STRINGS["app_title"])
        self.setMinimumSize(1100, 750)
        
        # Configurações
        self.settings = QSettings("DeepSeek", "VersionTimeTracker")
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
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Cabeçalho com título e subtítulo
        self.create_header_section()
        
        # Timer para atualização automática
        self.auto_update_timer = QTimer()
        self.auto_update_timer.setSingleShot(True)
        self.auto_update_timer.timeout.connect(self.process_data)
        self.auto_update_timer.setInterval(1500)  # 1.5 segundos
        
        # Splitter para áreas redimensionáveis
        self.splitter = QSplitter(Qt.Horizontal)
        
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
        
        # Atalho Ctrl+C para tabela
        self.copy_shortcut = QShortcut(QKeySequence.Copy, self.result_table)
        self.copy_shortcut.activated.connect(self.copy_selection_to_clipboard)
    
    def create_header_section(self):
        """Cria a seção de cabeçalho com título e subtítulo"""
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            background-color: {COLORS['header_bg']};
            border-radius: {COLORS['border_radius_md']};
            border: none; /* Removido a borda azul */
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_layout.setSpacing(5)
        
        # Título principal
        title_label = QLabel(STRINGS["app_title"])
        title_label.setFont(QFont(COLORS["font_family"], int(COLORS["font_size_title"].replace('px','')), QFont.Bold)) # Título maior
        title_label.setStyleSheet(f"color: {COLORS['accent']};")
        title_label.setAlignment(Qt.AlignLeft) # Alinhado à esquerda
        
        # Subtítulo (para nome do arquivo)
        self.subtitle_label = QLabel(STRINGS["app_subtitle"])
        self.subtitle_label.setFont(QFont(COLORS["font_family"], int(COLORS["font_size_subtitle"].replace('px',''))))
        self.subtitle_label.setStyleSheet("color: #aaaaaa;")
        self.subtitle_label.setAlignment(Qt.AlignLeft) # Alinhado à esquerda
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.subtitle_label)
        
        self.main_layout.addWidget(header_frame)
    
    def create_input_section(self):
        """Cria a seção de entrada de dados (lado esquerdo)"""
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        # Label
        input_label = QLabel(STRINGS["label_input"])
        input_label.setFont(QFont(COLORS["font_family"], int(COLORS["font_size_large"].replace('px','')), QFont.Bold))
        
        # Campo de texto
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Example:\nVersion 33\nfilename.blend\n18:15\nAuthor\n\nVersion 32\nfilename.blend\n18:10\nAuthor")
        self.input_text.textChanged.connect(self.schedule_auto_update)
        self.input_text.setToolTip(STRINGS["tt_input_text"]) # Tooltip
        
        # Configurações de processamento
        settings_layout = QHBoxLayout()
        
        # Botão de processamento
        self.process_btn = QPushButton(STRINGS["btn_process"])
        self.process_btn.clicked.connect(self.process_data)
        self.process_btn.setToolTip(STRINGS["tt_process_btn"]) # Tooltip

        # Seletor de tempo máximo de pausa (Slider e Input Manual)
        break_controls_container = QVBoxLayout() # Novo layout vertical para label e slider/input
        break_label = QLabel(STRINGS["max_break_label"])
        break_label.setFont(QFont(COLORS["font_family"], int(COLORS["font_size_medium"].replace('px',''))))
        
        self.max_break_slider = QSlider(Qt.Horizontal)
        self.max_break_slider.setRange(1, 120) # Intervalo de 1 a 120 minutos
        self.max_break_slider.setSingleStep(1)
        self.max_break_slider.setPageStep(5)
        self.max_break_slider.setTickPosition(QSlider.TicksBelow)
        self.max_break_slider.setTickInterval(5)
        self.max_break_slider.setValue(self.max_break_minutes)
        self.max_break_slider.valueChanged.connect(self.on_slider_value_changed)
        self.max_break_slider.setToolTip(STRINGS["tt_max_break_slider"]) # Tooltip

        self.max_break_input = QLineEdit()
        self.max_break_input.setValidator(QIntValidator(1, 999)) # Permite números de 1 a 999
        self.max_break_input.setText(str(self.max_break_minutes))
        self.max_break_input.setMaximumWidth(60) # Largura menor para o campo de input
        self.max_break_input.editingFinished.connect(self.on_manual_input_finished)
        self.max_break_input.setToolTip(STRINGS["tt_max_break_input"]) # Tooltip
        
        break_input_layout = QHBoxLayout() # Layout horizontal para slider e input
        break_input_layout.addWidget(self.max_break_slider)
        break_input_layout.addWidget(self.max_break_input)

        break_controls_container.addWidget(break_label) # Adiciona a label
        break_controls_container.addLayout(break_input_layout) # Adiciona o layout do slider/input

        settings_layout.addLayout(break_controls_container) # Adiciona o container ao settings_layout
        settings_layout.addStretch()
        settings_layout.addWidget(self.process_btn)
        
        # Adicionar ao layout
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_text, 1)
        input_layout.addLayout(settings_layout)
        
        self.splitter.addWidget(input_widget)
    
    def create_result_section(self):
        """Cria a seção de resultados (lado direito)"""
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setSpacing(10)
        
        # Cabeçalho da área de resultados
        result_header = QWidget()
        result_header_layout = QHBoxLayout(result_header)
        result_header_layout.setContentsMargins(0, 0, 0, 0)
        
        result_label = QLabel(STRINGS["label_result"])
        result_label.setFont(QFont(COLORS["font_family"], int(COLORS["font_size_large"].replace('px','')), QFont.Bold))
        
        # Botão para alternar entre visualizações
        self.toggle_view_btn = QPushButton(STRINGS["compact_view"])
        self.toggle_view_btn.clicked.connect(self.toggle_view)
        self.toggle_view_btn.setToolTip(STRINGS["tt_toggle_view_btn"]) # Tooltip
        
        result_header_layout.addWidget(result_label)
        result_header_layout.addStretch()
        result_header_layout.addWidget(self.toggle_view_btn)
        
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
        self.result_table.setToolTip(STRINGS["tt_result_table"]) # Tooltip
        
        # Botões
        button_layout = QHBoxLayout()
        
        # Botão de exportação
        self.export_btn = QPushButton(STRINGS["btn_export"])
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_data)
        self.export_btn.setToolTip(STRINGS["tt_export_btn"]) # Tooltip
        
        # Botão para copiar total
        self.copy_btn = QPushButton(STRINGS["btn_copy"])
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_total_to_clipboard)
        self.copy_btn.setToolTip(STRINGS["tt_copy_btn"]) # Tooltip
        
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.copy_btn)
        button_layout.addStretch()
        
        # Label de total com destaque
        self.total_label = QLabel()
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setFont(QFont(COLORS["font_family"], int(COLORS["font_size_total"].replace('px','')), QFont.Bold))
        self.total_label.setStyleSheet(f"""
            background-color: {COLORS['table_header']};
            padding: 15px;
            border-radius: {COLORS['border_radius_md']};
            border: {COLORS['border_width_thick']} solid {COLORS['highlight']};
            color: {COLORS['highlight']};
        """)
        self.total_label.setToolTip(STRINGS["tt_total_label"]) # Tooltip
        
        # Adicionar ao layout
        result_layout.addWidget(result_header)
        result_layout.addWidget(self.result_table, 1)
        result_layout.addLayout(button_layout)
        result_layout.addWidget(self.total_label)
        
        self.splitter.addWidget(result_widget)
        self.splitter.setSizes([400, 600])  # Proporção inicial
    
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
            self.show_error("Entrada inválida para 'Max Break'. Por favor, insira um número.")
    
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
            QTextEdit, QTableWidget {{
                background-color: {COLORS['table_header']};
                border: {COLORS['border_width_thin']} solid {COLORS['accent']};
                border-radius: {COLORS['border_radius_sm']};
                font-size: {COLORS['font_size_medium']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['table_header']};
                padding: 5px;
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QPushButton {{
                background-color: {COLORS['button']};
                border: none;
                border-radius: {COLORS['border_radius_sm']};
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
            QLabel {{
                font-size: {COLORS['font_size_medium']};
            }}
            QStatusBar {{
                font-size: {COLORS['font_size_small']};
                color: #aaa;
            }}
            QComboBox {{ /* Mantido caso haja necessidade futura, mas não usado para Max Break */
                background-color: {COLORS['table_header']};
                border: {COLORS['border_width_thin']} solid {COLORS['accent']};
                border-radius: {COLORS['border_radius_sm']};
                padding: 5px;
                min-width: 80px;
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
                margin: -5px 0; /* handle is 16x16, so -2px to make it vertical center */
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
                padding: 5px;
                font-size: {COLORS['font_size_medium']};
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
                self.subtitle_label.setText(f"Working on: {filename}")
            
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
        """Calcula a duração total de um bloco de trabalho considerando apenas intervalos válidos"""
        if len(block) < 2:
            return timedelta()
            
        total_duration = timedelta()
        sorted_block = sorted(block, key=lambda x: x['time']) # Garante que o bloco está ordenado por tempo
        
        for i in range(1, len(sorted_block)):
            prev_time = datetime.combine(datetime.today(), sorted_block[i-1]['time'])
            curr_time = datetime.combine(datetime.today(), sorted_block[i]['time'])
            
            # Ajuste para virada de meia-noite dentro do bloco
            if curr_time < prev_time:
                curr_time += timedelta(days=1)

            time_diff = curr_time - prev_time
            
            # Se o intervalo for válido (<= max_break), adiciona à duração
            if time_diff.total_seconds() / 60 <= self.max_break_minutes:
                total_duration += time_diff
        
        return total_duration
    
    # ==================== UI UPDATES ====================
    def display_results(self):
        """Exibe os resultados na tabela com a visualização selecionada"""
        if self.compact_view:
            self.display_compact_view()
        else:
            self.display_expanded_view()
    
    def display_compact_view(self):
        """Exibe apenas os blocos de trabalho (visão consolidada) do mais recente para o mais antigo."""
        # Ordena os blocos de trabalho do mais recente para o mais antigo
        # O bloco mais recente é o que tem a versão 'end' com o tempo mais recente.
        # Como work_blocks já é gerado em ordem cronológica crescente, basta reverter a lista.
        sorted_work_blocks_desc = sorted(self.work_blocks, key=lambda x: x['end']['time'], reverse=True)

        self.result_table.setRowCount(len(sorted_work_blocks_desc))
        
        for row, block in enumerate(sorted_work_blocks_desc):
            # Versão inicial
            start_version = block['start']['name']
            start_time = block['start']['time'].strftime("%H:%M")
            
            # Versão final
            end_version = block['end']['name']
            end_time = block['end']['time'].strftime("%H:%M")
            
            # Duração formatada (do bloco completo)
            duration_str = self.format_duration(block['duration'])
            
            # Criar itens
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
        """Exibe todas as transições de versão com duração e indicação de intervalos ignorados."""
        if not self.all_versions or len(self.all_versions) < 2:
            self.result_table.setRowCount(0)
            self.total_label.setText(f"{STRINGS['total_label']} <b>00:00</b>")
            return

        # Ordenar versões do mais novo para o mais antigo para corresponder ao formato de saída desejado
        sorted_versions_desc = sorted(self.all_versions, key=lambda x: x['time'], reverse=True)
        
        self.result_table.setRowCount(len(sorted_versions_desc) - 1) # Uma linha para cada transição
        
        row_index = 0
        for i in range(len(sorted_versions_desc) - 1):
            curr_version = sorted_versions_desc[i]
            prev_version = sorted_versions_desc[i+1] # A versão cronologicamente anterior

            curr_time_dt = datetime.combine(datetime.today(), curr_version['time'])
            prev_time_dt = datetime.combine(datetime.today(), prev_version['time'])

            # Ajuste para virada de meia-noite (se a versão anterior for "depois" da atual no mesmo dia)
            if prev_time_dt > curr_time_dt:
                prev_time_dt -= timedelta(days=1) # Assume que é do dia anterior

            time_diff = curr_time_dt - prev_time_dt
            
            duration_str = self.format_duration(time_diff)
            
            # Adicionar indicação de "IGNORADO" se o intervalo for muito grande
            if time_diff.total_seconds() / 60 > self.max_break_minutes:
                duration_str += f" (IGNORADO - Intervalo > {self.max_break_minutes} min)"
            
            items = [
                QTableWidgetItem(curr_version['name']),
                QTableWidgetItem(curr_version['time'].strftime("%H:%M")),
                QTableWidgetItem(prev_version['name']),
                QTableWidgetItem(prev_version['time'].strftime("%H:%M")),
                QTableWidgetItem(duration_str)
            ]
            
            for item in items:
                item.setTextAlignment(Qt.AlignCenter)
                # Aplicar cores alternadas para as linhas
                if row_index % 2 == 0:
                     item.setBackground(QColor(COLORS['table_row_even']))
                else:
                    item.setBackground(QColor(COLORS['table_row_odd']))
            
            for col, item in enumerate(items):
                self.result_table.setItem(row_index, col, item)
            
            row_index += 1
        
        # Atualiza total (o total ativo é o mesmo para ambas as vistas)
        total_str = self.format_duration(self.total_time)
        self.total_label.setText(
            f"{STRINGS['total_label']} <b>{total_str}</b>"
        )
    
    def format_duration(self, duration):
        """Formata timedelta para HH:MM"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{hours:02d}:{minutes:02d}"
    
    def copy_total_to_clipboard(self):
        """Copia o valor do tempo total para a área de transferência (apenas HH:MM)"""
        total_text = self.total_label.text()
        # Extrai apenas o valor HH:MM
        if "<b>" in total_text:
            total_value = total_text.split("<b>")[1].split("</b>")[0]
        else:
            # Fallback caso o formato mude (menos robusto, mas tenta pegar o último campo)
            total_value = total_text.split(":")[-1].strip()
        
        clipboard = QApplication.clipboard()
        clipboard.setText(total_value)
        self.status_bar.showMessage(STRINGS["msg_copied"])
    
    def copy_selection_to_clipboard(self):
        """Copia a seleção da tabela para a área de transferência"""
        selected_ranges = self.result_table.selectedRanges()
        if not selected_ranges:
            return
        
        clipboard_text = ""
        
        # Obter cabeçalhos para a cópia (opcional, mas bom para CSV/tabela)
        header_items = [self.result_table.horizontalHeaderItem(i).text() for i in range(self.result_table.columnCount())]
        clipboard_text += "\t".join(header_items) + "\n" # Adiciona cabeçalhos
        
        for r in range(selected_ranges[0].topRow(), selected_ranges[0].bottomRow() + 1):
            row_data = []
            for c in range(self.result_table.columnCount()): # Copiar todas as colunas da linha selecionada
                item = self.result_table.item(r, c)
                row_data.append(item.text() if item else "")
            clipboard_text += "\t".join(row_data) + "\n"
        
        clipboard = QApplication.clipboard()
        clipboard.setText(clipboard_text.strip())
        self.status_bar.showMessage("📋 Selection copied to clipboard!")
    
    # ==================== EXPORT/HISTORY ====================
    def export_data(self):
        """Exporta os dados para CSV ou TXT"""
        options = QFileDialog.Option()
        default_name = f"{self.current_filename}_work_blocks" if self.current_filename else "work_blocks"
        
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Data",
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
        """Exporta dados para formato CSV"""
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
                
                # Adiciona total
                total_text = self.total_label.text().split(">")[-1].replace("</b", "")
                writer.writerow(["", "", "", "TOTAL", total_text.strip()])
                
            QMessageBox.information(
                self,
                "Export Successful",
                f"Data exported to CSV:\n{file_path}"
            )
        except Exception as e:
            self.show_error(f"Export failed: {str(e)}")
    
    def export_to_txt(self, file_path):
        """Exporta dados para formato TXT"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(f"{'Start Version':<25}{'Start Time':<10}{'End Version':<25}{'End Time':<10}{'Duration':>10}\n")
                file.write("-" * 80 + "\n")
                
                for row in range(self.result_table.rowCount()):
                    row_data = []
                    for col in range(5):
                        item = self.result_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    file.write(f"{row_data[0]:<25}{row_data[1]:<10}{row_data[2]:<25}{row_data[3]:<10}{row_data[4]:>10}\n")
                
                # Adiciona total
                total_text = self.total_label.text().split(">")[-1].replace("</b", "").strip()
                file.write("\n" + "-" * 80 + "\n")
                file.write(f"{'TOTAL':<60}{total_text:>20}")
                
            QMessageBox.information(
                self,
                "Export Successful",
                f"Data exported to TXT:\n{file_path}"
            )
        except Exception as e:
            self.show_error(f"Export failed: {str(e)}")
    
    def save_to_history(self, raw_input, work_blocks, total_time):
        """Salva a sessão atual no histórico"""
        history = []
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as file:
                    history = json.load(file)
            except:
                history = []
        
        # Limitar histórico a 50 entradas
        if len(history) >= 50:
            history = history[-49:]
        
        # Adicionar nova entrada
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
        """Carrega o histórico do arquivo"""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as file:
                history = json.load(file)
                if history:
                    # Carrega o último item
                    last_entry = history[-1]
                    self.input_text.setText(last_entry["input"])
        except:
            pass
    
    # ==================== UTILITIES ====================
    def clear_results(self):
        """Limpa os resultados atuais"""
        self.result_table.setRowCount(0)
        self.total_label.clear()
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
    
    def show_error(self, message):
        """Exibe uma mensagem de erro"""
        self.status_bar.showMessage(message)
        self.clear_results()
        
        # Efeito visual temporário
        self.status_bar.setStyleSheet(f"color: {COLORS['error']};")
        QApplication.processEvents()
        QTimer.singleShot(3000, lambda: self.status_bar.setStyleSheet(""))
    
    def closeEvent(self, event):
        """Salva configurações ao fechar"""
        self.settings.setValue("window_size", self.size())
        self.settings.setValue("splitter_sizes", self.splitter.sizes())
        super().closeEvent(event)

# ==================== APPLICATION START ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = VersionTimeTracker()
    
    # Restaurar tamanho da janela
    if window.settings.contains("window_size"):
        window.resize(window.settings.value("window_size"))
    
    # Restaurar tamanho do splitter
    if window.settings.contains("splitter_sizes"):
        sizes = window.settings.value("splitter_sizes")
        window.splitter.setSizes([int(size) for size in sizes])
    
    window.show()
    sys.exit(app.exec())
