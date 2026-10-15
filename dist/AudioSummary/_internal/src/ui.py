import sys
import time
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, QFileDialog, QMessageBox, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal

from src.audio_utils import AudioUtils
from src.transcriber import Transcriber
from src.analyzer import Analyzer


class TranscriptionWorker(QThread):
    progress_signal = pyqtSignal(str)
    segment_signal = pyqtSignal(str)
    metrics_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, filepath, total_duration=0, model_size="tiny"):
        super().__init__()
        self.filepath = filepath
        self.model_size = model_size
        self.total_duration = total_duration

    def run(self):
        try:
            self.progress_signal.emit("准备处理路径...")
            safe_path = AudioUtils.get_safe_path(self.filepath)

            self.progress_signal.emit("加载模型...")
            transcriber = Transcriber(model_size=self.model_size)
            transcriber.load_model()

            self.progress_signal.emit("开始实时转写字幕流...")
            start_time = time.time()

            segments = []
            for seg in transcriber.transcribe_stream(safe_path):
                segments.append(seg)

                # Format for live streaming UI
                start_str = transcriber._format_srt_time(seg['start']).split(',')[0]
                end_str = transcriber._format_srt_time(seg['end']).split(',')[0]
                formatted_str = f"[{start_str} --> {end_str}] 正在发言: {seg['text']}"
                self.segment_signal.emit(formatted_str)

                # Metrics
                elapsed = time.time() - start_time
                processed_audio = seg['end']
                if elapsed > 0:
                    rtf = processed_audio / elapsed

                    eta_str = "-"
                    if rtf > 0 and self.total_duration > 0:
                        remaining_audio = max(0, self.total_duration - processed_audio)
                        eta_seconds = remaining_audio / rtf
                        eta_str = f"{eta_seconds:.1f}s"

                    metrics_str = f"已处理时长: {processed_audio:.1f}s | 实时推理倍速: {rtf:.1f}x | 预计剩余时间: {eta_str}"
                    self.metrics_signal.emit(metrics_str)

            self.finished_signal.emit(segments)

        except Exception as e:
            self.error_signal.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("全功能标杆级智能语音转写助手")
        self.setGeometry(100, 100, 900, 600)

        self.transcriber = Transcriber()
        self.analyzer = Analyzer()

        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()

        # Top controls
        top_layout = QHBoxLayout()
        self.btn_open = QPushButton("选择音频文件")
        self.btn_open.clicked.connect(self.select_file)
        top_layout.addWidget(self.btn_open)

        self.chk_export_srt = QCheckBox("导出标准 .srt 字幕")
        self.chk_export_srt.setChecked(True)
        top_layout.addWidget(self.chk_export_srt)

        self.lbl_metadata = QLabel("元数据: 等待文件...")
        top_layout.addWidget(self.lbl_metadata)
        layout.addLayout(top_layout)

        # Center streaming log
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setPlaceholderText("实时滚动展现最新识别出的时间戳句子，所见即所得 (Live Streaming)...")
        layout.addWidget(self.log_display)

        # Bottom metrics
        self.lbl_metrics = QLabel("指标: 实时推理速度 - / 已处理时长 - / 预计剩余时间 -")
        layout.addWidget(self.lbl_metrics)

        main_widget.setLayout(layout)

    def select_file(self):
        options = QFileDialog.Options()
        filepath, _ = QFileDialog.getOpenFileName(self, "选择音频文件", "", "Audio Files (*.mp3 *.wav);;All Files (*)", options=options)

        if filepath:
            self.start_processing(filepath)

    def start_processing(self, filepath):
        try:
            metadata = AudioUtils.get_metadata(filepath)
            self.current_filepath = filepath
            self.current_duration = metadata['duration']
            self.lbl_metadata.setText(f"时长: {metadata['duration']:.1f}s | 大小: {metadata['file_size']/1024:.1f}KB | 声道: {metadata['channels']} | 格式: {metadata['format']}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取文件元数据: {e}")
            return

        self.log_display.clear()
        self.btn_open.setEnabled(False)

        self.worker = TranscriptionWorker(filepath, total_duration=self.current_duration, model_size="base")
        self.worker.progress_signal.connect(self.update_log)
        self.worker.segment_signal.connect(self.update_log)
        self.worker.metrics_signal.connect(self.update_metrics)
        self.worker.error_signal.connect(self.show_error)
        self.worker.finished_signal.connect(self.processing_finished)
        self.worker.start()

    def update_log(self, text):
        self.log_display.append(text)

    def update_metrics(self, text):
        self.lbl_metrics.setText(text)

    def show_error(self, err_msg):
        self.btn_open.setEnabled(True)
        QMessageBox.critical(self, "异常诊断与防御", err_msg)

    def processing_finished(self, segments):
        self.update_log("\n--- 转写完成，开始离线深度提炼 ---")
        try:
            # Analyze (Offline fallback)
            txt, md_conv, md_sum, md_req = self.analyzer.analyze(segments)

            base_dir = os.path.dirname(self.current_filepath)
            base_name = os.path.splitext(os.path.basename(self.current_filepath))[0]

            def save_file(ext, content):
                path = os.path.join(base_dir, f"{base_name}_{ext}")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return path

            save_file("逐字稿.txt", txt)
            save_file("对话记录.md", md_conv)
            save_file("会议纪要.md", md_sum)
            save_file("需求清单.md", md_req)

            msg = "\n生成交付物成功: \n - 逐字稿.txt\n - 对话记录.md\n - 会议纪要.md\n - 需求清单.md"

            # Export SRT if checked
            if self.chk_export_srt.isChecked():
                srt_content = self.transcriber.generate_srt(segments)
                save_file("字幕.srt", srt_content)
                msg += "\n - 字幕.srt"

            self.update_log(msg)
            QMessageBox.information(self, "完成", "转写和分析全部完成！\n文件已保存至音频同目录。")

        except Exception as e:
            self.show_error(f"分析失败: {e}")

        self.btn_open.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
