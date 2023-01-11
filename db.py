import os

import pyodbc


class DBClient:
    def __init__(self, db_name: str):
        self._db_name = db_name
        self.conn = None

    def create_conn(self):
        match self._db_name:
            case 'gis':
                _driver = "MySQL ODBC 8.0 ANSI Driver"
                _server = "localhost"
                _uid = os.getenv("gis_uid")
                _password = os.getenv("gis_pwd")
            case 'Regoper':
                _driver = "SQL Server"
                _server = "srv-sql"
                _uid = os.getenv("ro_uid")
                _password = os.getenv("ro_pwd")
        self.conn = pyodbc.connect(f'Driver={_driver};Server={_server};Database={self._db_name};UID={_uid};PWD={_password};')

    def close_conn(self):
        self.conn.close()

    def execute_command_params(self, command: str, params: tuple):
        if self.conn is not None:
            self.conn.execute(command, params)
            self.conn.commit()
        else:
            raise ConnectionError('you need create connection to database!')

    def execute_select_command(self, command: str):
        if self.conn is not None:
            with self.conn.cursor() as cursor:
                cursor.execute(command)
            return cursor.fetchall()
        else:
            raise ConnectionError('you need create connection to database!')

    def execute_command(self, command: str):
        if self.conn is not None:
            cursor = self.conn.cursor()
            cursor.execute(command)
            self.conn.commit()
        else:
            raise ConnectionError('you need create connection to database!')
