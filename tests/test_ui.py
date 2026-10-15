import pytest
import time
from PyQt5.QtCore import Qt
from src.ui import MainWindow

def test_mainwindow_initialization(qtbot):
    """Test the main UI window initializes with correct components."""
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "全功能标杆级智能语音转写助手"
    assert window.btn_open.text() == "选择音频文件"
    assert window.chk_export_srt.isChecked() == True
    assert "元数据: 等待文件..." in window.lbl_metadata.text()

def test_mainwindow_file_selection_mocked(qtbot, monkeypatch, real_audio_file):
    """Test file selection via mocking the QFileDialog and verify UI updates."""
    # Force tiny model globally for the test by mocking TranscriptionWorker class instantiation
    from src import ui
    original_worker = ui.TranscriptionWorker

    class MockWorker(original_worker):
        def __init__(self, filepath, total_duration=0, model_size="base"):
            super().__init__(filepath, total_duration, "tiny")

    monkeypatch.setattr("src.ui.TranscriptionWorker", MockWorker)

    window = MainWindow()
    qtbot.addWidget(window)

    monkeypatch.setattr("src.ui.QMessageBox.information", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.ui.QMessageBox.critical", lambda *args, **kwargs: None)

    # Mock QFileDialog to return our test mp3
    test_path = real_audio_file["mp3"]
    monkeypatch.setattr("src.ui.QFileDialog.getOpenFileName", lambda *args, **kwargs: (test_path, ""))

    # This should trigger start_processing
    qtbot.mouseClick(window.btn_open, Qt.LeftButton)

    # The UI should update to show the file is being processed
    assert not window.btn_open.isEnabled()
    assert "时长:" in window.lbl_metadata.text()
    assert "大小:" in window.lbl_metadata.text()

    # Wait for processing to finish by waiting for the button to re-enable
    qtbot.waitUntil(lambda: window.btn_open.isEnabled(), timeout=15000)

    # Log should contain success messages
    log_text = window.log_display.toPlainText()
    assert "转写完成" in log_text
    assert "逐字稿.txt" in log_text
    assert "字幕.srt" in log_text  # SRT is checked by default

def test_mainwindow_srt_checkbox_toggle(qtbot, monkeypatch, real_audio_file):
    """Test unchecking SRT export."""
    from src import ui
    original_worker = ui.TranscriptionWorker

    class MockWorker(original_worker):
        def __init__(self, filepath, total_duration=0, model_size="base"):
            super().__init__(filepath, total_duration, "tiny")

    monkeypatch.setattr("src.ui.TranscriptionWorker", MockWorker)

    window = MainWindow()
    qtbot.addWidget(window)

    monkeypatch.setattr("src.ui.QMessageBox.information", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.ui.QMessageBox.critical", lambda *args, **kwargs: None)

    # Uncheck the box
    window.chk_export_srt.setChecked(False)

    test_path = real_audio_file["mp3"]
    monkeypatch.setattr("src.ui.QFileDialog.getOpenFileName", lambda *args, **kwargs: (test_path, ""))

    qtbot.mouseClick(window.btn_open, Qt.LeftButton)
    qtbot.waitUntil(lambda: window.btn_open.isEnabled(), timeout=15000)

    log_text = window.log_display.toPlainText()
    assert "转写完成" in log_text
    assert "字幕.srt" not in log_text # SRT should NOT be in the log

def test_mainwindow_error_handling(qtbot, monkeypatch):
    """Test how the UI handles an invalid file that raises an error in metadata parsing."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Pass a non-existent file path
    monkeypatch.setattr("src.ui.QFileDialog.getOpenFileName", lambda *args, **kwargs: ("/path/to/nothing.mp3", ""))

    # Mock QMessageBox to prevent actual popups blocking tests
    message_box_shown = False
    def mock_warning(*args, **kwargs):
        nonlocal message_box_shown
        message_box_shown = True

    monkeypatch.setattr("src.ui.QMessageBox.warning", mock_warning)

    qtbot.mouseClick(window.btn_open, Qt.LeftButton)

    # Verify popup occurred and button is still enabled
    assert message_box_shown
    assert window.btn_open.isEnabled()
