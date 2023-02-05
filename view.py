from datetime import datetime
import time
import sys

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QIcon

from bots import GetRequestsBot, SendResponseBot
from esia import AuthGIS
import utils
import conf
import db


db_client = db.DBClient('gis')
db_client.create_conn()


def write_response_to_db(deb_id, answer):
    sql = f"""
        INSERT IGNORE INTO stat (debt_id, answer, answer_time)
        VALUES (?, ?, ?)
    """
    record = (
                deb_id,
                answer,
                str(datetime.now().strftime('%d-%m-%Y %H:%M:%S'))
                )
    db_client.execute_command_params(sql, record)


class OutputLogger(QObject):
    log_signal = pyqtSignal(str)

    def __init__(self, io_stream):
        super().__init__()
        self.io_stream = io_stream

    def write(self, text):
        # self.io_stream.write(text)
        d = datetime.now().strftime('%d.%m.%Y %H:%M:%S ')
        if text != '\n':
            text = d + text    
        self.log_signal.emit(text)

    def flush(self):
        self.io_stream.flush()


OUTPUT_LOGGER_STDOUT = OutputLogger(sys.stdout)
sys.stdout = OUTPUT_LOGGER_STDOUT


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi()
        self.show()

        OUTPUT_LOGGER_STDOUT.log_signal.connect(self.browser.append)

    def setupUi(self):
        self.setWindowTitle("Графический интерфейс")
        self.setWindowIcon(QIcon("logo.png"))
        self.resize(330, 400)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.setStyleSheet("QLabel, QPushButton, QDateEdit {font-size: 9pt;}")

        grid = QGridLayout(self.centralWidget)

        # Панель меню 
        self._create_menubar()
        # Статус-панель
        self._create_statusbar()

        status_label = QLabel("Статус:")
        status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_work = QLabel("Требуется авторизация")
        self.status_work.setStyleSheet("color: red; font-weight: bold")

        self.start_date = QDateEdit(self)
        sdate = QDate(*utils.get_start_date())
        self.start_date.setDate(sdate)

        start_date_label = QLabel("Дата направления запроса:")
        start_date_label.setAlignment(Qt.AlignRight)

        req_label = QLabel("Количество запросов:")
        req_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count_req_label = QLabel("0")
        
        resp_label = QLabel("Отвечено на:")
        resp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count_resp_label = QLabel("0")
        
        self.do_button = QPushButton("В работу...")
        self.do_button.setEnabled(False)
        self.do_button.clicked.connect(self.start_func)

        self.browser = QTextBrowser()
        
        grid.addWidget(status_label, 0, 0)
        grid.addWidget(self.status_work, 0, 1)
        grid.addWidget(start_date_label, 1, 0)
        grid.addWidget(self.start_date, 1, 1)
        grid.addWidget(req_label, 2, 0)
        grid.addWidget(self.count_req_label, 2, 1)
        grid.addWidget(resp_label, 3, 0)
        grid.addWidget(self.count_resp_label, 3, 1)
        grid.addWidget(self.do_button, 4, 0, 1, 2)
        grid.addWidget(self.browser, 5, 0, 4, 2)
        
    def _create_menubar(self):
        menubar = self.menuBar()

        primary_menu = QMenu("Меню", self)
        primary_menu.addAction("Авторизоваться")
        primary_menu.addSeparator()
        primary_menu.addAction("Выход")
        primary_menu.triggered[QAction].connect(self.menu_trigger)

        about_menu = QMenu("Справка", self)
        about_menu.addAction("О программе")
        about_menu.triggered[QAction].connect(self.help_trigger)

        menubar.addMenu(primary_menu)
        menubar.addMenu(about_menu)

    def _create_statusbar(self):
        self.statusbar = self.statusBar()
        self.statusbar.showMessage("Готов")

    def menu_trigger(self, q):
        match q.text():
            case "Авторизоваться":
                self.auth = AuthWindow()
                self.auth.account[str, str].connect(self.auth_input)
                self.auth.exec()
            case "Выход":
                self.close()

    def help_trigger(self, q):
        match q.text():
            case "О программе":
                about = QMessageBox()
                about.setWindowTitle("О программе")
                about.setText("Версия программы 1.1.0")
                about.setIcon(QMessageBox.Information)
                about.setStandardButtons(QMessageBox.Ok)
                about.exec_()       

    def auth_input(self, login, password):
        label = QLabel()
        label.setText(f"Логин пользователя {login}")
        self.statusbar.addWidget(label)

        self.status_work.setText("Готова к запуску")
        self.status_work.setStyleSheet("color: orange; font-weight: bold")
        
        pyqt_date = self.start_date.date()
        b_date = pyqt_date.toString('dd.MM.yyyy')

        self.worker_thread = WorkerThread(b_date, login, password)
        self.worker_thread.resp_count_signal.connect(self.status_func)
        self.worker_thread.req_count_signal.connect(self.status_func)
        self.worker_thread.status_signal.connect(self.status_func)

        self.do_button.setEnabled(True)

    def start_func(self):
        self.status_work.setText("Процесс запущен...")
        self.status_work.setStyleSheet("color: blue; font-weight: bold")

        self.worker_thread.start()
        self.do_button.setEnabled(False)

    def status_func(self, type_signal, count=None):
        match type_signal:
            case 'resp':
                self.count_resp_label.setText(str(count))
            case 'req':
                self.count_req_label.setText(str(count))
            case 'complete':
                self.do_button.setEnabled(True)
                self.status_work.setText("Завершено")
                self.status_work.setStyleSheet("color: green; font-weight: bold")

    def __del__(self) -> None:
        db_client.close_conn()


class WorkerThread(QThread):
    resp_count_signal = pyqtSignal(str, int)
    req_count_signal = pyqtSignal(str, int)
    status_signal = pyqtSignal(str)

    def __init__(self, b_date, login, password):
        super(WorkerThread, self).__init__()
        self.b_date = b_date
        self.login = login
        self.password = password

    def run(self):
        # 
        auth = AuthGIS(self.login, self.password)
        session = auth.get_session()
    #   глобальный маркер
        marker = False
        bots_state = False
        total_requests = 0
        total_answer = 0
        stime = datetime.now()
        delta = datetime.now() - stime
        #
        while True:
            if not bots_state:
                request_bot = GetRequestsBot(self.b_date, session)
                response_bot = SendResponseBot(session)
                bots_state = True

            if delta.seconds < 800:
                delta = datetime.now() - stime
                requests_data = request_bot.manage()
                if requests_data not in ("Error", "JSONDecodeError"):
                    if requests_data:
                        count = len(requests_data)
                        if count != 100:
                            marker = True
                        total_requests += count
                        self.resp_count_signal.emit('req', total_requests)
                        #   блок кода - ответы на запросы
                        for request in requests_data:
                            rec = (
                                request['id'],
                                request['debtReq']['houseId'],
                                # request['debtReq']['formattedAddress'],
                                utils.num_apartment(request['debtReq']['apartmentNumber']),
                                utils.modify_date(request['debtReq']['debtPeriod']['beginDate']),
                                utils.modify_date(request['debtReq']['debtPeriod']['endDate']),
                                )
                            result = response_bot.manage(*rec)
                            if result != "Forbidden":
                                # id запроса (debt_id) = rec[0]
                                write_response_to_db(rec[0], result)
                                total_answer += 1
                                self.resp_count_signal.emit('resp', total_answer)
                            else:
                                continue

                    else:
                        del request_bot
                        del response_bot
                        bots_state = False
                        marker = True
                else:
                    print("Некорректный ответ от сервера ГИС ЖКХ")
                    del auth
                    del request_bot
                    del response_bot
                    bots_state = False
                    time.sleep(5)
                    auth = AuthGIS(self.login, self.password)
                    session = auth.get_session()
                    stime = datetime.now()
                    delta = datetime.now() - stime
            else:
                print("Обновление куки")
                del auth
                del request_bot
                del response_bot
                bots_state = False
                time.sleep(5)
                auth = AuthGIS(self.login, self.password)
                session = auth.get_session()
                stime = datetime.now()
                delta = datetime.now() - stime
            if marker:
                print("Робот завершил работу")
                del auth
                self.status_signal.emit('complete')
                break


class AuthWindow(QDialog):
    account = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.setupUi()
        self.setWindowIcon(QIcon("logo.png"))
        self.read_config()

    def setupUi(self):
        self.setWindowTitle("Авторизация")
        self.resize(200, 200)
        self.setStyleSheet("QLabel, QPushButton, QLineEdit {font-size: 9pt;}")

        grid = QGridLayout()

        header_label = QLabel("Введите учетные данные:")
        self.login_edit = QLineEdit()
        self.login_edit.setPlaceholderText("Телефон / Email / СНИЛС")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Пароль")
        self.password_edit.setEchoMode(QLineEdit.Password)
        
        self.checkbox = QCheckBox("Сохранить учетные данные")
        self.checkbox.setChecked(True)

        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.write_config)
        self.buttonBox.rejected.connect(self.reject)

        grid.addWidget(header_label, 0, 0)
        grid.addWidget(self.login_edit, 1, 0)
        grid.addWidget(self.password_edit, 2, 0)
        grid.addWidget(self.checkbox, 3, 0)
        grid.addWidget(self.buttonBox, 4, 0)
        
        self.setLayout(grid)

    def read_config(self):
        cnf = conf.get_configuration()
        login = cnf.get("login", "")
        password = cnf.get("password", "")
        if login and password:
            self.login_edit.setText(login)
            self.password_edit.setText(password)

    def write_config(self):
        login = self.login_edit.text()
        password = self.password_edit.text()
        if login and password:
            if self.checkbox.isChecked():
                conf.write_configuration(login, password)
            self.account.emit(login, password)
            self.close()
        else:
            mb = QMessageBox()
            mb.setWindowTitle("Ошибка")
            mb.setText("Введите учетные данные")
            mb.setIcon(QMessageBox.Warning)
            mb.setStandardButtons(QMessageBox.Ok)
            mb.exec_()
           