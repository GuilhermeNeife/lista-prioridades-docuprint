import sys
import os
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QDialogButtonBox, QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox, QLabel,
    QPushButton, QMessageBox, QDialog, QLineEdit, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from qt_material import apply_stylesheet
import subprocess

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

# Opções fixas para as máquinas
MAQUINA_PB_OPTIONS = ["", "OCÉ 1", "OCÉ 3", "BALTORO", "ATEXCO"]
MAQUINA_CL_OPTIONS = ["", "RICOH", "BALTORO"]

database_path = "Q:\\___LISTA DE PRIORIDADES\\GUILHERME\\pedidos.db"

# ---------- Funções de banco de dados ----------
def load_data(is_admin=False):
    """
    Carrega todos os pedidos. Se não for admin, exclui os que já estão finalizados.
    """
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    if is_admin:
        cursor.execute("""
            SELECT lote, data_hora_entrada, cliente, prazo_grafica, status, 
                   M, C, maquina_PB, maquina_CL, 
                   observacoes_impressao, observacoes_acabamento, 
                   descricao, caminho_do_pedido, Total, informacao_impressao 
            FROM pedidos 
            ORDER BY lote
        """)
    else:
        cursor.execute("""
            SELECT lote, data_hora_entrada, cliente, prazo_grafica, status, 
                   M, C, maquina_PB, maquina_CL, 
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
               M, C, maquina_PB, maquina_CL, 
               observacoes_impressao, observacoes_acabamento, 
               descricao, caminho_do_pedido, Total, informacao_impressao 
        FROM pedidos 
        WHERE lote = ?
    """, (lote,))
    row = cursor.fetchone()
    conn.close()
    return row

# ---------- Janela de Login (inalterada) ----------
class LoginWindow(QDialog):
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
        self.setGeometry(100, 100, 1200, 600)
        self.user_sector = user_sector
        self.setWindowIcon(QIcon("Q:\\___LISTA DE PRIORIDADES\\GUILHERME\\LOGOS\\favicon.ico"))

        # Define se é admin (pode ver Finalizados)
        if isinstance(user_sector, list):
            self.is_admin = 'Admin' in user_sector
            self.user_sectors = user_sector
        else:
            self.is_admin = (user_sector == 'Admin')
            self.user_sectors = [user_sector]

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Monta a lista de abas visíveis para este usuário
        all_stages = ['Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado']
        if self.is_admin:
            self.stages = all_stages
        else:
            self.stages = [stage for stage in all_stages if stage != 'Finalizado']

        self.create_tabs()
        # Sem timer – a interface fica fluida e só atualiza quando necessário

    def has_permission_for_stage(self, stage):
        """Verifica se o usuário atual tem permissão para aquela etapa."""
        return self.is_admin or (stage in self.user_sectors)

    def create_tabs(self):
        self.tables = {}
        for stage in self.stages:
            table_widget = QWidget()
            layout = QVBoxLayout()
            table = QTableWidget()
            table.setColumnCount(14)
            table.setHorizontalHeaderLabels([
                'Lote', 'Data/Hora Entrada', 'Cliente', 'Prazo Gráfica',
                'Status', 'M', 'C', 'Maquina PB', 'Maquina CL',
                'Obs. Impressão', 'Obs. Acabamento', 'Descrição',
                'Caminho do Pedido', 'Total'
            ])

            # Permissão de edição para a aba atual
            permitido = self.has_permission_for_stage(stage)
            if permitido:
                table.cellChanged.connect(self.cell_changed)
                table.cellClicked.connect(self.cell_clicked)

            self.setup_table_styles(table)
            layout.addWidget(table)
            table_widget.setLayout(layout)
            self.tabs.addTab(table_widget, stage)
            self.tables[stage] = table

        self.load_data_into_tables()

    def setup_table_styles(self, table):
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
        widths = [43, 120, 58, 95, 130, 70, 70, 80, 80, 140, 150, 250, 130, 40]
        for i, width in enumerate(widths):
            table.setColumnWidth(i, width)
        table.verticalHeader().setDefaultSectionSize(40)

    def load_data_into_tables(self):
        data = load_data(is_admin=self.is_admin)

        # Desconecta o sinal globalmente durante a recarga
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
                 M, C, maquina_PB, maquina_CL, obs_imp, obs_acab,
                 descricao, caminho, Total, informacao_impressao) = row
                if status == "Concluído":
                    continue
                self.add_row_to_table(row)
            except ValueError as e:
                print(f"Erro ao desestruturar linha: {e} | Dados: {row}")
                continue

        # Reconecta o sinal apenas nas abas com permissão
        for stage, table in self.tables.items():
            permitido = self.has_permission_for_stage(stage)
            if permitido:
                table.cellChanged.connect(self.cell_changed)

    def add_row_to_table(self, row):
        try:
            (lote, data_hora_entrada, cliente, prazo_grafica, status,
             M, C, maquina_PB, maquina_CL, obs_imp, obs_acab,
             descricao, caminho, Total, _) = row
        except ValueError:
            return

        # Se o status é Finalizado e o usuário não é admin, não mostra
        if status == 'Finalizado' and not self.is_admin:
            return

        table = self.tables.get(status, self.tables['Pré-Impressão'])
        row_count = table.rowCount()
        table.insertRow(row_count)

        values = {
            0: lote, 1: data_hora_entrada, 2: cliente, 3: prazo_grafica,
            4: status, 5: M, 6: C, 7: maquina_PB, 8: maquina_CL,
            9: obs_imp, 10: obs_acab, 11: descricao, 12: caminho, 13: Total
        }

        for col in range(14):
            value = values[col]

            # Colunas somente leitura
            if col in (0, 1, 2, 3, 11, 12, 13):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_count, col, item)

            # Status (combobox)
            elif col == 4:
                combo = QComboBox()
                # Determina o índice atual
                all_stages_full = ['Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado']
                if status in all_stages_full:
                    current_index = all_stages_full.index(status)
                else:
                    current_index = 0

                options = [all_stages_full[current_index]]

                # Só adiciona a próxima etapa se o usuário tiver permissão para ela
                if current_index < len(all_stages_full) - 1:
                    next_stage = all_stages_full[current_index + 1]
                    if self.has_permission_for_stage(next_stage):
                        options.append(next_stage)

                # Permite voltar para Pré-Impressão (correção), desde que o usuário tenha permissão
                if 'Pré-Impressão' not in options and current_index > 0 and self.has_permission_for_stage('Pré-Impressão'):
                    options.append('Pré-Impressão')

                combo.addItems(options)
                combo.setCurrentText(status)

                # Só habilita se o usuário pode editar a etapa atual (a aba em que o lote está)
                permitido = self.has_permission_for_stage(status)
                combo.setEnabled(permitido)
                if permitido:
                    combo.currentIndexChanged.connect(
                        lambda idx, c=combo, l=lote: self.update_status(l, c.currentText())
                    )
                table.setCellWidget(row_count, col, combo)

            # M e C (combobox "ok")
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

            # Maquina PB e Maquina CL (combobox com opções fixas)
            elif col in (7, 8):
                combo = QComboBox()
                if col == 7:
                    combo.addItems(MAQUINA_PB_OPTIONS)
                else:
                    combo.addItems(MAQUINA_CL_OPTIONS)
                combo.setCurrentText(str(value) if value else "")
                permitido = self.has_permission_for_stage(status)
                combo.setEnabled(permitido)
                if permitido:
                    field_name = 'maquina_PB' if col == 7 else 'maquina_CL'
                    combo.currentIndexChanged.connect(
                        lambda idx, c=combo, l=lote, f=field_name: self.update_maquina_field(l, c.currentText(), f)
                    )
                table.setCellWidget(row_count, col, combo)

            # Observações (editáveis)
            elif col in (9, 10):
                item = QTableWidgetItem(str(value) if value is not None else "")
                if not self.has_permission_for_stage(status):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_count, col, item)

    # ---------- Eventos ----------
    def cell_clicked(self, row, column):
        if column == 12:  # Caminho do Pedido
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
                if column in (9, 10):   # observações
                    new_text_item = table.item(row, column)
                    new_text = new_text_item.text() if new_text_item else ""
                    self.update_observations(lote, new_text, column)

    def update_observations(self, lote, new_text, column):
        field = 'observacoes_impressao' if column == 9 else 'observacoes_acabamento'
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE pedidos SET {field} = ? WHERE lote = ?", (new_text, lote))
        conn.commit()
        conn.close()

    def update_maquina_field(self, lote, value, field):
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE pedidos SET {field} = ? WHERE lote = ?", (value, lote))
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

        # Bloqueia mudança para Finalizado se o usuário não for admin
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

        # Se o novo status é Finalizado e o usuário não é admin, o lote simplesmente some da interface
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