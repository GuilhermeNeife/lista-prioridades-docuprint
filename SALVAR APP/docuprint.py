import sys
import os
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QDialogButtonBox, QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox, QLabel,
    QPushButton, QMessageBox, QDialog, QLineEdit, QHBoxLayout, QDateEdit,
    QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QIcon
from qt_material import apply_stylesheet
import subprocess
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import defaultdict
from datetime import datetime

# ---------- Configurações ----------
RESPONSIBLES_BY_STAGE = {
    'Pré-Impressão': ['Guilherme', 'Calixto'],
    'Impressão': [
        'Eduardo', 'Kennedy', 'Diogo', 'Pedro', 'Francine',
        'Monalisa', 'Marcos', 'Camila'
    ],
    'Encadernação': ['Marcos', 'Josefa', 'Carla', 'Janaina', 'Valeria', 'Vania'],
    'Refile': ['Luan', 'Diego', 'Valeria', 'Josefa', 'Vania'],
    'Expedição': ['Dayana', 'David'],
    'Finalizado': ['Guilherme']
}

USERS = {
    'Admin': ('', ['Admin', 'Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado']),
    'Pré-impressao': ('123', 'Pré-Impressão'),
    'Impressao': ('imp123', 'Impressão'),
    'Acabamento': ('acab123', ['Encadernação', 'Refile']),
    'Expedição': ('exp123', ['Expedição', 'Finalizado']),
}

MAQUINA_PB_OPTIONS = ["", "OCÉ 1", "OCÉ 3", "BALTORO", "ATEXCO"]
MAQUINA_CL_OPTIONS = ["", "RICOH", "BALTORO"]

database_path = "Q:\\___LISTA DE PRIORIDADES\\GUILHERME\\pedidos.db"

# ---------- Banco de dados ----------
def load_data(is_admin=False):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    # ADICIONEI mc DE VOLTA
    if is_admin:
        cursor.execute("""
            SELECT lote, data_hora_entrada, cliente, prazo_grafica, status, 
                   M, C, mc, maquina_PB, maquina_CL, 
                   observacoes_impressao, observacoes_acabamento, 
                   descricao, caminho_do_pedido, Total, informacao_impressao 
            FROM pedidos 
            ORDER BY lote
        """)
    else:
        cursor.execute("""
            SELECT lote, data_hora_entrada, cliente, prazo_grafica, status, 
                   M, C, mc, maquina_PB, maquina_CL, 
                   observacoes_impressao, observacoes_acabamento, 
                   descricao, caminho_do_pedido, Total, informacao_impressao 
            FROM pedidos
            WHERE status != 'Finalizado'
            ORDER BY lote
        """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_database(lote, new_status):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE pedidos SET status = ? WHERE lote = ?", (new_status, lote))
    conn.commit()
    conn.close()

def fetch_single_lote_data(lote):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT lote, data_hora_entrada, cliente, prazo_grafica, status, 
               M, C, mc, maquina_PB, maquina_CL, 
               observacoes_impressao, observacoes_acabamento, 
               descricao, caminho_do_pedido, Total, informacao_impressao 
        FROM pedidos 
        WHERE lote = ?
    """, (lote,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_metrics_data(start_date, end_date):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            substr(data_hora_entrada, 7, 4) || '-' ||
            substr(data_hora_entrada, 4, 2) || '-' ||
            substr(data_hora_entrada, 1, 2) as dia,
            SUM(Total) as total_dia
        FROM pedidos
        WHERE substr(data_hora_entrada, 7, 4) || '-' ||
              substr(data_hora_entrada, 4, 2) || '-' ||
              substr(data_hora_entrada, 1, 2)
              BETWEEN ? AND ?
        GROUP BY dia
        ORDER BY dia
    """, (start_date.toString("yyyy-MM-dd"), end_date.toString("yyyy-MM-dd")))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return [], []
    dias = [row[0] for row in rows]
    totais = [row[1] for row in rows]
    return dias, totais

# ---------- Login (inalterado) ----------
class LoginWindow(QDialog):
    # (código igual ao fornecido anteriormente – omitido por brevidade)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(500, 300, 300, 200)
        self.setWindowIcon(QIcon("Q:\\___LISTA DE PRIORIDADES\\GUILHERME\\LOGOS\\D DE DOCUPRINT.ico"))
        self.user_sector = None

        layout = QVBoxLayout()
        self.username_combo = QComboBox(self)
        self.username_combo.addItems(USERS.keys())
        layout.addWidget(self.username_combo)

        password_layout = QHBoxLayout()
        self.password = QLineEdit(self)
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.password)

        self.toggle_password_btn = QPushButton("Show", self)
        self.toggle_password_btn.setCheckable(True)
        self.toggle_password_btn.toggled.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.toggle_password_btn)

        layout.addLayout(password_layout)
        login_button = QPushButton("Login", self)
        login_button.clicked.connect(self.check_credentials)
        layout.addWidget(login_button)
        self.setLayout(layout)

    def toggle_password_visibility(self, checked):
        if checked:
            self.password.setEchoMode(QLineEdit.Normal)
            self.toggle_password_btn.setText("Hide")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.toggle_password_btn.setText("Show")

    def check_credentials(self):
        username = self.username_combo.currentText()
        password = self.password.text()
        user_info = USERS.get(username)
        if user_info and user_info[0] == password:
            self.user_sector = user_info[1]
            self.accept()
        else:
            QMessageBox.warning(self, 'Login Failed', 'Invalid username or password')

# ---------- Janela Principal ----------
class PedidoApp(QMainWindow):
    def __init__(self, user_sector):
        super().__init__()
        self.setWindowTitle("Lista de Prioridade UICLAP")
        self.setGeometry(100, 100, 1300, 700)
        self.user_sector = user_sector
        self.setWindowIcon(QIcon("Q:\\___LISTA DE PRIORIDADES\\GUILHERME\\LOGOS\\favicon.ico"))

        if isinstance(user_sector, list):
            self.is_admin = 'Admin' in user_sector
            self.user_sectors = user_sector
        else:
            self.is_admin = (user_sector == 'Admin')
            self.user_sectors = [user_sector]

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # --- Barra de pesquisa global ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Buscar Lote:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Digite o número do lote...")
        self.search_input.returnPressed.connect(self.search_lote)
        search_layout.addWidget(self.search_input)
        search_btn = QPushButton("Buscar")
        search_btn.clicked.connect(self.search_lote)
        search_layout.addWidget(search_btn)
        main_layout.addLayout(search_layout)

        # Abas principais
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        all_stages = ['Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado']
        if self.is_admin:
            self.stages = all_stages
        else:
            self.stages = [stage for stage in all_stages if stage != 'Finalizado']

        self.create_tabs()

        if self.is_admin:
            self.create_metrics_tab()

    # ================== MÉTRICAS ==================
    def create_metrics_tab(self):
        metrics_widget = QWidget()
        layout = QVBoxLayout()

        filter_group = QGroupBox("Filtrar por período")
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("De:"))
        self.metrics_start = QDateEdit()
        self.metrics_start.setCalendarPopup(True)
        self.metrics_start.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(self.metrics_start)

        filter_layout.addWidget(QLabel("Até:"))
        self.metrics_end = QDateEdit()
        self.metrics_end.setCalendarPopup(True)
        self.metrics_end.setDate(QDate.currentDate())
        filter_layout.addWidget(self.metrics_end)

        update_btn = QPushButton("Atualizar")
        update_btn.clicked.connect(self.update_metrics)
        filter_layout.addWidget(update_btn)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        indicators_layout = QHBoxLayout()
        self.lbl_total = QLabel("Total de unidades: 0")
        self.lbl_total.setStyleSheet("font-size: 14px; font-weight: bold;")
        indicators_layout.addWidget(self.lbl_total)

        self.lbl_avg = QLabel("Média diária: 0")
        self.lbl_avg.setStyleSheet("font-size: 14px; font-weight: bold;")
        indicators_layout.addWidget(self.lbl_avg)
        layout.addLayout(indicators_layout)

        self.metrics_figure = Figure()
        self.metrics_canvas = FigureCanvas(self.metrics_figure)
        layout.addWidget(self.metrics_canvas)

        metrics_widget.setLayout(layout)
        self.tabs.addTab(metrics_widget, "Métricas")

    def update_metrics(self):
        start = self.metrics_start.date()
        end = self.metrics_end.date()
        dias, totais = get_metrics_data(start, end)

        self.metrics_figure.clear()
        ax = self.metrics_figure.add_subplot(111)

        if not dias:
            self.lbl_total.setText("Total de unidades: 0")
            self.lbl_avg.setText("Média diária: 0")
            ax.set_title("Nenhum dado no período")
            self.metrics_canvas.draw()
            return

        total_geral = sum(totais)
        delta = end.toPython() - start.toPython()
        dias_corridos = delta.days + 1
        media_diaria = total_geral / dias_corridos if dias_corridos > 0 else 0

        self.lbl_total.setText(f"Total de unidades: {total_geral}")
        self.lbl_avg.setText(f"Média diária: {media_diaria:.1f} (período de {dias_corridos} dias)")

        ax.bar(dias, totais, color='steelblue')
        ax.set_xlabel('Data')
        ax.set_ylabel('Total de unidades')
        ax.set_title('Totais por dia')
        ax.tick_params(axis='x', rotation=45)
        self.metrics_figure.tight_layout()
        self.metrics_canvas.draw()

    # ================== PESQUISA E PERMISSÕES ==================
    def search_lote(self):
        texto = self.search_input.text().strip()
        if not texto:
            return
        for stage, table in self.tables.items():
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item and texto in item.text():
                    index = self.tabs.indexOf(table.parent().parent())
                    self.tabs.setCurrentIndex(index)
                    table.selectRow(row)
                    table.scrollToItem(item, QTableWidget.PositionAtCenter)
                    return
        QMessageBox.information(self, "Busca", f"Lote '{texto}' não encontrado.")

    def has_permission_for_stage(self, stage):
        return self.is_admin or (stage in self.user_sectors)

    # ================== CRIAÇÃO DAS ABAS ==================
    def create_tabs(self):
        self.tables = {}
        for stage in self.stages:
            table_widget = QWidget()
            layout = QVBoxLayout()
            table = QTableWidget()

            # COLUNAS: agora 15 para estágios normais (inclui MC), 17 para Finalizado (Histórico + Ações)
            if stage == 'Finalizado':
                table.setColumnCount(17)
                table.setHorizontalHeaderLabels([
                    'Lote', 'Data/Hora Entrada', 'Cliente', 'Prazo Gráfica',
                    'Status', 'M', 'C', 'MC', 'Maquina PB', 'Maquina CL',
                    'Obs. Impressão', 'Obs. Acabamento', 'Descrição',
                    'Caminho do Pedido', 'Total', 'Histórico', 'Ações'
                ])
            else:
                table.setColumnCount(15)
                table.setHorizontalHeaderLabels([
                    'Lote', 'Data/Hora Entrada', 'Cliente', 'Prazo Gráfica',
                    'Status', 'M', 'C', 'MC', 'Maquina PB', 'Maquina CL',
                    'Obs. Impressão', 'Obs. Acabamento', 'Descrição',
                    'Caminho do Pedido', 'Total'
                ])

            permitido = self.has_permission_for_stage(stage)
            if permitido:
                table.cellChanged.connect(self.cell_changed)
                table.cellClicked.connect(self.cell_clicked)

            self.setup_table_styles(table, stage)
            layout.addWidget(table)
            table_widget.setLayout(layout)
            self.tabs.addTab(table_widget, stage)
            self.tables[stage] = table

        self.load_data_into_tables()

    def setup_table_styles(self, table, stage):
        table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: orange;
                color: black;
                padding: 4px;
                border: none;
                font-size: 10px;
                height: 30px;
                font-weight: bold;
                text-align: center;
            }
        """)
        if stage == 'Finalizado':
            widths = [43, 120, 58, 95, 130, 70, 70, 70, 80, 80, 140, 150, 250, 130, 40, 250, 80]
        else:
            widths = [43, 120, 58, 95, 130, 70, 70, 70, 80, 80, 140, 150, 250, 130, 40]
        for i, width in enumerate(widths):
            table.setColumnWidth(i, width)
        table.verticalHeader().setDefaultSectionSize(40)

    def load_data_into_tables(self):
        data = load_data(is_admin=self.is_admin)

        for table in self.tables.values():
            try:
                table.cellChanged.disconnect(self.cell_changed)
            except:
                pass

        for table in self.tables.values():
            table.setRowCount(0)

        for row in data:
            try:
                (lote, data_hora_entrada, cliente, prazo_grafica, status,
                 M, C, mc, maquina_PB, maquina_CL, obs_imp, obs_acab,
                 descricao, caminho, Total, informacao_impressao) = row
                if status == "Concluído":
                    continue
                self.add_row_to_table(row)
            except ValueError as e:
                print(f"Erro ao desestruturar linha: {e} | Dados: {row}")
                continue

        for stage, table in self.tables.items():
            permitido = self.has_permission_for_stage(stage)
            if permitido:
                table.cellChanged.connect(self.cell_changed)

    def add_row_to_table(self, row):
        try:
            (lote, data_hora_entrada, cliente, prazo_grafica, status,
             M, C, mc, maquina_PB, maquina_CL, obs_imp, obs_acab,
             descricao, caminho, Total, informacao_impressao) = row
        except ValueError:
            return

        if status == 'Finalizado' and not self.is_admin:
            return

        table = self.tables.get(status, self.tables['Pré-Impressão'])
        row_count = table.rowCount()
        table.insertRow(row_count)

        # Mapeamento das 15 primeiras colunas (0-14), ajustado para incluir MC
        values = {
            0: lote, 1: data_hora_entrada, 2: cliente, 3: prazo_grafica,
            4: status, 5: M, 6: C, 7: mc, 8: maquina_PB, 9: maquina_CL,
            10: obs_imp, 11: obs_acab, 12: descricao, 13: caminho, 14: Total
        }

        num_cols = table.columnCount()
        for col in range(num_cols):
            # Colunas 15 = Histórico, 16 = Ações (apenas Finalizado)
            if col == 15:
                value = informacao_impressao if informacao_impressao else ""
            elif col == 16:
                continue
            else:
                value = values.get(col, "")

            # Colunas não editáveis
            if col in (0, 1, 2, 3, 12, 13, 14, 15):  # inclui Histórico
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_count, col, item)

            # Status
            elif col == 4:
                combo = QComboBox()
                all_stages_full = ['Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado']
                if status in all_stages_full:
                    current_index = all_stages_full.index(status)
                else:
                    current_index = 0

                options = [all_stages_full[current_index]]
                if current_index < len(all_stages_full) - 1:
                    next_stage = all_stages_full[current_index + 1]
                    if self.has_permission_for_stage(next_stage):
                        options.append(next_stage)
                if 'Pré-Impressão' not in options and current_index > 0 and self.has_permission_for_stage('Pré-Impressão'):
                    options.append('Pré-Impressão')

                combo.addItems(options)
                combo.setCurrentText(status)
                permitido = self.has_permission_for_stage(status)
                combo.setEnabled(permitido)
                if permitido:
                    combo.currentIndexChanged.connect(
                        lambda idx, c=combo, l=lote: self.update_status(l, c.currentText())
                    )
                table.setCellWidget(row_count, col, combo)

            # M e C (combo "ok")
            elif col in (5, 6):
                combo = QComboBox()
                combo.addItems(["", "ok"])
                combo.setCurrentText(str(value) if value else "")
                permitido = self.has_permission_for_stage(status)
                combo.setEnabled(permitido)
                if permitido:
                    combo.currentIndexChanged.connect(
                        lambda idx, c=combo, l=lote, col=col: self.update_m_c_field(l, c.currentText(), col)
                    )
                table.setCellWidget(row_count, col, combo)

            # MC (combo com opções "ok", "sem color", etc.)
            elif col == 7:
                combo = QComboBox()
                combo.addItems(["", "ok", "sem color"])
                combo.setCurrentText(str(value) if value else "")
                permitido = self.has_permission_for_stage(status)
                combo.setEnabled(permitido)
                if permitido:
                    combo.currentIndexChanged.connect(
                        lambda idx, c=combo, l=lote: self.update_mc_field(l, c.currentText())
                    )
                table.setCellWidget(row_count, col, combo)

            # Maquina PB e Maquina CL (combobox com opções fixas)
            elif col in (8, 9):
                combo = QComboBox()
                if col == 8:
                    combo.addItems(MAQUINA_PB_OPTIONS)
                else:
                    combo.addItems(MAQUINA_CL_OPTIONS)
                combo.setCurrentText(str(value) if value else "")
                permitido = self.has_permission_for_stage(status)
                combo.setEnabled(permitido)
                if permitido:
                    field_name = 'maquina_PB' if col == 8 else 'maquina_CL'
                    combo.currentIndexChanged.connect(
                        lambda idx, c=combo, l=lote, f=field_name: self.update_maquina_field(l, c.currentText(), f)
                    )
                table.setCellWidget(row_count, col, combo)

            # Observações
            elif col in (10, 11):
                item = QTableWidgetItem(str(value) if value is not None else "")
                if not self.has_permission_for_stage(status):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_count, col, item)

        # Botão Detalhes (só na aba Finalizado)
        if num_cols == 17:
            btn_detalhes = QPushButton("Detalhes")
            btn_detalhes.setStyleSheet("background-color: #4CAF50; color: white;")
            btn_detalhes.clicked.connect(lambda checked, l=lote: self.show_historico_detalhes(l))
            table.setCellWidget(row_count, 16, btn_detalhes)

    # ================== ATUALIZAÇÕES DE CAMPOS ==================
    def update_mc_field(self, lote, value):
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET mc = ? WHERE lote = ?", (value, lote))
        conn.commit()
        conn.close()
        print(f"Atualizado MC para '{value}' no lote {lote}")

    def update_maquina_field(self, lote, value, field):
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE pedidos SET {field} = ? WHERE lote = ?", (value, lote))
        conn.commit()
        conn.close()

    # Os demais métodos (update_m_c_field, update_observations, etc.) permanecem iguais,
    # apenas com os índices ajustados quando necessário. Exemplo: observações agora estão nas colunas 10 e 11.

    def update_observations(self, lote, new_text, column):
        field = 'observacoes_impressao' if column == 10 else 'observacoes_acabamento'
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE pedidos SET {field} = ? WHERE lote = ?", (new_text, lote))
        conn.commit()
        conn.close()

    def update_m_c_field(self, lote, value, column):
        field_map = {5: 'M', 6: 'C'}
        if column not in field_map:
            return
        field_name = field_map[column]

        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE pedidos SET {field_name} = ? WHERE lote = ?", (value or "", lote))
            conn.commit()
            print(f"Atualizado {field_name} para '{value}' no lote {lote}")

            if value == "ok" and column in (5, 6):
                current_status = 'Miolo' if column == 5 else 'Capa'
                responsible_list = RESPONSIBLES_BY_STAGE.get('Impressão', [])
                responsible = self.ask_for_responsible(responsible_list, current_status)
                if responsible:
                    self.update_responsible(lote, current_status, responsible, current_status)

                cursor.execute("SELECT M, C, status FROM pedidos WHERE lote = ?", (lote,))
                result = cursor.fetchone()
                if result:
                    m_value, c_value, status = result
                    if m_value == "ok" and c_value == "ok" and status == "Impressão":
                        reply = QMessageBox.question(
                            self, 'Confirmação',
                            'Capa e Miolo estão prontos. Deseja mudar o status para "Encadernação"?',
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                        )
                        if reply == QMessageBox.Yes:
                            cursor.execute("UPDATE pedidos SET status = 'Encadernação' WHERE lote = ?", (lote,))
                            conn.commit()
                            responsible_list = RESPONSIBLES_BY_STAGE.get('Impressão', [])
                            responsible = self.ask_for_responsible(responsible_list, 'Impressão')
                            if responsible:
                                self.update_responsible(lote, 'Impressão', responsible, status)
                                self.move_row_to_new_table(lote, 'Impressão', 'Encadernação')
                            else:
                                QMessageBox.warning(self, 'Operação Cancelada', 'Mudança de status cancelada.')

    def cell_clicked(self, row, column):
        # Caminho do Pedido agora está na coluna 13
        if column == 13:
            table = self.tables[self.tabs.tabText(self.tabs.currentIndex())]
            item = table.item(row, column)
            if item:
                caminho = item.text()
                reply = QMessageBox.question(self, 'Abrir Pasta',
                                             "Deseja abrir a pasta?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    if os.path.exists(caminho):
                        subprocess.Popen(f'explorer "{caminho}"')
                    else:
                        QMessageBox.warning(self, 'Erro', 'Caminho não encontrado.')

    def cell_changed(self, row, column):
        current_tab = self.tabs.tabText(self.tabs.currentIndex())
        table = self.tables.get(current_tab)
        if table:
            item = table.item(row, 0)
            if item:
                lote = item.text()
                if column in (10, 11):   # Observações agora 10 e 11
                    new_text_item = table.item(row, column)
                    new_text = new_text_item.text() if new_text_item else ""
                    self.update_observations(lote, new_text, column)

    # Restante do código (status, responsáveis, etc.) mantido, apenas com índices corrigidos
    # ... (demais métodos não alterados em relação à lógica, apenas índices)

    def get_current_status(self, lote):
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM pedidos WHERE lote = ?", (lote,))
        status = cursor.fetchone()
        conn.close()
        return status[0] if status else None

    def update_status(self, lote, new_status):
        current_status = self.get_current_status(lote)
        if not current_status or current_status == new_status:
            return

        if new_status == "Finalizado" and not self.is_admin:
            QMessageBox.warning(self, 'Permissão negada', 'Apenas o administrador pode finalizar pedidos.')
            return

        if new_status == "Finalizado":
            reply = QMessageBox.question(self, 'Finalizar Pedido',
                                         f'Você tem certeza que deseja FINALIZAR o pedido {lote}?\n\n'
                                         'Esta ação moverá o pedido para a aba "Finalizado".',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

        responsible_list = RESPONSIBLES_BY_STAGE.get(current_status, [])
        responsible = self.ask_for_responsible(responsible_list, current_status)
        if responsible:
            if self.confirm_status_change(lote, new_status, current_status):
                self.update_responsible(lote, new_status, responsible, current_status)
                update_database(lote, new_status)
                self.move_row_to_new_table(lote, current_status, new_status)
                if new_status == "Finalizado":
                    QMessageBox.information(self, 'Pedido Finalizado',
                                            f'Pedido {lote} foi finalizado com sucesso!')
            else:
                QMessageBox.warning(self, 'Operação Cancelada', 'Mudança de status cancelada.')
        else:
            QMessageBox.warning(self, 'Operação Cancelada', 'Mudança de status cancelada.')

    def find_row_by_lote(self, lote, table):
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.text() == lote:
                return row
        return -1

    def move_row_to_new_table(self, lote, old_status, new_status):
        old_table = self.tables.get(old_status)
        if not old_table:
            return
        row_index = self.find_row_by_lote(lote, old_table)
        if row_index == -1:
            return
        old_table.removeRow(row_index)

        if new_status == 'Finalizado' and not self.is_admin:
            return

        new_row_data = fetch_single_lote_data(lote)
        if new_row_data:
            self.add_row_to_table(new_row_data)
        else:
            self.load_data_into_tables()

    def ask_for_responsible(self, responsible_list, current_status):
        if not responsible_list:
            return None
        dialog = QDialog()
        layout = QVBoxLayout()
        combo = QComboBox()
        combo.addItems(responsible_list)
        layout.addWidget(QLabel(f'Escolha o responsável que finalizou o {current_status}:'))
        layout.addWidget(combo)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.rejected.connect(dialog.reject)
        layout.addWidget(buttonBox)
        dialog.setLayout(layout)
        if dialog.exec() == QDialog.Accepted:
            return combo.currentText()
        return None

    def confirm_status_change(self, lote, new_status, current_status):
        reply = QMessageBox.question(self, 'Confirmação de Mudança de Status',
                                     f'Você tem certeza que deseja mudar o status de "{current_status}" para "{new_status}"?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def update_responsible(self, lote, new_status, responsible, current_status):
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT informacao_impressao FROM pedidos WHERE lote = ?", (lote,))
        result = cursor.fetchone()
        current_info = result[0] if result else ""

        info_dict = {}
        if current_info:
            pairs = current_info.split(',')
            for pair in pairs:
                if ':' in pair:
                    status_key, resp = pair.split(':')
                    info_dict[status_key] = resp

        info_dict[current_status] = responsible
        ordered_status = ['Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado', 'Miolo', 'Capa']
        updated_info = ','.join(
            f"{status}:{info_dict.get(status, '')}"
            for status in ordered_status if status in info_dict
        )
        cursor.execute("UPDATE pedidos SET informacao_impressao = ? WHERE lote = ?", (updated_info, lote))
        conn.commit()
        conn.close()

    def show_historico_detalhes(self, lote):
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT informacao_impressao FROM pedidos WHERE lote = ?", (lote,))
        result = cursor.fetchone()
        conn.close()

        if not result or not result[0]:
            QMessageBox.information(self, "Histórico", "Nenhum histórico registrado.")
            return

        historico_raw = result[0]
        pares = [p.strip() for p in historico_raw.split(',') if p.strip()]
        msg = f"<h3>Histórico do Lote {lote}</h3><ul>"
        for par in pares:
            if ':' in par:
                etapa, resp = par.split(':', 1)
                msg += f"<li><b>{etapa.strip()}:</b> {resp.strip()}</li>"
            else:
                msg += f"<li>{par}</li>"
        msg += "</ul>"

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detalhes do Lote {lote}")
        layout = QVBoxLayout()
        label = QLabel(msg)
        label.setWordWrap(True)
        layout.addWidget(label)
        fechar_btn = QPushButton("Fechar")
        fechar_btn.clicked.connect(dlg.accept)
        layout.addWidget(fechar_btn)
        dlg.setLayout(layout)
        dlg.exec()

# ---------- Inicialização ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='light_orange.xml')
    login_window = LoginWindow()
    if login_window.exec() == QDialog.Accepted:
        window = PedidoApp(login_window.user_sector)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit()