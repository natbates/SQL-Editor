
print("SQL GUI Made by Nathaniel Bates 10/3/2024, Version 1.0.0")

import sys
import pandas as pd
from PyQt5.QtGui import QTextCursor, QKeyEvent, QFont
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QInputDialog, \
    QMessageBox, QLabel, QLineEdit, QHBoxLayout, QComboBox, QTabWidget, QDialogButtonBox, QTextEdit, QAction, QDialog, \
    QListWidget, QTableWidget, QGridLayout, QSizePolicy, QTableWidgetItem, \
    QSplitter, qApp, QTableView, QFileDialog, QListWidgetItem, QCheckBox, QScrollArea
from PyQt5.QtCore import Qt, QObject, QEvent, QCoreApplication

import mysql.connector

removed_dbs = ["mysql", "information_schema", "performance_schema", "sys"]
defaulthostname = "localhost"

# Widgets
class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item and item.text() == "Table Selection Window":
            event.ignore()
        else:
            super().mouseDoubleClickEvent(event)
class TableWidget(QWidget):
    def __init__(self, tablename, info):
        super().__init__()
        self.tablename = tablename
        self.info = info
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.table_view = QTableWidget()
        self.layout.addWidget(self.table_view)
        self.load_table_structure()
        self.load_table_data()

    def load_table_structure(self):
        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(f"SHOW COLUMNS FROM {self.tablename}")
            self.columns = cursor.fetchall()
            connection.close()
        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Error", f"Failed to load table structure: {err}")

        # Fetch additional information about each column, including whether it's auto-incremented
        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(f"SHOW KEYS FROM {self.tablename} WHERE Key_name = 'PRIMARY'")
            primary_keys = cursor.fetchall()
            primary_key_names = [key["Column_name"] for key in primary_keys]


            for column in self.columns:
                column_name = column["Field"]
                column["auto_increment"] = column_name in primary_key_names and column["Extra"] == "auto_increment"
                column["key_type"] = "P" if column_name in primary_key_names else "F" if column["Key"] == "MUL" else ""

            connection.close()
        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Error", f"Failed to fetch column information: {err}")

    def load_table_data(self):
        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )

            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM {self.tablename}")
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            # Get primary and foreign keys
            primary_keys = self.get_primary_keys()
            foreign_keys = self.get_foreign_keys()

            # Modify column names to include symbols for primary and foreign keys
            modified_column_names = []
            for column_name in column_names:
                if column_name in primary_keys:
                    modified_column_names.append(column_name + " (P)")
                elif column_name in foreign_keys:
                    modified_column_names.append(column_name + " (F)")
                else:
                    modified_column_names.append(column_name)

            self.table_view.setColumnCount(len(modified_column_names))
            self.table_view.setHorizontalHeaderLabels(modified_column_names)

            self.table_view.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    item = QTableWidgetItem(str(val))
                    self.table_view.setItem(i, j, item)

        except mysql.connector.Error as e:
            QMessageBox.warning(self, "Error", f"Failed to execute query: {e}")

    def get_primary_keys(self):
        primary_keys = []
        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(f"SHOW KEYS FROM {self.tablename} WHERE Key_name = 'PRIMARY'")
            primary_keys_info = cursor.fetchall()
            primary_keys = [key_info["Column_name"] for key_info in primary_keys_info]
            connection.close()
        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Error", f"Failed to fetch primary keys: {err}")
        return primary_keys

    def get_foreign_keys(self):
        foreign_keys = []
        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )
            cursor = connection.cursor(dictionary=True)
            cursor.execute(f"SHOW CREATE TABLE {self.tablename}")
            create_table_statement = cursor.fetchone()["Create Table"]

            lines = create_table_statement.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("FOREIGN KEY"):
                    parts = line.split("REFERENCES")
                    constraint_info = parts[0].strip().split("(")
                    column_name = constraint_info[1][1:-1]  # Extract column name
                    foreign_keys.append(column_name)
            connection.close()
        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Error", f"Failed to fetch foreign keys: {err}")
        return foreign_keys

    def get_column_names_and_types(self):
        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )
            cursor = connection.cursor()
            cursor.execute(f"SHOW COLUMNS FROM {self.tablename}")
            columns = cursor.fetchall()
            connection.close()
            # Extract column names and data types from the result set
            names_and_types = [(column[0], column[1]) for column in columns]
            return names_and_types
        except mysql.connector.Error as err:
            print(f"Error retrieving column names and types: {err}")
            return []

# Main classes
class DatabaseManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Database Manager")
        self.databasewindow = None
        self.setFixedSize(320, 500)  # Set fixed size for the window

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()  # Vertical layout
        self.central_widget.setLayout(self.layout)

        # Credentials layout
        self.credentials_layout = QVBoxLayout()  # Vertical layout
        self.layout.addLayout(self.credentials_layout)

        self.hostname_label = QLabel("Hostname:")
        self.credentials_layout.addWidget(self.hostname_label)
        self.hostname_input = QLineEdit(defaulthostname)  # Default hostname
        self.credentials_layout.addWidget(self.hostname_input)

        self.username_label = QLabel("Username:")
        self.credentials_layout.addWidget(self.username_label)
        self.username_input = QLineEdit()
        self.credentials_layout.addWidget(self.username_input)

        self.password_label = QLabel("Password:")
        self.credentials_layout.addWidget(self.password_label)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.credentials_layout.addWidget(self.password_input)

        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_server_and_refresh)
        self.layout.addWidget(self.connect_button)

        # Indicator label for database connection status
        self.connection_status_label = QLabel("Not Connected")  # Default status
        self.connection_status_label.setStyleSheet("color: red")  # Default color
        self.layout.addWidget(self.connection_status_label, alignment=Qt.AlignCenter)

        # Database controls
        self.database_controls_layout = QVBoxLayout()  # Vertical layout
        self.layout.addLayout(self.database_controls_layout)

        self.database_combo_box = QComboBox()
        self.database_controls_layout.addWidget(self.database_combo_box)
        self.database_combo_box.setEnabled(False)

        self.create_database_button = QPushButton("Create Database")
        self.create_database_button.clicked.connect(self.create_database)
        self.database_controls_layout.addWidget(self.create_database_button)

        self.delete_database_button = QPushButton("Delete Database")
        self.delete_database_button.clicked.connect(self.confirm_delete_database)
        self.database_controls_layout.addWidget(self.delete_database_button)

        self.rename_database_button = QPushButton("Rename Database")
        self.rename_database_button.clicked.connect(self.rename_database)
        self.database_controls_layout.addWidget(self.rename_database_button)

        self.load_database_button = QPushButton("Load Database")
        self.load_database_button.clicked.connect(self.load_database)
        self.database_controls_layout.addWidget(self.load_database_button)

        self.database_info_label = QLabel()
        self.layout.addWidget(self.database_info_label)

        self.database_info_label.hide()

        # Disable database controls by default
        self.set_database_controls_enabled(False)

        # Connect QLineEdit widgets to connect_to_server_and_refresh method
        self.hostname_input.returnPressed.connect(self.connect_to_server_and_refresh)
        self.username_input.returnPressed.connect(self.connect_to_server_and_refresh)
        self.password_input.returnPressed.connect(self.connect_to_server_and_refresh)


    def create_database(self):
        new_database_name, ok = QInputDialog.getText(self, "Create Database", "Enter database name:")
        if ok:
            # Establish connection
            connection = self.connect_to_server()

            if connection is not None:
                # Create cursor
                cursor = connection.cursor()

                try:
                    # Execute CREATE DATABASE query
                    cursor.execute(f"CREATE DATABASE {new_database_name}")
                    self.populate_database_combo_box()
                    self.database_combo_box.setCurrentText(new_database_name)  # Select the new database
                except mysql.connector.Error as err:
                    print(f"Error: {err}")
                finally:
                    # Close cursor and connection
                    cursor.close()
                    connection.close()

    def confirm_delete_database(self):
        selected_database = self.database_combo_box.currentText()
        if selected_database:
            # Ask for confirmation
            confirm = QMessageBox.question(self, "Confirm Deletion",
                                           f"Are you sure you want to delete the database '{selected_database}'?",
                                           QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                # Ask for password
                self.prompt_password_for_deletion(selected_database)

    def prompt_password_for_deletion(self, database_name):
        # Prompt for password
        password, ok = QInputDialog.getText(self, "Enter Password", "Enter your password:", QLineEdit.Password)
        if ok:
            # Connect to server and attempt deletion
            self.delete_database(database_name, password)

    def delete_database(self, database_name, password):
        # Establish connection with password
        connection = self.connect_to_server(password)

        if connection is not None:
            # Create cursor
            cursor = connection.cursor()

            try:
                # Execute DROP DATABASE query
                cursor.execute(f"DROP DATABASE {database_name}")
                self.populate_database_combo_box()
            except mysql.connector.Error as err:
                print(f"Error: {err}")
            finally:
                # Close cursor and connection
                cursor.close()
                connection.close()

    def connect_to_server(self, password):
        try:
            # Establish connection with password
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password=password
            )
            return connection
        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Error", f"Failed to connect to server: {err}")
            return None

    def confirm_delete_database(self):
        selected_database = self.database_combo_box.currentText()
        if selected_database:
            # Ask for confirmation
            confirm = QMessageBox.question(self, "Confirm Deletion",
                                           f"Are you sure you want to delete the database '{selected_database}'?",
                                           QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                # Ask for password
                self.prompt_password_for_deletion(selected_database)

    def prompt_password_for_deletion(self, database_name):
        # Prompt for password
        password, ok = QInputDialog.getText(self, "Enter Password", "Enter your password:", QLineEdit.Password)
        if ok:
            # Connect to server and attempt deletion
            self.delete_database(database_name, password)

    def delete_database(self, database_name, password):
        # Establish connection with password
        connection = self.checkpassword(password)

        if connection is not None:
            # Create cursor
            cursor = connection.cursor()

            try:
                # Execute DROP DATABASE query
                cursor.execute(f"DROP DATABASE {database_name}")
                self.populate_database_combo_box()
                QMessageBox.information(self, "Success", database_name + " has been deleted")
            except mysql.connector.Error as err:
                print(f"Error: {err}")
            finally:
                # Close cursor and connection
                cursor.close()
                connection.close()

    def checkpassword(self, password):
        try:
            # Establish connection with password
            connection = mysql.connector.connect(
                host=self.hostname_input.text(),
                user=self.username_input.text(),
                password=password
            )
            return connection
        except mysql.connector.Error as err:
            QMessageBox.information(self, "Fail", "Password is incorrect.")
            return None

    def rename_database(self):
        old_name = self.database_combo_box.currentText()
        if old_name:
            new_name, ok = QInputDialog.getText(self, "Rename Database", f"Enter new name for database '{old_name}':")
            if ok:
                # Establish connection
                connection = self.connect_to_server()

                if connection is not None:
                    # Create cursor
                    cursor = connection.cursor()

                    try:
                        cursor.execute(f"CREATE DATABASE {new_name}")

                        # Get list of tables from the old database
                        cursor.execute(f"USE {old_name}")
                        cursor.execute("SHOW TABLES")
                        tables = cursor.fetchall()

                        # Copy tables and data from old database to new database
                        for table in tables:
                            table_name = table[0]
                            cursor.execute(f"USE {old_name}")
                            cursor.execute(f"CREATE TABLE {new_name}.{table_name} LIKE {old_name}.{table_name}")
                            cursor.execute(f"INSERT INTO {new_name}.{table_name} SELECT * FROM {old_name}.{table_name}")

                        # Drop the old database
                        cursor.execute(f"DROP DATABASE {old_name}")

                        self.populate_database_combo_box()
                        self.database_combo_box.setCurrentText(new_name)  # Select the renamed database
                    except mysql.connector.Error as err:
                        print(f"Error: {err}")
                    finally:
                        # Close cursor and connection
                        cursor.close()
                        connection.close()

    def load_database(self):
        selected_database = self.database_combo_box.currentText()
        if selected_database and self.databasewindow is None:
            # Open a new window to load the database (placeholder)
            self.hide()
            info = [self.hostname_input.text(), self.username_input.text(), self.password_input.text(), selected_database]
            self.databasewindow = DatabaseWindow(info)
            self.databasewindow.show()

    def connect_to_server(self):
        try:
            # Establish connection
            connection = mysql.connector.connect(
                host=self.hostname_input.text() if self.hostname_input.text() else None,
                user=self.username_input.text() if self.username_input.text() else None,
                password=self.password_input.text() if self.password_input.text() else None
            )

            # Enable database controls
            self.set_database_controls_enabled(True)
            self.database_combo_box.setEnabled(True)
            return connection
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            self.hostname_input.setText("")
            self.username_input.setText("")
            self.password_input.setText("")
            self.database_combo_box.clear()
            self.set_database_controls_enabled(False)
            self.connection_status_label.setText("Disconnected")
            self.connection_status_label.setStyleSheet("color: red")
            QMessageBox.warning(self, "Error", f"Failed to connect: {err}")
            return None

    def set_database_controls_enabled(self, enabled):
        # Enable or disable database controls
        self.create_database_button.setEnabled(enabled)
        self.delete_database_button.setEnabled(enabled)
        self.rename_database_button.setEnabled(enabled)
        self.load_database_button.setEnabled(enabled)
        self.database_combo_box.setEnabled(enabled)


    def populate_database_combo_box(self):
        self.database_combo_box.clear()

        # Establish connection
        connection = self.connect_to_server()

        if connection is not None:
            # Create cursor
            cursor = connection.cursor()

            try:
                # Execute SHOW DATABASES query
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                for db in databases:
                    formatted = str(db).replace("('", "").replace("',)", "")
                    if formatted not in removed_dbs:
                        self.database_combo_box.addItem(db[0])
            except mysql.connector.Error as err:
                print(f"Error: {err}")
            finally:
                # Close cursor and connection
                cursor.close()
                connection.close()

    def connect_to_server_and_refresh(self):
        # Connect to the database and refresh controls
        if self.hostname_input.text():
            connection = self.connect_to_server()
            if connection:
                self.connection_status_label.setText("Connected")
                self.connection_status_label.setStyleSheet("color: green")
                self.populate_database_combo_box()
            else:
                self.connection_status_label.setStyleSheet("color: red")
                self.connection_status_label.setText("Disconnected")

        else:
            QMessageBox.warning(self, "Error", "Please enter the hostname.")
class DatabaseWindow(QMainWindow):
    def __init__(self, info):
        super().__init__()

        self.info = info
        self.setWindowTitle("Database: " + info[3])
        self.setMinimumSize(800, 600)
        self.query_history = []  # Initialize an empty list to store the query history


        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        grid_layout = QGridLayout()
        central_widget.setLayout(grid_layout)

        splitter = QSplitter(Qt.Vertical)  # Vertical splitter

        horizontal_splitter = QSplitter(Qt.Horizontal)  # Horizontal splitter

        self.hierarchy_widget = CustomListWidget()
        self.hierarchy_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Set size policy

        table_selection_item = QListWidgetItem("Table Selection Window")
        table_selection_item.setFlags(table_selection_item.flags() & ~Qt.ItemIsSelectable)
        font = QFont()
        font.setBold(True)
        table_selection_item.setFont(font)  # Set font to bold
        self.hierarchy_widget.addItem(table_selection_item)

        self.table_view = QTableView()

        self.info_label = QPushButton("Show Table Info")
        self.info_label.clicked.connect(self.show_table_info)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.toggle_console()  # Initialize console with prompt

        splitter.addWidget(horizontal_splitter)
        splitter.addWidget(self.console)
        splitter.addWidget(self.info_label)

        horizontal_splitter.addWidget(self.hierarchy_widget)
        horizontal_splitter.addWidget(self.table_view)

        self.table_tab_widget = QTabWidget()
        horizontal_splitter.addWidget(self.table_tab_widget)
        # Create a table view
        self.table_tab_widget.addTab(self.table_view, "Table View")
        self.table_tab_widget.setTabVisible(0, False)
        self.table_tab_widget.setTabsClosable(True)  # Enable close button for tabs

        grid_layout.addWidget(splitter, 0, 0, 2, 1)

        splitter.setSizes([200, 20, 10])
        vertical_splitter = splitter.widget(0)
        vertical_splitter.setSizes([100, 240])

        self.load_tables()
        self.create_menu()

        self.table_tab_widget.tabCloseRequested.connect(self.close_table_tab)
        self.hierarchy_widget.itemDoubleClicked.connect(self.open_table_tab)
        self.table_tab_widget.currentChanged.connect(self.update_hierarchy_selection)

        self.console.installEventFilter(self)

    def update_hierarchy_selection(self, index):
        if index != -1:  # Ensure valid index
            table_name = self.table_tab_widget.tabText(index)
            items = self.hierarchy_widget.findItems(table_name, Qt.MatchExactly)
            if items:
                self.hierarchy_widget.setCurrentItem(items[0])

    def toggle_hierarchy(self):
        self.hierarchy_widget.setVisible(not self.hierarchy_widget.isVisible())

    def toggle_console(self):
        self.console.setVisible(not self.console.isVisible())

        if self.console.isVisible():
            # Set console to read-write mode
            self.console.setReadOnly(False)

            # Clear console and add prompt
            self.console.clear()
            self.console.insertPlainText("MySQL > ")

            # Set cursor to end of prompt
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.console.setTextCursor(cursor)
        else:
            # Set console back to read-only mode
            self.console.setReadOnly(True)

    def eventFilter(self, obj, event):
        if obj == self.console and event.type() == QEvent.KeyPress:
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.End)

            if event.key() == Qt.Key_Return and event.modifiers() == Qt.NoModifier:
                self.execute_sql_command()
                return True  # Event handled

            elif event.key() == Qt.Key_Backspace and cursor.position() <= len("MySQL > "):
                return True  # Prevent deletion of MySQL prompt with Backspace key

            elif event.key() == Qt.Key_Delete and cursor.position() <= len("MySQL > "):
                return True  # Prevent deletion of MySQL prompt with Delete key

            elif event.key() == Qt.Key_Escape:
                self.console.setFocus()  # Set focus back to console on Escape key press

        return super().eventFilter(obj, event)

    def execute_sql_command(self):
        command = self.console.toPlainText().split(">")[-1].strip()  # Extract SQL command entered by the user
        if command:
            try:
                connection = mysql.connector.connect(
                    host=self.info[0],
                    user=self.info[1],
                    password=self.info[2],
                    database=self.info[3]
                )

                cursor = connection.cursor()
                cursor.execute(command)
                connection.commit()

                # Fetch and display results if any
                if cursor.description:
                    column_names = [column[0] for column in cursor.description]
                    rows = cursor.fetchall()
                    result_text = "\n".join(["\t".join(map(str, row)) for row in [column_names] + list(rows)])
                    self.console.append(result_text)
                else:
                    self.console.append("Query executed successfully.")

            except mysql.connector.Error as err:
                self.console.append(f"Error: {err}")

            # Add a new prompt for the next command
            self.console.append("MySQL > ")
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.console.setTextCursor(cursor)
            self.hierarchy_widget.clear()
            self.refresh()

    def refresh(self):
        self.hierarchy_widget.clear()

        table_selection_item = QListWidgetItem("Table Selection Window")
        table_selection_item.setFlags(table_selection_item.flags() & ~Qt.ItemIsSelectable)
        font = QFont()
        font.setBold(True)
        table_selection_item.setFont(font)  # Set font to bold
        self.hierarchy_widget.addItem(table_selection_item)

        self.load_tables()

        # Refresh the data in the current selected table
        current_tab_index = self.table_tab_widget.currentIndex()
        if current_tab_index != -1:
            current_tab_widget = self.table_tab_widget.widget(current_tab_index)
            if isinstance(current_tab_widget, TableWidget):
                current_tab_widget.load_table_data()

    def create_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&File')

        exit_action = QAction('&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(qApp.quit)
        file_menu.addAction(exit_action)

        open_database_action = QAction('Open Database', self)
        open_database_action.triggered.connect(self.open_database)
        file_menu.addAction(open_database_action)

        clear_console_action = QAction('Clear Console', self)
        clear_console_action.triggered.connect(self.clear_console)
        file_menu.addAction(clear_console_action)

        refresh_action = QAction('Refresh', self)
        refresh_action.triggered.connect(self.refresh)
        file_menu.addAction(refresh_action)

        view_menu = menu_bar.addMenu("View")

        toggle_hierarchy_action = QAction("Toggle Hierarchy", self)
        toggle_hierarchy_action.setCheckable(True)
        toggle_hierarchy_action.setChecked(True)  # Hierarchy enabled by default
        toggle_hierarchy_action.triggered.connect(self.toggle_hierarchy)
        view_menu.addAction(toggle_hierarchy_action)

        toggle_console_action = QAction("Toggle Console", self)
        toggle_console_action.setCheckable(True)
        toggle_console_action.setChecked(True)  # Console enabled by default
        toggle_console_action.triggered.connect(self.toggle_console)
        view_menu.addAction(toggle_console_action)

        create_menu = menu_bar.addMenu('&Tables')

        create_table_action = QAction('Create Table', self)
        create_table_action.triggered.connect(self.create_table)
        create_menu.addAction(create_table_action)

        alter_table_action = QAction('Alter Table', self)
        alter_table_action.triggered.connect(self.alter_table)
        create_menu.addAction(alter_table_action)

        delete_table_action = QAction('Delete Table', self)
        delete_table_action.triggered.connect(self.delete_table)
        create_menu.addAction(delete_table_action)

        data_menu = menu_bar.addMenu('&Data')

        delete_row_action = QAction('Delete Row', self)
        delete_row_action.triggered.connect(self.delete_row)
        data_menu.addAction(delete_row_action)

        modify_row_action = QAction('Modify Row', self)
        modify_row_action.triggered.connect(self.modify_row)
        data_menu.addAction(modify_row_action)

        insert_row_action = QAction('Insert Row', self)
        insert_row_action.triggered.connect(self.insert_data)
        data_menu.addAction(insert_row_action)

        query_menu = menu_bar.addMenu('&Queries')

        query_action = QAction('Execute Query', self)
        query_action.triggered.connect(self.execute_query)
        query_menu.addAction(query_action)

        query_history_action = QAction('Query History', self)
        query_history_action.triggered.connect(self.show_query_history)
        query_menu.addAction(query_history_action)

        clear_history_action = QAction('Clear Query History', self)
        clear_history_action.triggered.connect(self.clear_query_history)
        query_menu.addAction(clear_history_action)

        upload_menu = menu_bar.addMenu('&Upload')

        upload_table_action = QAction('Upload Table', self)
        upload_table_action.triggered.connect(self.upload_table)
        upload_menu.addAction(upload_table_action)

    def open_database(self):
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        QCoreApplication.sendEvent(self, event)


    def execute_query_command(self, query):

        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )

            cursor = connection.cursor()
            cursor.execute(query)
            self.query_history.append(query.strip())

            # Fetch all results before executing another query
            rows = cursor.fetchall()
            description = cursor.description

            connection.commit()
            cursor.close()

            # Fetch query results and display them in a new window
            self.display_query_results(rows, description)

            # Refresh the data after a successful query execution
            self.refresh()

        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Error", f"Failed to execute query: {err}")
    def execute_query(self):
        query, ok = QInputDialog.getText(self, "Execute Query", "Enter your SQL query:")
        if ok and query.strip():
            try:
                connection = mysql.connector.connect(
                    host=self.info[0],
                    user=self.info[1],
                    password=self.info[2],
                    database=self.info[3]
                )

                cursor = connection.cursor()
                cursor.execute(query)
                self.query_history.append(query)

                # Fetch all results before executing another query
                rows = cursor.fetchall()
                description = cursor.description

                connection.commit()
                cursor.close()

                # Fetch query results and display them in a new window
                self.display_query_results(rows, description)

                # Refresh the data after a successful query execution
                self.refresh()

            except mysql.connector.Error as err:
                QMessageBox.warning(self, "Error", f"Failed to execute query: {err}")

    def display_query_results(self, rows, description):
        query_window = QueryWindow(self)
        headers = [column[0] for column in description]
        query_window.set_data(rows, headers)
        query_window.exec_()
    def clear_console(self):
        self.console.clear()

    def clear_query_history(self):
        self.query_history.clear()  # Clear the query history list

    def show_query_history(self):
        dialog = QueryHistoryDialog(self)
        dialog.load_query_history(self.query_history)  # Pass the query history list to the dialog
        dialog.exec_()

    def load_tables(self):
        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )

            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            for table in tables:
                table_name = table[0]
                self.hierarchy_widget.addItem(table_name)

        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Error", f"Failed to load tables: {err}")

    def insert_data(self):
        current_tab_index = self.table_tab_widget.currentIndex()
        if current_tab_index != -1:
            current_tab_widget = self.table_tab_widget.currentWidget()
            if isinstance(current_tab_widget, TableWidget):
                # Fetch column names and data types
                column_info = current_tab_widget.get_column_names_and_types()

                # Open the InsertDataDialog with column information
                dialog = InsertDataDialog(current_tab_widget.tablename, self.info, column_info)
                if dialog.exec_():
                    data = dialog.get_data()
                    # Prepare column names and values for the INSERT statement
                    columns = ', '.join(data.keys())
                    values = ', '.join(f"'{value}'" if value is not None else "NULL" for value in data.values())

                    # Check for primary keys and foreign keys
                    primary_keys = current_tab_widget.get_primary_keys()
                    foreign_keys = current_tab_widget.get_foreign_keys()

                    # If a primary key is auto-incremented, do not include it in the insert statement
                    for key in primary_keys:
                        if key["auto_increment"]:
                            columns = columns.replace(key["column_name"], "")
                            values = values.replace("NULL", "")

                    # Construct the INSERT statement
                    insert_query = f"INSERT INTO {current_tab_widget.tablename} ({columns}) VALUES ({values})"

                    try:
                        # Execute the INSERT statement
                        connection = mysql.connector.connect(
                            host=self.info[0],
                            user=self.info[1],
                            password=self.info[2],
                            database=self.info[3]
                        )
                        cursor = connection.cursor()
                        cursor.execute(insert_query)
                        connection.commit()
                        connection.close()
                        QMessageBox.information(self, "Success", "Data inserted successfully.")
                        self.refresh()
                    except mysql.connector.Error as err:
                        QMessageBox.warning(self, "Error", f"Failed to insert data: {err}")
            else:
                QMessageBox.warning(self, "Error", "Please select a table tab.")
        else:
            QMessageBox.warning(self, "Error", "Please select a table tab.")

    def delete_row(self):
        current_tab_index = self.table_tab_widget.currentIndex()
        if current_tab_index != -1:
            current_tab_widget = self.table_tab_widget.currentWidget()
            if isinstance(current_tab_widget, TableWidget):
                dialog = DeleteRowDialog(current_tab_widget.tablename, self.info, self)
                dialog.exec_()
                self.refresh()
                QMessageBox.information(self, "Title", "DELETE successful", QMessageBox.Ok)


            else:
                QMessageBox.warning(self, "Error", "Please select a table tab.")
        else:
            QMessageBox.warning(self, "Error", "Please select a table tab.")

    def modify_row(self):
        current_tab_index = self.table_tab_widget.currentIndex()
        if current_tab_index != -1:
            current_tab_widget = self.table_tab_widget.currentWidget()
            if isinstance(current_tab_widget, TableWidget):
                dialog = ModifyRowDialog(current_tab_widget.tablename, self.info, self)
                dialog.exec_()
                self.refresh()

            else:
                QMessageBox.warning(self, "Error", "Please select a table tab.")
        else:
            QMessageBox.warning(self, "Error", "Please select a table tab.")
    def close_table_tab(self, index):
        self.table_tab_widget.removeTab(index)

    def open_table_tab(self, item):
        table_name = item.text()
        for index in range(self.table_tab_widget.count()):
            if self.table_tab_widget.tabText(index) == table_name:
                # If the tab already exists, set the current widget to the existing one
                self.table_tab_widget.setCurrentIndex(index)
                self.refresh()
                return  # Exit the method once the tab is set

        # If the tab doesn't exist, create a new one and set it as the current widget
        table_widget = TableWidget(table_name, self.info)
        self.table_tab_widget.addTab(table_widget, table_name)
        self.table_tab_widget.setCurrentWidget(table_widget)

    def create_table(self):
        create_table_window = CreateTableWindow(self)
        if create_table_window.exec_() == QDialog.Accepted:
            table_name, columns = create_table_window.get_table_data()
            if table_name and columns:
                self.create_table_in_database(table_name, columns)
                self.refresh()

    def create_table_in_database(self, table_name, columns):
        try:
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )
            cursor = connection.cursor()
            column_definitions = []
            for column in columns:
                key_type, data_type, column_name, not_null = column
                column_definition = f"{column_name} {data_type}"
                if key_type:
                    column_definition += f" {key_type}"
                if not_null:
                    column_definition += " NOT NULL"
                column_definitions.append(column_definition)
            query = f"CREATE TABLE {table_name} ({', '.join(column_definitions)})"
            cursor.execute(query)
            connection.commit()
            QMessageBox.information(self, "Success", "Table created successfully.")
            connection.close()
        except mysql.connector.Error as err:
            QMessageBox.warning(self, "Error", f"Failed to create table: {err}")

    def alter_table(self):
        current_item = self.hierarchy_widget.currentItem()
        if current_item:
            table_name = current_item.text()
            alter_table_window = AlterTableWindow(table_name, self.info, self)
            if alter_table_window.exec_() == QDialog.Accepted:
                # Perform any necessary actions after alteration
                self.refresh()
        else:
            QMessageBox.warning(self, "Error", "Please select a table to alter.")
    def delete_table(self):
        current_item = self.hierarchy_widget.currentItem()
        if current_item:
            table_name = current_item.text()
            confirm = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete the table '{table_name}'?", QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                try:
                    connection = mysql.connector.connect(
                        host=self.info[0],
                        user=self.info[1],
                        password=self.info[2],
                        database=self.info[3]
                    )

                    cursor = connection.cursor()
                    cursor.execute(f"DROP TABLE {table_name}")
                    connection.commit()
                    self.refresh()
                    QMessageBox.information(self, "Success", "Table deleted successfully.")

                except mysql.connector.Error as err:
                    QMessageBox.warning(self, "Error", f"Failed to delete table: {err}")
        else:
            QMessageBox.warning(self, "Error", "Please select a table to delete.")

    def upload_table(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if file_path:
            try:
                # Read data from file
                if file_path.endswith('.csv'):
                    data = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    data = pd.read_excel(file_path)
                else:
                    QMessageBox.warning(self, "Error", "Unsupported file format")
                    return

                # Process and upload data to the database
                self.upload_data_to_database(data)
                self.refresh()

                QMessageBox.information(self, "Success", "Table uploaded successfully")

            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to upload table: {str(e)}")

    def upload_data_to_database(self, data):
        try:
            # Establish connection to the database
            connection = mysql.connector.connect(
                host=self.info[0],
                user=self.info[1],
                password=self.info[2],
                database=self.info[3]
            )

            # Create a cursor object
            cursor = connection.cursor()

            # UPLOAD FUNCTION ISNT IMPLEMENTED YET, BUT WHEN IT IS IT WILL GO HERE

            connection.commit()

            # Close the cursor and connection
            cursor.close()
            connection.close()

        except mysql.connector.Error as e:
            raise e

    def show_table_info(self):
        current_item = self.hierarchy_widget.currentItem()
        if current_item is not None:
            try:
                connection = mysql.connector.connect(
                    host=self.info[0],
                    user=self.info[1],
                    password=self.info[2],
                    database=self.info[3]
                )
                tablename = current_item.text()
                cursor = connection.cursor()
                cursor.execute(f"SHOW CREATE TABLE {current_item.text()}")
                result = cursor.fetchone()
                create_table_statement = result[1]

                connection.close()

                # Display the table information in a new window
                table_info_window = TableInfoWindow(current_item.text(), create_table_statement)
                table_info_window.exec_()

            except mysql.connector.Error as e:
                print(f"Error showing table info: {e}")
        else:
            QMessageBox.warning(self, "Error", "Please select a table to show its info.")
class EventFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            if window.isVisible() == False:
                window.show()
                window.populate_database_combo_box()
                window.databasewindow = None
                return True
            return False
        return False

# Dialogs
class QueryHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Query History")
        self.layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.layout.addWidget(self.list_widget)

        self.list_widget.itemDoubleClicked.connect(self.run_selected_query)

    def load_query_history(self, query_history):
        self.list_widget.clear()  # Clear the list widget
        self.list_widget.addItems(query_history)  # Add items from query_history to the list widget

    def run_selected_query(self, item):
        # Retrieve and execute the selected query
        query = item.text()
        self.parent().execute_query_command(query)  # Execute the selected query
class CreateTableWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Table")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setMinimumSize(500, 300)

        self.table_name_input = QLineEdit()
        self.layout.addWidget(QLabel("Table Name:"))
        self.layout.addWidget(self.table_name_input)

        self.layout.addWidget(QLabel("Columns"))

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area_content = QWidget()
        self.scroll_area_layout = QVBoxLayout(self.scroll_area_content)

        self.rows = []
        self.add_row()

        self.scroll_area_layout.addStretch()  # Add stretch to push add row button to the bottom
        self.layout.addWidget(self.scroll_area)

        self.add_row_button = QPushButton("+ Add Row")
        self.add_row_button.clicked.connect(self.add_row)
        self.layout.addWidget(self.add_row_button)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept_wrapper)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.scroll_area.setWidget(self.scroll_area_content)

    def add_row(self):
        row_layout = QHBoxLayout()
        key_type_combo = QComboBox()
        key_type_combo.addItems(["", "Primary Key", "Foreign Key"])
        data_type_combo = QComboBox()
        data_type_combo.addItems(["INT", "BIGINT", "SMALLINT", "TINYINT", "FLOAT", "DOUBLE",
                                  "DECIMAL", "NUMERIC", "DATE", "TIME", "DATETIME", "TIMESTAMP",
                                  "YEAR", "CHAR", "VARCHAR(255)", "TEXT", "LONGTEXT", "BLOB",
                                  "MEDIUMBLOB", "LONGBLOB"])

        column_name_input = QLineEdit()
        not_null_checkbox = QCheckBox("Not Null")

        delete_row_button = QPushButton("Delete Row")
        delete_row_button.clicked.connect(lambda _, layout=row_layout: self.delete_row(layout))

        row_layout.addWidget(key_type_combo)
        row_layout.addWidget(data_type_combo)
        row_layout.addWidget(column_name_input)
        row_layout.addWidget(not_null_checkbox)
        row_layout.addWidget(delete_row_button)

        self.scroll_area_layout.insertLayout(len(self.rows), row_layout)
        self.rows.append((key_type_combo, data_type_combo, column_name_input, not_null_checkbox, delete_row_button))

    def delete_row(self, row_layout):
        for widget in row_layout:
            widget.deleteLater()
        self.rows = [row for row in self.rows if row[0] != row_layout.itemAt(0).widget()]

    def get_table_data(self):
        table_name = self.table_name_input.text().strip()
        columns = []
        for row in self.rows:
            key_type = row[0].currentText().strip()
            data_type = row[1].currentText().strip()
            column_name = row[2].text().strip()
            not_null = row[3].isChecked()
            columns.append((key_type, data_type, column_name, not_null))
        return table_name, columns

    def accept_wrapper(self):
        table_name = self.table_name_input.text().strip().replace(" ", "")  # Remove spaces from the table name
        if not table_name:
            QMessageBox.warning(self, "Warning", "Table name cannot be empty.")
        else:
            all_column_names = [row[2].text().strip() for row in self.rows]
            if not all(all_column_names):
                QMessageBox.warning(self, "Warning", "All column names must be filled.")
            elif not self.rows:
                QMessageBox.warning(self, "Warning", "You must add at least one column before creating the table.")
            else:
                self.table_name_input.setText(table_name)  # Update the table name input with the modified name
                self.accept()


class AlterTableWindow(QDialog):
    def __init__(self, table_name, Info, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Alter Table {table_name}")
        layout = QVBoxLayout()

        self.table_name = table_name
        self.Info = Info

        self.column_name_edit = QLineEdit()
        self.column_name_edit.setPlaceholderText("Enter column name")

        self.column_type_combobox = QComboBox()
        self.column_type_combobox.addItems(["INT", "VARCHAR(255)", "TEXT", "DATE"])

        # Checkboxes for additional column properties
        self.primary_key_checkbox = QCheckBox("Primary Key")
        self.auto_increment_checkbox = QCheckBox("Auto Increment")
        self.not_null_checkbox = QCheckBox("Not Null")
        self.foreign_key_checkbox = QCheckBox("Foreign Key")

        self.add_column_button = QPushButton("Add Column")
        self.add_column_button.clicked.connect(self.add_column)

        self.clear_add_button = QPushButton("Clear")
        self.clear_add_button.clicked.connect(self.clear_add_form)

        self.drop_column_edit = QLineEdit()
        self.drop_column_edit.setPlaceholderText("Enter column to drop")

        self.drop_column_button = QPushButton("Drop Column")
        self.drop_column_button.clicked.connect(self.drop_column)

        self.clear_drop_button = QPushButton("Clear")
        self.clear_drop_button.clicked.connect(self.clear_drop_form)

        self.alter_table_button = QPushButton("Alter Table")
        self.alter_table_button.clicked.connect(self.alter_table)

        tab_widget = QTabWidget()

        # Tab for adding columns
        add_column_tab = QWidget()
        add_column_layout = QVBoxLayout()
        self.add_column_label = QLabel()
        add_column_layout.addWidget(self.add_column_label)
        add_column_layout.addWidget(QLabel("Column Name:"))
        add_column_layout.addWidget(self.column_name_edit)
        add_column_layout.addWidget(QLabel("Column Type:"))
        add_column_layout.addWidget(self.column_type_combobox)
        add_column_layout.addWidget(self.primary_key_checkbox)
        add_column_layout.addWidget(self.auto_increment_checkbox)
        add_column_layout.addWidget(self.not_null_checkbox)
        add_column_layout.addWidget(self.foreign_key_checkbox)
        add_column_layout.addWidget(self.add_column_button)
        add_column_layout.addWidget(self.clear_add_button)
        add_column_tab.setLayout(add_column_layout)

        # Tab for dropping columns
        drop_column_tab = QWidget()
        drop_column_layout = QVBoxLayout()
        self.drop_column_label = QLabel()
        drop_column_layout.addWidget(self.drop_column_label)
        drop_column_layout.addWidget(self.drop_column_edit)
        drop_column_layout.addWidget(self.drop_column_button)
        drop_column_layout.addWidget(self.clear_drop_button)
        drop_column_tab.setLayout(drop_column_layout)

        tab_widget.addTab(add_column_tab, "Add Column")
        tab_widget.addTab(drop_column_tab, "Drop Column")

        layout.addWidget(tab_widget)
        layout.addWidget(self.alter_table_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

        self.columns_to_add = []
        self.columns_to_drop = []

    def get_table_data(self):
        return self.columns_to_add, self.columns_to_drop

    def add_column(self):
        column_name = self.column_name_edit.text()
        column_type = self.column_type_combobox.currentText()
        is_primary_key = self.primary_key_checkbox.isChecked()
        is_auto_increment = self.auto_increment_checkbox.isChecked()
        is_not_null = self.not_null_checkbox.isChecked()
        is_foreign_key = self.foreign_key_checkbox.isChecked()

        if column_name and column_type:
            self.columns_to_add.append(
                (column_name, column_type, is_primary_key, is_auto_increment, is_not_null, is_foreign_key))
            self.column_name_edit.clear()
            self.update_add_column_label()

    def drop_column(self):
        column_name = self.drop_column_edit.text()
        if column_name:
            self.columns_to_drop.append(column_name)
            self.drop_column_edit.clear()
            self.update_drop_column_label()

    def alter_table(self):
        if self.columns_to_drop or self.columns_to_add:
            try:
                connection = mysql.connector.connect(
                    host=self.Info[0],
                    user=self.Info[1],
                    password=self.Info[2],
                    database=self.Info[3]
                )
                cursor = connection.cursor()

                # Add columns
                for column_data in self.columns_to_add:
                    column_name, column_type, is_primary_key, is_auto_increment, is_not_null, is_foreign_key = column_data
                    alter_query = f"ALTER TABLE {self.table_name} ADD COLUMN {column_name} {column_type}"
                    if is_primary_key:
                        alter_query += " PRIMARY KEY"
                    if is_auto_increment:
                        alter_query += " AUTO_INCREMENT"
                    if is_not_null:
                        alter_query += " NOT NULL"
                    if is_foreign_key:
                        alter_query += " FOREIGN KEY (ref_column) REFERENCES ref_table(ref_column)"
                    cursor.execute(alter_query)

                # Drop columns
                for column_name in self.columns_to_drop:
                    drop_query = f"ALTER TABLE {self.table_name} DROP COLUMN {column_name}"
                    cursor.execute(drop_query)

                connection.commit()
                connection.close()
                self.accept()
            except mysql.connector.Error as e:
                QMessageBox.warning(self, "Error", f"Failed to alter table: {e}")
        else:
            QMessageBox.warning(self, "Error", "Cannot alter table: No changes specified.")

    def clear_add_form(self):
        self.columns_to_add = []
        self.update_add_column_label()

    def clear_drop_form(self):
        self.columns_to_drop = []
        self.update_drop_column_label()

    def update_add_column_label(self):
        if self.columns_to_add:
            column_details = ""
            for column_data in self.columns_to_add:
                column_name, column_type, is_primary_key, is_auto_increment, is_not_null, is_foreign_key = column_data
                details = f"{column_name} {column_type}"
                if is_primary_key:
                    details += " PRIMARY KEY"
                if is_auto_increment:
                    details += " AUTO_INCREMENT"
                if is_not_null:
                    details += " NOT NULL"
                if is_foreign_key:
                    details += " FOREIGN KEY (ref_column) REFERENCES ref_table(ref_column)"
                column_details += details + "\n"
            self.add_column_label.setText(f"ADD columns:\n{column_details.strip()}")
            self.add_column_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Set alignment
            self.add_column_label.setWordWrap(True)  # Enable word wrapping
        else:
            self.add_column_label.clear()

    def update_drop_column_label(self):
        if self.columns_to_drop:
            column_names = "\n".join(self.columns_to_drop)  # Use '\n' to create new lines
            self.drop_column_label.setText(f"DROP columns:\n{column_names}")
            self.drop_column_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Set alignment
            self.drop_column_label.setWordWrap(True)  # Enable word wrapping
        else:
            self.drop_column_label.clear()
class DeleteRowDialog(QDialog):
    def __init__(self, table_name, info, parent=None):
        super().__init__(parent)
        self.table_name = table_name
        self.info = info
        self.setWindowTitle("Delete Row")
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.create_widgets()

    def create_widgets(self):
        self.layout.addWidget(QLabel(f"Delete row from table '{self.table_name}'"))
        self.layout.addWidget(QLabel("Enter condition for deletion (e.g., id=1):"))
        self.condition_line_edit = QLineEdit()
        self.layout.addWidget(self.condition_line_edit)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_row)
        self.layout.addWidget(delete_button)

    def delete_row(self):
        condition = self.condition_line_edit.text()
        if condition:
            try:
                connection = mysql.connector.connect(
                    host=self.info[0],
                    user=self.info[1],
                    password=self.info[2],
                    database=self.info[3]
                )
                cursor = connection.cursor()
                query = f"DELETE FROM {self.table_name} WHERE {condition}"
                cursor.execute(query)
                connection.commit()
                QMessageBox.information(self, "Success", "Row deleted successfully.")
                self.close()
            except mysql.connector.Error as err:
                QMessageBox.warning(self, "Error", f"Failed to delete row: {err}")
        else:
            QMessageBox.warning(self, "Error", "Please enter a condition for deletion.")
class ModifyRowDialog(QDialog):
    def __init__(self, table_name, info, parent=None):
        super().__init__(parent)
        self.table_name = table_name
        self.info = info
        self.setWindowTitle("Modify Row")
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.create_widgets()

    def create_widgets(self):
        self.layout.addWidget(QLabel(f"Modify row in table '{self.table_name}'"))
        self.layout.addWidget(QLabel("Enter condition for modification (e.g., id=1):"))
        self.condition_line_edit = QLineEdit()
        self.layout.addWidget(self.condition_line_edit)
        self.layout.addWidget(QLabel("Enter new values for the row:"))
        self.new_values_text_edit = QTextEdit()
        self.layout.addWidget(self.new_values_text_edit)
        modify_button = QPushButton("Modify")
        modify_button.clicked.connect(self.modify_row)
        self.layout.addWidget(modify_button)

    def modify_row(self):
        condition = self.condition_line_edit.text()
        new_values = self.new_values_text_edit.toPlainText().strip()
        if condition and new_values:
            try:
                connection = mysql.connector.connect(
                    host=self.info[0],
                    user=self.info[1],
                    password=self.info[2],
                    database=self.info[3]
                )
                cursor = connection.cursor()
                query = f"UPDATE {self.table_name} SET {new_values} WHERE {condition}"
                cursor.execute(query)
                connection.commit()
                QMessageBox.information(self, "Success", "Row modified successfully.")
                self.close()
            except mysql.connector.Error as err:
                QMessageBox.warning(self, "Error", f"Failed to modify row: {err}")
        else:
            QMessageBox.warning(self, "Error", "Please enter both condition and new values for modification.")
class InsertDataDialog(QDialog):
    def __init__(self, tablename, info, column_info):
        super().__init__()
        self.tablename = tablename
        self.info = info
        self.setWindowTitle("Insert into " + tablename)
        self.column_info = column_info
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.inputs = {}
        for column, data_type in column_info:
            label = QLabel(f"{column} ({data_type}):")
            input_field = QLineEdit()
            self.layout.addWidget(label)
            self.layout.addWidget(input_field)
            self.inputs[column] = input_field
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

    def get_data(self):
        data = {}
        for column, input_field in self.inputs.items():
            data[column] = input_field.text()
        return data
class TableInfoWindow(QDialog):
    def __init__(self, tablename, table_info):
        super().__init__()
        self.resize(400, 300)

        layout = QVBoxLayout()

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(table_info)
        self.setWindowTitle(tablename + " Table Information")

        self.text_edit.setReadOnly(True)

        layout.addWidget(self.text_edit)
        self.setLayout(layout)
class QueryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Query Results")
        self.setModal(True)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.table_widget = QTableWidget()
        self.layout.addWidget(self.table_widget)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        self.layout.addWidget(self.close_button)

    def set_data(self, data, headers):
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setRowCount(len(data))
        self.table_widget.setHorizontalHeaderLabels(headers)

        for row_idx, row_data in enumerate(data):
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                self.table_widget.setItem(row_idx, col_idx, item)
class CreateTableDialog(QDialog):
    def __init__(self, parent=None):
        super(CreateTableDialog, self).__init__(parent)
        self.setWindowTitle("Create Table")
        layout = QVBoxLayout()

        self.table_name_line_edit = QLineEdit()
        layout.addWidget(QLabel("Table Name:"))
        layout.addWidget(self.table_name_line_edit)

        self.fields_text_edit = QTextEdit()
        layout.addWidget(QLabel("Fields (comma separated):"))
        layout.addWidget(self.fields_text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DatabaseManager()
    window.show()
    event_filter = EventFilter()
    app.installEventFilter(event_filter)
    sys.exit(app.exec_())

# Made by Nathaniel Bates 10/3/2024, Version 1.0.0
