import sys
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QStatusBar, QFileDialog, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QColor, QPalette, QFont

# ==================== CONSTANTS ====================
COLORS = {
    "bg": "#1e1e1e",
    "text": "#ffffff",
    "accent": "#00adb5",
    "button": "#393e46",
    "error": "#ff2e63",
    "table_header": "#252525",
    "table_row_even": "#2a2a2a",
    "table_row_odd": "#242424"
}

STRINGS = {
    "app_title": "🧮 Version Time Tracker",
    "label_input": "📋 Paste your version list:",
    "btn_process": "⚙️ Process",
    "btn_export": "💾 Export",
    "label_result": "📊 Work Blocks",
    "msg_invalid": "⚠️ Invalid or incomplete data detected",
    "msg_success": "✅ Processed successfully!",
    "export_csv": "CSV Files (*.csv)",
    "export_txt": "Text Files (*.txt)",
    "status_ready": "Ready",
    "status_processing": "Processing...",
    "col_version_start": "Start Version",
    "col_version_end": "End Version",
    "col_duration": "Duration",
    "total_label": "TOTAL ACTIVE TIME:",
    "history_file": "version_tracker_history.json"
}

# ==================== MAIN WINDOW ====================
class VersionTimeTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(STRINGS["app_title"])
        self.setMinimumSize(800, 600)
        
        # Configurações
        self.settings = QSettings("DeepSeek", "VersionTimeTracker")
        self.max_break_minutes = 15
        self.history_file = Path(STRINGS["history_file"])
        
        # Widgets principais
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Área de input
        self.create_input_section()
        
        # Área de resultados
        self.create_result_section()
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(STRINGS["status_ready"])
        
        # Aplicar estilo
        self.apply_dark_theme()
        self.load_history()
    
    def create_input_section(self):
        """Cria a seção de entrada de dados"""
        # Label
        input_label = QLabel(STRINGS["label_input"])
        input_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        # Campo de texto
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Example:\nCurrent version\n...\n23:25\n...\n\nVersion 100\n...\n23:22\n...")
        self.input_text.setMinimumHeight(150)
        
        # Botão de processamento
        self.process_btn = QPushButton(STRINGS["btn_process"])
        self.process_btn.clicked.connect(self.process_data)
        
        # Adicionar ao layout
        self.main_layout.addWidget(input_label)
        self.main_layout.addWidget(self.input_text)
        self.main_layout.addWidget(self.process_btn)
    
    def create_result_section(self):
        """Cria a seção de resultados"""
        # Label
        result_label = QLabel(STRINGS["label_result"])
        result_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        # Tabela de resultados
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(3)
        self.result_table.setHorizontalHeaderLabels([
            STRINGS["col_version_start"],
            STRINGS["col_version_end"],
            STRINGS["col_duration"]
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.verticalHeader().setVisible(False)
        
        # Botão de exportação
        self.export_btn = QPushButton(STRINGS["btn_export"])
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_data)
        
        # Label de total
        self.total_label = QLabel()
        self.total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_label.setFont(QFont("Arial", 10, QFont.Bold))
        
        # Adicionar ao layout
        self.main_layout.addWidget(result_label)
        self.main_layout.addWidget(self.result_table)
        self.main_layout.addWidget(self.export_btn)
        self.main_layout.addWidget(self.total_label)
    
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
        self.total_label.setStyleSheet(f"color: {COLORS['accent']};")
    
    # ==================== CORE LOGIC ====================
    def process_data(self):
        """Processa os dados de entrada e calcula os blocos de trabalho"""
        self.status_bar.showMessage(STRINGS["status_processing"])
        self.export_btn.setEnabled(False)
        raw_text = self.input_text.toPlainText().strip()
        
        if not raw_text:
            self.show_error(STRINGS["msg_invalid"])
            return
        
        try:
            # Parse das versões
            versions = self.parse_versions(raw_text)
            
            # Agrupamento em blocos
            work_blocks = self.calculate_work_blocks(versions)
            
            # Cálculo do tempo total
            total_time = sum((block['duration'] for block in work_blocks), timedelta())
            
            # Exibição dos resultados
            self.display_results(work_blocks, total_time)
            self.save_to_history(raw_text, work_blocks, total_time)
            
            self.status_bar.showMessage(STRINGS["msg_success"])
            self.export_btn.setEnabled(True)
            
        except Exception as e:
            self.show_error(f"{STRINGS['msg_invalid']}: {str(e)}")
    
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
                    time_str = line
                    break
            
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
            start_item = QTableWidgetItem(block['start']['name'])
            # Versão final
            end_item = QTableWidgetItem(block['end']['name'])
            # Duração formatada
            duration_str = self.format_duration(block['duration'])
            duration_item = QTableWidgetItem(duration_str)
            
            # Centraliza conteúdo
            start_item.setTextAlignment(Qt.AlignCenter)
            end_item.setTextAlignment(Qt.AlignCenter)
            duration_item.setTextAlignment(Qt.AlignCenter)
            
            # Insere na tabela
            self.result_table.setItem(row, 0, start_item)
            self.result_table.setItem(row, 1, end_item)
            self.result_table.setItem(row, 2, duration_item)
        
        # Atualiza total
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
    
    # ==================== EXPORT/HISTORY ====================
    def export_data(self):
        """Exporta os dados para CSV ou TXT"""
        options = QFileDialog.Option()
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "",
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
                    STRINGS["col_version_end"],
                    STRINGS["col_duration"]
                ])
                
                for row in range(self.result_table.rowCount()):
                    start = self.result_table.item(row, 0).text()
                    end = self.result_table.item(row, 1).text()
                    duration = self.result_table.item(row, 2).text()
                    writer.writerow([start, end, duration])
                
                # Adiciona total
                total_text = self.total_label.text().split(">")[-1].replace("</b", "")
                writer.writerow(["", "TOTAL", total_text.strip()])
                
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
                file.write(f"{'Version Start':<30}{'Version End':<30}{'Duration':>10}\n")
                file.write("-" * 70 + "\n")
                
                for row in range(self.result_table.rowCount()):
                    start = self.result_table.item(row, 0).text()
                    end = self.result_table.item(row, 1).text()
                    duration = self.result_table.item(row, 2).text()
                    file.write(f"{start:<30}{end:<30}{duration:>10}\n")
                
                # Adiciona total
                total_text = self.total_label.text().split(">")[-1].replace("</b", "").strip()
                file.write("\n" + "-" * 70 + "\n")
                file.write(f"{'TOTAL':<60}{total_text:>10}")
                
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
                    "end": b['end']['name'],
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