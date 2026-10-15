import pytest
import os
from PyQt5.QtWidgets import QMessageBox
from src.ui import MainWindow

def test_ui_initial_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    # Verify window title
    assert window.windowTitle() == "全功能标杆级智能语音转写助手"

    # Verify btn_open is enabled
    assert window.btn_open.isEnabled()

    # Verify chk_export_srt is checked
    assert window.chk_export_srt.isChecked()

    # Verify lbl_metrics text
    assert window.lbl_metrics.text() == "指标: 实时推理速度 - / 已处理时长 - / 预计剩余时间 -"

    # Verify log_display is empty and placeholder is correct
    assert window.log_display.toPlainText() == ""
    assert window.log_display.placeholderText() == "实时滚动展现最新识别出的时间戳句子，所见即所得 (Live Streaming)..."

def test_ui_signals_and_state_flow(qtbot, mocker, real_audio_file):
    window = MainWindow()
    qtbot.addWidget(window)

    # Mock file dialog to select the test audio
    mocker.patch("PyQt5.QtWidgets.QFileDialog.getOpenFileName", return_value=(real_audio_file['mp3'], ""))

    # Mock message box so it doesn't block the UI thread waiting for user input
    mocker.patch("PyQt5.QtWidgets.QMessageBox.information")

    # Start the processing to create the worker
    window.btn_open.click()

    # Verify UI state is updated immediately
    assert not window.btn_open.isEnabled()
    assert window.log_display.toPlainText() == ""
    assert "时长: " in window.lbl_metadata.text()

    # Wait for the worker thread to finish completely and emit finished_signal
    def wait_for_finish():
        return window.btn_open.isEnabled()

    qtbot.waitUntil(wait_for_finish, timeout=120000)

    # Check that UI was updated via signals
    log_content = window.log_display.toPlainText()
    assert "准备处理路径..." in log_content
    assert "加载模型..." in log_content
    assert "开始实时转写字幕流..." in log_content
    assert "正在发言: " in log_content
    assert "--- 转写完成，开始离线深度提炼 ---" in log_content

    assert "已处理时长: " in window.lbl_metrics.text()

    # Verify finish state
    assert window.btn_open.isEnabled()

def test_ui_srt_export_checkbox_toggle(qtbot, mocker, real_audio_file, tmp_path):
    # Setup test audio path
    import shutil
    test_audio = tmp_path / "test_audio.mp3"
    shutil.copy(real_audio_file['mp3'], test_audio)
    test_audio_path = str(test_audio)

    # Run 1: Checked (Default)
    window1 = MainWindow()
    qtbot.addWidget(window1)
    mocker.patch("PyQt5.QtWidgets.QFileDialog.getOpenFileName", return_value=(test_audio_path, ""))
    mocker.patch("PyQt5.QtWidgets.QMessageBox.information")
    window1.btn_open.click()
    qtbot.waitUntil(lambda: window1.btn_open.isEnabled(), timeout=120000)

    base_name = os.path.splitext(test_audio_path)[0]
    assert os.path.exists(f"{base_name}_逐字稿.txt")
    assert os.path.exists(f"{base_name}_对话记录.md")
    assert os.path.exists(f"{base_name}_会议纪要.md")
    assert os.path.exists(f"{base_name}_需求清单.md")
    assert os.path.exists(f"{base_name}_字幕.srt")

    # Cleanup for run 2
    os.remove(f"{base_name}_逐字稿.txt")
    os.remove(f"{base_name}_对话记录.md")
    os.remove(f"{base_name}_会议纪要.md")
    os.remove(f"{base_name}_需求清单.md")
    os.remove(f"{base_name}_字幕.srt")

    # Run 2: Unchecked
    window2 = MainWindow()
    qtbot.addWidget(window2)
    window2.chk_export_srt.setChecked(False)
    window2.btn_open.click()
    qtbot.waitUntil(lambda: window2.btn_open.isEnabled(), timeout=120000)

    assert os.path.exists(f"{base_name}_逐字稿.txt")
    assert os.path.exists(f"{base_name}_对话记录.md")
    assert os.path.exists(f"{base_name}_会议纪要.md")
    assert os.path.exists(f"{base_name}_需求清单.md")
    assert not os.path.exists(f"{base_name}_字幕.srt")

def test_ui_error_handling(qtbot, mocker, real_audio_file):
    window = MainWindow()
    qtbot.addWidget(window)

    mocker.patch("PyQt5.QtWidgets.QFileDialog.getOpenFileName", return_value=(real_audio_file['mp3'], ""))

    # Mock transcriber to raise an exception
    mocker.patch("src.transcriber.Transcriber.load_model", side_effect=RuntimeError("模拟异常: 模型加载失败"))

    mock_critical = mocker.patch("PyQt5.QtWidgets.QMessageBox.critical")

    window.btn_open.click()

    # Wait for the worker to finish and emit error
    qtbot.waitUntil(lambda: window.btn_open.isEnabled(), timeout=5000)

    # Because of Qt's threading, wait a bit for slot execution
    qtbot.wait(100)

    # Verify error messagebox was shown
    mock_critical.assert_called_once()
    assert "模拟异常: 模型加载失败" in mock_critical.call_args[0][2]

    # Verify button is enabled again and we didn't crash
    assert window.btn_open.isEnabled()
