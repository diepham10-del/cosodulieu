import sys
import mysql.connector
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QMessageBox, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QLabel, QDateTimeEdit, QStyledItemDelegate
)
from PyQt5.QtCore import Qt, QDateTime

class DateItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QDateTimeEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if value:
            dt = QDateTime.fromString(value, "yyyy-MM-dd HH:mm:ss")
            if not dt.isValid():
                dt = QDateTime.fromString(value, "yyyy-MM-dd")
            if dt.isValid():
                editor.setDateTime(dt)
            else:
                editor.setDateTime(QDateTime.currentDateTime())
        else:
            editor.setDateTime(QDateTime.currentDateTime())

    def setModelData(self, editor, model, index):
        value = editor.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        model.setData(index, value, Qt.EditRole)

class AddRecordDialog(QDialog):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm bản ghi mới")
        self.columns = columns
        self.inputs = {}
        
        layout = QFormLayout()
        for idx, col in enumerate(columns):
            col_type = col['Type'].decode('utf-8').lower() if isinstance(col['Type'], bytes) else col['Type'].lower()
            if 'date' in col_type or 'time' in col_type:
                editor = QDateTimeEdit(self)
                editor.setCalendarPopup(True)
                editor.setDateTime(QDateTime.currentDateTime())
                editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            else:
                editor = QLineEdit()
                
            self.inputs[col['Field']] = editor
            is_required = col['Null'] == 'NO' and 'auto_increment' not in col['Extra']
            label_text = col['Field'] + (" (*)" if is_required else "")
            layout.addRow(QLabel(label_text), editor)
            
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.setLayout(layout)
        
    def get_data(self):
        data = {}
        for col, editor in self.inputs.items():
            if isinstance(editor, QDateTimeEdit):
                data[col] = editor.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            else:
                data[col] = editor.text()
        return data

class MySQLTableTab(QWidget):
    def __init__(self, connection, table_name):
        super().__init__()
        self.conn = connection
        self.table_name = table_name
        self.columns = []
        self.primary_keys = []
        self.data_store = [] 
        self.is_updating = False
        
        self.setup_ui()
        self.load_schema()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        self.table_widget = QTableWidget()
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.cellChanged.connect(self.on_cell_changed)
        layout.addWidget(self.table_widget)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Thêm dữ liệu (Insert)")
        del_btn = QPushButton("Xóa dòng đã chọn (Delete)")
        refresh_btn = QPushButton("Làm mới bảng (Refresh)")
        
        add_btn.clicked.connect(self.add_row)
        del_btn.clicked.connect(self.delete_row)
        refresh_btn.clicked.connect(self.load_data)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(refresh_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def load_schema(self):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(f"DESCRIBE {self.table_name}")
        self.columns = cursor.fetchall()
        cursor.close()
        self.primary_keys = [c['Field'] for c in self.columns if c['Key'] == 'PRI']
        
        self.table_widget.setColumnCount(len(self.columns))
        self.table_widget.setHorizontalHeaderLabels([c['Field'] for c in self.columns])

        for col_idx, col in enumerate(self.columns):
            col_type = col['Type'].decode('utf-8').lower() if isinstance(col['Type'], bytes) else col['Type'].lower()
            if 'date' in col_type or 'time' in col_type:
                self.table_widget.setItemDelegateForColumn(col_idx, DateItemDelegate(self.table_widget))
        
    def load_data(self):
        self.is_updating = True
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute(f"SELECT * FROM {self.table_name}")
            rows = cursor.fetchall()
        except Exception as e:
            QMessageBox.warning(self, "Lỗi tải bảng", str(e))
            self.is_updating = False
            return
            
        self.table_widget.setRowCount(len(rows))
        self.data_store = []
        
        for row_idx, row in enumerate(rows):
            self.data_store.append(row.copy())
            for col_idx, col in enumerate(self.columns):
                val = row[col['Field']]
                item = QTableWidgetItem(str(val) if val is not None else "")
                self.table_widget.setItem(row_idx, col_idx, item)
                
        cursor.close()
        self.is_updating = False
        
    def add_row(self):
        dialog = AddRecordDialog(self.columns, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            fields, values = [], []
            for col in self.columns:
                val = data[col['Field']]
                if val == '' and col['Null'] == 'YES':
                    continue
                if val == '' and 'auto_increment' in col['Extra']:
                    continue
                fields.append(col['Field'])
                values.append(val)
                
            placeholders = ", ".join(["%s"] * len(fields))
            query = f"INSERT INTO {self.table_name} ({', '.join(fields)}) VALUES ({placeholders})"
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, values)
                self.conn.commit()
                QMessageBox.information(self, "Thành công", "Thêm dữ liệu mới thành công!")
                self.load_data()
            except mysql.connector.Error as err:
                QMessageBox.critical(self, "Lỗi Insert (Có thể do Trigger/Khóa chính)", f"Mã lỗi MySQL:\n{err.msg}")
                
    def delete_row(self):
        row = self.table_widget.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn hoặc click vào một ô trong dòng muốn xóa!")
            return
            
        confirm = QMessageBox.question(self, "Xác nhận", "Bạn có chắc chắn muốn xóa bản ghi này?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.No: return
        
        row_data = self.data_store[row]
        if not self.primary_keys:
            QMessageBox.warning(self, "Lỗi hệ thống", "Bảng này không có Primary Key, không thể xác định vị trí xóa đúng!")
            return
            
        conditions = " AND ".join([f"{pk} = %s" for pk in self.primary_keys])
        params = [row_data[pk] for pk in self.primary_keys]
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"DELETE FROM {self.table_name} WHERE {conditions}", params)
            self.conn.commit()
            QMessageBox.information(self, "Thành công", "Đã XÓA dữ liệu.")
            self.load_data()
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Lỗi Xóa", f"Chi tiết:\n{err.msg}")
            
    def on_cell_changed(self, row, column):
        if self.is_updating: return
        self.is_updating = True 
        
        col_name = self.columns[column]['Field']
        new_val = self.table_widget.item(row, column).text()
        
        row_data = self.data_store[row]
        if not self.primary_keys:
            QMessageBox.warning(self, "Chú ý", "Bảng không có khóa chính, ứng dụng không thể hỗ trợ cập nhật trực tiếp.")
            self.load_data()
            return
            
        conditions = " AND ".join([f"{pk} = %s" for pk in self.primary_keys])
        params = [new_val] + [row_data[pk] for pk in self.primary_keys]
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"UPDATE {self.table_name} SET {col_name} = %s WHERE {conditions}", params)
            self.conn.commit()
            self.data_store[row][col_name] = new_val
        except mysql.connector.Error as err:
            QMessageBox.critical(self, "Lỗi Update", f"Sửa dữ liệu không thành công:\n{err.msg}")
            self.conn.rollback()
            self.load_data()
            return
        finally:
            self.is_updating = False

class CinemaManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần mềm Quản lý Rạp phim (Hệ CSDL: MySQL + Triggers)")
        self.resize(1100, 700)
        
        if not self.connect_db():
            return
            
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        cursor = self.conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        cursor.close()
        
        for table in tables:
            tab = MySQLTableTab(self.conn, table)
            self.tabs.addTab(tab, table.upper())
            
    def connect_db(self):
        try:
            self.conn = mysql.connector.connect(
                host="127.0.0.1",
                user="root",
                password="khanhtuan1703@",
                database="cinema_management"
            )
            return True
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Kết Nối", f"Lỗi:\n{e}")
            sys.exit(1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = CinemaManager()
    window.show()
    sys.exit(app.exec_())
