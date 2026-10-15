import os
import sys

# Prevent OpenMP runtime conflict on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Ensure current directory is in sys.path and chdir to app dir when frozen
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(os.path.abspath(sys.executable))
    os.chdir(app_dir)
    sys.path.insert(0, app_dir)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from src.ui import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
