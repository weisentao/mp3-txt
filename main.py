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

import traceback

# Top-level exception hook to prevent silent crash (闪退)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        with open("crash.log", "w", encoding="utf-8") as f:
            f.write(error_msg)
    except Exception:
        pass
    try:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "运行异常", f"程序运行遇到未捕获异常:\n\n{error_msg}")
    except Exception:
        pass

sys.excepthook = handle_exception

from PyQt5.QtWidgets import QApplication
from src.ui import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
