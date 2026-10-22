import sys
import os
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem, QComboBox, QLabel, QPushButton, QProgressBar, QDateEdit, QMessageBox
from PySide6.QtCore import Qt, QDate
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qt_material import apply_stylesheet
import subprocess


# Conecta ao banco de dados e obtém os pedidos
def load_data():
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    cursor.execute("SELECT lote, data_hora_entrada, cliente, prazo_grafica, status, observacoes_impressao, observacoes_acabamento, descricao, caminho_do_pedido, qtd_copias, informacao_impressao FROM pedidos ORDER BY lote")
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
    cursor.execute("SELECT status, COUNT(*), SUM(qtd_copias) FROM pedidos GROUP BY status")
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


# Classe principal do aplicativo
class PedidoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciamento de Pedidos")
        self.setGeometry(100, 100, 1200, 600)

        self.tabs = QTabWidget()  # Widget de abas
        self.setCentralWidget(self.tabs)

        self.stages = ['Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado']
        self.create_tabs()
        self.create_dashboard_tab()  # Chame o método para criar a aba de dashboard

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

        # Criando subplots para pedidos e livros
        ax1 = self.figure.add_subplot(121)  # 1 linha, 2 colunas, posição 1
        ax2 = self.figure.add_subplot(122)  # 1 linha, 2 colunas, posição 2

        # Gráfico de barras para pedidos
        indices = range(len(sectors))
        ax1.bar(indices, total_pedidos, color='blue', label='Total de Pedidos')
        ax1.set_title('Total de Pedidos por Setor')
        ax1.set_xlabel('Setor')
        ax1.set_ylabel('Quantidade de Pedidos')
        ax1.set_xticks(indices)
        ax1.set_xticklabels(sectors, rotation=45, ha='right')

        # Adicionando etiquetas de atrasos no gráfico de pedidos
        for i, delay in enumerate(delay_counts):
            if delay > 0:
                ax1.text(i, total_pedidos[i] + 1, f'Atrasados: {delay}', color='red', ha='center')

        # Gráfico de barras para livros
        ax2.bar(indices, total_livros, color='green', label='Total de Livros')
        ax2.set_title('Total de Livros por Setor')
        ax2.set_xlabel('Setor')
        ax2.set_ylabel('Quantidade de Livros')
        ax2.set_xticks(indices)
        ax2.set_xticklabels(sectors, rotation=45, ha='right')

        # Ajustando o layout para evitar sobreposição de etiquetas
        self.figure.tight_layout()

        self.canvas.draw()


    def fetch_data(self, sector):
        if sector == "Geral":
            return count_books_by_stage()  # Retorna dados de todos os setores
        else:
            return {sector: count_books_by_stage().get(sector, 0)}  # Retorna dados de um setor específico


        
    
    
    # Cria as abas e suas respectivas tabelas
    def create_tabs(self):
        self.tables = {}

        for stage in self.stages:
            table_widget = QWidget()
            layout = QVBoxLayout()

            table = QTableWidget()
            table.setColumnCount(10)
            table.setHorizontalHeaderLabels(['Lote', 'Data/Hora Entrada', 'Cliente', 'Prazo Gráfica', 'Status', 'Observações Impressão', 'Observações Acabamento', 'Descrição', 'Caminho do Pedido', 'Qtd Cópias'])
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
                background-color: lightgray;
                padding: 4px;
                border: none; /* Remove as bordas */
                font-size: 10px; /* Ajuste o tamanho da fonte */
                height: 25px; /* Altura do cabeçalho */
            }
        """)
        # Configurações de largura das colunas
        widths = [50, 95, 60, 95, 130, 170, 170, 230, 205, 80]
        for i, width in enumerate(widths):
            table.setColumnWidth(i, width)

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
            lote, data_hora_entrada, cliente, prazo_grafica, status, observacoes_impressao, observacoes_acabamento, descricao, caminho_do_pedido, qtd_copias, informacao_impressao = row
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

# Executa o aplicativo
app = QApplication(sys.argv)
apply_stylesheet(app, theme='light_orange.xml')  # Aplicando o tema Qt Material
window = PedidoApp()
window.show()
sys.exit(app.exec())
