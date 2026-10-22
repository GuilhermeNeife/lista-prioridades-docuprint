import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QComboBox, QVBoxLayout, QWidget, QTabWidget, QMessageBox
from PySide6.QtCore import Qt
from qt_material import apply_stylesheet
import sqlite3
import os
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

# Classe principal do aplicativo
class PedidoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciamento de Pedidos")
        self.setGeometry(100, 100, 1200, 600)
        

        self.tabs = QTabWidget()  # Widget de abas
        self.setCentralWidget(self.tabs)

        # Lista de estágios (status)
        self.stages = ['Pré-Impressão', 'Impressão', 'Encadernação', 'Refile', 'Expedição', 'Finalizado']

        # Criando tabelas (abas) para cada estágio
        self.create_tabs()






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

        # Inicializa todos os itens da linha como QTableWidgetItem e ajusta a editabilidade
        for col_index, data in enumerate(row):
            item = QTableWidgetItem(str(data))
            if col_index not in [5, 6, 8]:  # Editáveis apenas observações e caminho do pedido
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if col_index == 4:  # Coluna de status com ComboBox
                combo = QComboBox()
                combo.addItems(self.stages)
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
            update_database(lote, new_status)
            self.load_data_into_tables()
              # Recarrega os dados para mover o pedido para a nova aba
        else:
            self.load_data_into_tables()  # Recarrega sem mudar o status para reverter a seleção do ComboBox



# Configuração do caminho do banco de dados
database_path = "C:\\Users\\gneife\\Desktop\\pedidos.db"

# Executa o aplicativo
app = QApplication(sys.argv)
apply_stylesheet(app, theme='light_orange.xml')  # Aplicando o tema Qt Material
window = PedidoApp()
window.show()
sys.exit(app.exec())