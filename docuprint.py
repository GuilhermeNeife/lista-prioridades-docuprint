import sys
import os
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem, QComboBox, QLabel, QPushButton, QProgressBar, QDateEdit, QMessageBox
from PySide6.QtWidgets import QDialog, QLineEdit, QHBoxLayout
from PySide6.QtCore import Qt, QDate
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qt_material import apply_stylesheet
import subprocess



# Dicionário de usuários: senha e setor
USERS = {
    'Admin': ('123', ['Pré-Impressão','Impressão','Encadernação','Refile','Expedição','Finalizado']),   # Usuário administrador com acesso a todas as abas
    'Pré-impressao': ('123', 'Pré-Impressão'),
    'Impressao': ('123', 'Impressão'),
    'Acabamento': ('123', ['Encadernação','Refile']),
    'Expedição': ('123', ['Expedição','Finalizado']),

}

# Conecta ao banco de dados e obtém os pedidos
def load_data():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("SELECT lote, data_hora_entrada, cliente, prazo_grafica, status, observacoes_impressao, observacoes_acabamento, descricao, caminho_do_pedido, Total, informacao_impressao FROM pedidos ORDER BY lote")
    rows = cursor.fetchall()
    conn.close()
    return rows

# Atualiza o banco de dados com o novo status
def update_database(lote, new_status):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE pedidos SET status = ? WHERE lote = ?", (new_status, lote))
    conn.commit()
    conn.close()

# Envia um e-mail notificando a mudança de status
def send_email(lote, new_status):
    sender_email = "guilherme.neife@docuprint.com.br"  # E-mail do usuário
    password = "3#5QtvVG"  # Senha do e-mail
    receivers = ["marlusm@docuprint.com.br", "guineife@hotmail.com"]  # E-mails dos destinatários

    message = MIMEMultipart()
    message["Subject"] = f"Notificação lote {lote}"
    message["From"] = sender_email
    message["To"] = ", ".join(receivers)

    text = f"""\
    Olá, Tudo bem?

    Status do Lote: {lote}
    Mudou para: {str.upper(new_status)}.

    Atenciosamente,
    Equipe Docuprint"""

    part = MIMEText(text, "plain")
    message.attach(part)

    try:
        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receivers, message.as_string())
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}")


def count_books_and_orders_by_stage():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    # Esta consulta retorna o total de pedidos e livros agrupados por setor
    cursor.execute("SELECT status, COUNT(*), SUM(Total) FROM pedidos GROUP BY status")
    data = cursor.fetchall()
    conn.close()
    return {row[0]: {'total_pedidos': row[1], 'total_livros': row[2]} for row in data}

def check_delays_by_stage():
    from datetime import datetime
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    # Esta consulta verifica os atrasos por setor
    cursor.execute("SELECT status, COUNT(*) FROM pedidos WHERE prazo_grafica < ? GROUP BY status", (today,))
    delays = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in delays}




class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(500, 300, 300, 200)
        
        self.user_sector = None  # Armazena o setor do usuário logado

        layout = QVBoxLayout()
        
        # Combobox para usuários
        self.username_combo = QComboBox(self)
        self.username_combo.addItems(USERS.keys())
        layout.addWidget(self.username_combo)
        
        # Senha
        password_layout = QHBoxLayout()
        self.password = QLineEdit(self)
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.password)
        
        # Botão para mostrar/ocultar senha
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
            self.user_sector = user_info[1]  # Armazena o setor do usuário
            self.accept()
        else:
            QMessageBox.warning(self, 'Login Failed', 'Invalid username or password')



# Classe principal do aplicativo
class PedidoApp(QMainWindow):
    def __init__(self, user_sector):
        super().__init__()
        self.setWindowTitle("Gerenciamento de Pedidos")
        self.setGeometry(100, 100, 1200, 600)
        self.user_sector = user_sector  # Setor do usuário logado

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.stages = ['Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado', 'Concluido']
        
        # Removendo a aba 'Concluido' antes de criar as abas
        if 'Concluido' in self.stages:
            self.stages.remove('Concluido')

        self.create_tabs()
        self.create_dashboard_tab()

    def create_tabs(self):
        self.tables = {}
        
        for stage in self.stages:
            table_widget = QWidget()
            layout = QVBoxLayout()

            table = QTableWidget()
            table.setColumnCount(10)
            table.setHorizontalHeaderLabels(['Lote', 'Data/Hora Entrada', 'Cliente', 'Prazo Gráfica', 'Status', 'Observações Impressão', 'Observações Acabamento', 'Descrição', 'Caminho do Pedido', 'Total'])
            if self.user_sector == stage or self.user_sector == "Admin":
                table.cellChanged.connect(self.cell_changed)
                table.cellClicked.connect(self.cell_clicked)
            else:
                table.setToolTip("Você não tem permissão para editar nesta aba.")

            self.setup_table_styles(table)
            layout.addWidget(table)
            table_widget.setLayout(layout)
            self.tabs.addTab(table_widget, stage)
            self.tables[stage] = table

        self.load_data_into_tables()





    def create_dashboard_tab(self):
        dashboard_widget = QWidget()
        dashboard_layout = QVBoxLayout()

        # ComboBox para seleção de setor
        self.combo_filter = QComboBox()
        self.combo_filter.addItem("Geral")
        self.combo_filter.addItems(self.stages)  # Adiciona os setores já definidos
        self.combo_filter.currentIndexChanged.connect(self.update_graph)
        dashboard_layout.addWidget(self.combo_filter)

        # Configuração do canvas para gráfico
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        dashboard_layout.addWidget(self.canvas)

        dashboard_widget.setLayout(dashboard_layout)
        self.tabs.addTab(dashboard_widget, "Dashboard")

        self.update_graph()  # Inicia com o gráfico geral

    def update_graph(self):
        sector = self.combo_filter.currentText()
        self.figure.clear()  # Limpa os gráficos anteriores

        data = count_books_and_orders_by_stage()
        delays = check_delays_by_stage()

        if sector == "Geral":
            sectors = self.stages
        else:
            sectors = [sector]

        total_pedidos = [data.get(s, {'total_pedidos': 0})['total_pedidos'] for s in sectors]
        total_livros = [data.get(s, {'total_livros': 0})['total_livros'] for s in sectors]
        delay_counts = [delays.get(s, 0) for s in sectors]

        indices = range(len(sectors))
        width = 0.25  # Largura das barras

        # Usando add_subplot para adicionar os eixos à figura existente
        ax = self.figure.add_subplot(111)  # 111 significa 1x1 grid, primeira subplot

        bar1 = ax.bar([i - width for i in indices], total_pedidos, width, label='Total de Pedidos', color='b')
        bar2 = ax.bar(indices, total_livros, width, label='Total de Livros', color='g')
        bar3 = ax.bar([i + width for i in indices], delay_counts, width, label='Atrasados', color='r')

        ax.set_title('Comparativo por Setor')
        ax.set_xlabel('Setor')
        ax.set_xticks(indices)
        ax.set_xticklabels(sectors, rotation=45, ha='right')
        ax.legend()

        self.add_bar_labels(bar1, ax)
        self.add_bar_labels(bar2, ax)
        self.add_bar_labels(bar3, ax)

        self.figure.tight_layout()
        self.canvas.draw()

    def add_bar_labels(self, bars, ax):
        for bar in bars:
            height = bar.get_height()
            ax.annotate('{}'.format(height),
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')


    def fetch_data(self, sector):
        if sector == "Geral":
            return count_books_by_stage()  # type: ignore # Retorna dados de todos os setores
        else:
            return {sector: count_books_by_stage().get(sector, 0)}  # type: ignore # Retorna dados de um setor específico


        
    
    
    # Cria as abas e suas respectivas tabelas
    def create_tabs(self):
        self.tables = {}

        for stage in self.stages:
            table_widget = QWidget()
            layout = QVBoxLayout()

            table = QTableWidget()
            table.setColumnCount(10)
            table.setHorizontalHeaderLabels(['Lote', 'Data/Hora Entrada', 'Cliente', 'Prazo Gráfica', 'Status', 'Observações Impressão', 'Observações Acabamento', 'Descrição', 'Caminho do Pedido', 'total'])
            table.cellChanged.connect(self.cell_changed)  # Conecta o evento de edição de célula
            table.cellClicked.connect(self.cell_clicked)  # Conecta o evento de clique na célula

            self.setup_table_styles(table)

            layout.addWidget(table)
            table_widget.setLayout(layout)
            self.tabs.addTab(table_widget, stage)

            self.tables[stage] = table  # Salvando referência da tabela

        # Carrega os dados na interface
        self.load_data_into_tables()

    def setup_table_styles(self, table):
        # Configurações de estilo para a tabela
        table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: orange;
                color: black;
                padding: 4px;
                border: none; /* Remove as bordas */
                font-size: 10px; /* Ajuste o tamanho da fonte */
                height: 30px; /* Altura do cabeçalho */
                font-weight: bold;
                text-align: center;

            }
        """)
        # Configurações de largura das colunas
        widths = [50, 120, 60, 95, 150, 170, 150, 280, 120, 50]
        for i, width in enumerate(widths):
            table.setColumnWidth(i, width)

        # Configurações de altura da linha vertical
        table.verticalHeader().setDefaultSectionSize(40)


    def load_data_into_tables(self):
        data = load_data()

        # Desativar temporariamente o sinal cellChanged
        for table in self.tables.values():
            table.cellChanged.disconnect(self.cell_changed)

        # Limpa as tabelas antes de recarregar os dados
        for table in self.tables.values():
            table.setRowCount(0)

    
        for row in data:
            self.add_row_to_table(row)

        # Reativar o sinal cellChanged após todos os dados serem carregados
        for table in self.tables.values():
            table.cellChanged.connect(self.cell_changed)

    def add_row_to_table(self, row):
        try:
            lote, data_hora_entrada, cliente, prazo_grafica, status, observacoes_impressao, observacoes_acabamento, descricao, caminho_do_pedido, Total, informacao_impressao = row
        except ValueError:
            print("Erro: número de valores não corresponde ao esperado.")
            return

        table = self.tables[status] if status in self.tables else self.tables['Pré-Impressão']
        row_count = table.rowCount()
        table.insertRow(row_count)

        for col_index, data in enumerate(row):
            item = QTableWidgetItem(str(data))
            if col_index not in [5, 6, 8]:  # Editáveis apenas observações e caminho do pedido
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if col_index == 4:  # Coluna de status com ComboBox
                combo = QComboBox()
                current_index = self.stages.index(status)
                # Adicionar apenas o status anterior, atual e próximo
                options = [self.stages[current_index]]  # Adicionar o status atual
                if current_index > 0:
                    options.insert(0, self.stages[current_index - 1])  # Adicionar o status anterior
                if current_index < len(self.stages) - 1:
                    options.append(self.stages[current_index + 1])  # Adicionar o próximo status
                if 'Pré-Impressão' not in options:
                    options.insert(0, 'Pré-Impressão')  # Sempre permitir voltar para Pré-Impressão
                combo.addItems(options)
                combo.setCurrentText(status)
                combo.currentIndexChanged.connect(lambda index, lote=lote, combo=combo: self.update_status(lote, combo.currentText()))
                table.setCellWidget(row_count, col_index, combo)
            else:
                table.setItem(row_count, col_index, item)



    def cell_clicked(self, row, column):
        # Verificar se a coluna clicada é "Caminho do Pedido" (índice 8)
        if column == 8:
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
        item = self.tables[self.tabs.tabText(self.tabs.currentIndex())].item(row, 0)
        if item:
            lote = item.text()  # Correto o erro de digitação aqui
            if column in [5, 6]:  # Colunas de observações
                new_text = self.tables[self.tabs.tabText(self.tabs.currentIndex())].item(row, column).text()
                if new_text:
                    self.update_observations(lote, new_text, column)
        else:
            print(f"Erro: Item não encontrado na linha {row}, coluna 0")

    def update_observations(self, lote, new_text, column):
        field = 'observacoes_impressao' if column == 5 else 'observacoes_acabamento'
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(f"UPDATE pedidos SET {field} = ? WHERE lote = ?", (new_text, lote))
        conn.commit()
        conn.close()

    def update_status(self, lote, new_status):
        reply = QMessageBox.question(self, 'Confirmação de Mudança de Status',
                                     'Você tem certeza que deseja mudar o status?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            update_database(lote, new_status)  # Atualiza o status no banco de dados
            send_email(lote, new_status)  # Envia o e-mail notificando a mudança de status
            self.load_data_into_tables()  # Recarrega os dados para refletir a mudança na interface
        else:
            self.load_data_into_tables()  # Recarrega os dados sem mudança para reverter a seleção do ComboBox

# Configuração do caminho do banco de dados
database_path = "C:\\Users\\gneife\\Desktop\\pedidos.db"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='light_orange.xml')
    login_window = LoginWindow()

    if login_window.exec() == QDialog.Accepted:
        window = PedidoApp(login_window.user_sector)  # Passa o setor do usuário
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit()

