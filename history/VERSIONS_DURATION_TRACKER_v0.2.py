import sys
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QStatusBar, QFileDialog, QHeaderView, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QFont, QClipboard, QKeySequence, QShortcut

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
    "header_bg": "#151515"
}

STRINGS = {
    "app_title": "🧮 Version Time Tracker",
    "app_subtitle": "Blender Version Time Calculator",
    "label_input": "📋 Paste your version list:",
    "btn_process": "⚙️ Process",
    "btn_export": "💾 Export",
    "btn_copy": "📋 Copy Total",
    "label_result": "📊 Work Blocks",
    "msg_invalid": "⚠️ Invalid or incomplete data detected",
    "msg_success": "✅ Processed successfully!",
    "msg_copied": "📋 Total copied to clipboard!",
    "export_csv": "CSV Files (*.csv)",
    "export_txt": "Text Files (*.txt)",
    "status_ready": "Ready",
    "status_processing": "Processing...",
    "col_version_start": "Start Version",
    "col_start_time": "Start Time",
    "col_version_end": "End Version",
    "col_end_time": "End Time",
    "col_duration": "Duration",
    "total_label": "TOTAL ACTIVE TIME:",
    "history_file": "version_tracker_history.json"
}

# ==================== MAIN WINDOW ====================
class VersionTimeTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(STRINGS["app_title"])
        self.setMinimumSize(1000, 700)  # Janela maior
        
        # Configurações
        self.settings = QSettings("DeepSeek", "VersionTimeTracker")
        self.max_break_minutes = 15
        self.history_file = Path(STRINGS["history_file"])
        self.current_filename = ""
        
        # Widgets principais
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(10)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Cabeçalho com título e subtítulo
        self.create_header_section()
        
        # Área de conteúdo
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Área de input (esquerda)
        self.create_input_section(content_layout)
        
        # Área de resultados (direita)
        self.create_result_section(content_layout)
        
        self.main_layout.addWidget(content_widget, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(STRINGS["status_ready"])
        
        # Aplicar estilo
        self.apply_dark_theme()
        self.load_history()
        
        # Timer para atualização automática
        self.auto_update_timer = QTimer()
        self.auto_update_timer.setSingleShot(True)
        self.auto_update_timer.timeout.connect(self.process_data)
        self.auto_update_timer.setInterval(1500)  # 1.5 segundos
        
        # Atalho Ctrl+C para tabela
        self.copy_shortcut = QShortcut(QKeySequence.Copy, self.result_table)
        self.copy_shortcut.activated.connect(self.copy_selection_to_clipboard)
    
    def create_header_section(self):
        """Cria a seção de cabeçalho com título e subtítulo"""
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {COLORS['header_bg']}; border-radius: 8px;")
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_layout.setSpacing(5)
        
        # Título principal
        title_label = QLabel(STRINGS["app_title"])
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setStyleSheet(f"color: {COLORS['accent']};")
        title_label.setAlignment(Qt.AlignCenter)
        
        # Subtítulo (para nome do arquivo)
        self.subtitle_label = QLabel(STRINGS["app_subtitle"])
        self.subtitle_label.setFont(QFont("Arial", 12))
        self.subtitle_label.setStyleSheet("color: #aaaaaa;")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.subtitle_label)
        
        self.main_layout.addWidget(header_frame)
    
    def create_input_section(self, parent_layout):
        """Cria a seção de entrada de dados (lado esquerdo)"""
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 10, 0)  # Margem à direita
        
        # Label
        input_label = QLabel(STRINGS["label_input"])
        input_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        # Campo de texto
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Example:\nCurrent version\n...\n23:25\n...\n\nVersion 100\n...\n23:22\n...")
        self.input_text.setMinimumHeight(400)  # Altura maior
        
        # Conectar alterações de texto ao timer de atualização automática
        self.input_text.textChanged.connect(self.schedule_auto_update)
        
        # Botão de processamento
        self.process_btn = QPushButton(STRINGS["btn_process"])
        self.process_btn.clicked.connect(self.process_data)
        
        # Adicionar ao layout
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.process_btn)
        
        parent_layout.addWidget(input_widget, 1)  # 40% do espaço
    
    def create_result_section(self, parent_layout):
        """Cria a seção de resultados (lado direito)"""
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        
        # Label
        result_label = QLabel(STRINGS["label_result"])
        result_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        # Tabela de resultados
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)  # Mais colunas para horários
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
        self.result_table.setMinimumHeight(300)
        
        # Botões
        button_layout = QHBoxLayout()
        
        # Botão de exportação
        self.export_btn = QPushButton(STRINGS["btn_export"])
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_data)
        
        # Botão para copiar total
        self.copy_btn = QPushButton(STRINGS["btn_copy"])
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_total_to_clipboard)
        
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.copy_btn)
        
        # Label de total com destaque
        self.total_label = QLabel()
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.total_label.setStyleSheet(f"""
            background-color: {COLORS['table_header']};
            padding: 15px;
            border-radius: 8px;
            border: 2px solid {COLORS['accent']};
        """)
        
        # Adicionar ao layout
        result_layout.addWidget(result_label)
        result_layout.addWidget(self.result_table)
        result_layout.addLayout(button_layout)
        result_layout.addWidget(self.total_label)
        
        parent_layout.addWidget(result_widget, 2)  # 60% do espaço
    
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
                font-family: 'Segoe UI';
            }}
            QTextEdit, QTableWidget {{
                background-color: {COLORS['table_header']};
                border: 1px solid {COLORS['accent']};
                border-radius: 4px;
                font-size: 12px;
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
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
            QLabel {{
                font-size: 12px;
            }}
            QStatusBar {{
                font-size: 11px;
                color: #aaa;
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
        
        # Cor de destaque para total
        self.total_label.setStyleSheet(f"""
            color: {COLORS['accent']};
            font-weight: bold;
            font-size: 14px;
        """)
    
    # ==================== CORE LOGIC ====================
    def process_data(self):
        """Processa os dados de entrada e calcula os blocos de trabalho"""
        self.status_bar.showMessage(STRINGS["status_processing"])
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        raw_text = self.input_text.toPlainText().strip()
        
        if not raw_text:
            self.show_error(STRINGS["msg_invalid"])
            return
        
        try:
            # Parse das versões
            versions = self.parse_versions(raw_text)
            
            # Tentar extrair nome do arquivo
            filename = self.extract_filename(raw_text)
            if filename:
                self.current_filename = filename
                self.subtitle_label.setText(f"Working on: {filename}")
            
            # Agrupamento em blocos
            work_blocks = self.calculate_work_blocks(versions)
            
            # Cálculo do tempo total
            total_time = sum((block['duration'] for block in work_blocks), timedelta())
            
            # Exibição dos resultados
            self.display_results(work_blocks, total_time)
            self.save_to_history(raw_text, work_blocks, total_time)
            
            self.status_bar.showMessage(STRINGS["msg_success"])
            self.export_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            
        except Exception as e:
            self.show_error(f"{STRINGS['msg_invalid']}: {str(e)}")
    
    def extract_filename(self, raw_text):
        """Tenta extrair o nome do arquivo do texto"""
        blocks = raw_text.split('\n\n')
        if blocks:
            first_block_lines = blocks[0].splitlines()
            if len(first_block_lines) > 1:
                # A segunda linha pode ser o nome do arquivo
                filename_line = first_block_lines[1].strip()
                if '.' in filename_line:
                    return filename_line.split('.')[0]
        return None
    
    def parse_versions(self, text):
        """Converte texto em lista de versões com timestamps - novo formato"""
        versions = []
        blocks = text.split('\n\n')  # Separa por blocos vazios

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if len(lines) < 2:  # Pelo menos versão e hora
                continue
                
            # Primeira linha é sempre o nome da versão
            version_name = lines[0]
            
            # Procurar linha com formato de hora (HH:MM)
            time_str = None
            for line in lines[1:]:
                if len(line) == 5 and line[2] == ':':  # Formato básico de hora
                    try:
                        # Tenta converter para validar
                        datetime.strptime(line, "%H:%M")
                        time_str = line
                        break
                    except:
                        continue
            
            if not time_str:
                continue
                
            try:
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
    
    def calculate_work_blocks(self, versions):
        """Agrupa versões em blocos de trabalho contínuos"""
        if len(versions) < 2:
            raise ValueError("At least two versions needed")
        
        versions.sort(key=lambda x: x['time'])
        work_blocks = []
        current_block = [versions[0]]
        
        for i in range(1, len(versions)):
            prev_time = datetime.combine(datetime.today(), versions[i-1]['time'])
            curr_time = datetime.combine(datetime.today(), versions[i]['time'])
            time_diff = curr_time - prev_time
            
            # Verifica se é uma pausa aceitável
            if time_diff <= timedelta(minutes=self.max_break_minutes):
                current_block.append(versions[i])
            else:
                # Finaliza o bloco atual
                block_duration = self.calculate_block_duration(current_block)
                work_blocks.append({
                    'start': current_block[0],
                    'end': current_block[-1],
                    'duration': block_duration
                })
                # Inicia novo bloco
                current_block = [versions[i]]
        
        # Adiciona o último bloco
        if current_block:
            block_duration = self.calculate_block_duration(current_block)
            work_blocks.append({
                'start': current_block[0],
                'end': current_block[-1],
                'duration': block_duration
            })
        
        return work_blocks
    
    def calculate_block_duration(self, block):
        """Calcula a duração total de um bloco de trabalho"""
        start_time = datetime.combine(datetime.today(), block[0]['time'])
        end_time = datetime.combine(datetime.today(), block[-1]['time'])
        return end_time - start_time
    
    # ==================== UI UPDATES ====================
    def display_results(self, work_blocks, total_time):
        """Exibe os resultados na tabela"""
        self.result_table.setRowCount(len(work_blocks))
        
        for row, block in enumerate(work_blocks):
            # Versão inicial
            start_version = block['start']['name']
            start_time = block['start']['time'].strftime("%H:%M")
            
            # Versão final
            end_version = block['end']['name']
            end_time = block['end']['time'].strftime("%H:%M")
            
            # Duração formatada
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
        
        # Atualiza total com mais destaque
        total_str = self.format_duration(total_time)
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
        
        for r in range(selected_ranges[0].topRow(), selected_ranges[0].bottomRow() + 1):
            row_items = []
            for c in range(selected_ranges[0].leftColumn(), selected_ranges[0].rightColumn() + 1):
                item = self.result_table.item(r, c)
                row_items.append(item.text() if item else "")
            clipboard_text += "\t".join(row_items) + "\n"
        
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
    def show_error(self, message):
        """Exibe uma mensagem de erro"""
        self.status_bar.showMessage(message)
        self.result_table.setRowCount(0)
        self.total_label.clear()
        self.export_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        
        # Efeito visual temporário
        self.status_bar.setStyleSheet(f"color: {COLORS['error']};")
        QApplication.processEvents()
        QTimer.singleShot(3000, lambda: self.status_bar.setStyleSheet(""))
    
    def closeEvent(self, event):
        """Salva configurações ao fechar"""
        self.settings.setValue("window_size", self.size())
        super().closeEvent(event)

# ==================== APPLICATION START ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = VersionTimeTracker()
    
    # Restaurar tamanho da janela
    if window.settings.contains("window_size"):
        window.resize(window.settings.value("window_size"))
    
    window.show()
    sys.exit(app.exec())