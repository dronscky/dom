from PyQt5.QtWidgets import QApplication

from view import MainWindow


if __name__ == "__main__":
    app = QApplication([])
    
    windows = MainWindow()
    
    app.exec_()
