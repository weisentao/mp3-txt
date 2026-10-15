import os
import sys
from typing import Generator, Dict, Any, List
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download

class Transcriber:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None

    def _download_model(self) -> str:
        """
        Loads local model or downloads from hf-mirror.com with fallback to standard HF
        """
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        candidates = [
            os.path.join(base_dir, "models", f"faster-whisper-{self.model_size}"),
            os.path.join(getattr(sys, "_MEIPASS", ""), "models", f"faster-whisper-{self.model_size}"),
            os.path.join(os.getcwd(), "models", f"faster-whisper-{self.model_size}"),
            os.path.join("models", f"faster-whisper-{self.model_size}"),
        ]
        for cand in candidates:
            if cand and os.path.exists(cand):
                print(f"优先自动加载本地离线 Whisper 模型: {cand}")
                return cand

        # Fallback: check if ANY model is present in the models/ directory
        for search_root in [base_dir, os.getcwd(), getattr(sys, "_MEIPASS", "")]:
            if not search_root:
                continue
            models_dir = os.path.join(search_root, "models")
            if os.path.isdir(models_dir):
                for entry in os.listdir(models_dir):
                    sub = os.path.join(models_dir, entry)
                    if os.path.isdir(sub) and entry.startswith("faster-whisper"):
                        print(f"找到本地已预置的 Whisper 模型 ({entry}): {sub}")
                        return sub

        # Download using huggingface_hub from domestic mirror
        # Note: In a real app, environment variables would be set for HF_ENDPOINT
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        print("无本地模型，尝试从内置国内镜像极速下载...")
        try:
            repo_id = f"Systran/faster-whisper-{self.model_size}"
            model_path = snapshot_download(repo_id=repo_id, local_files_only=False)
            return model_path
        except Exception as e:
            print(f"国内镜像下载失败，降级回退: {e}")
            raise Exception("无法加载模型，请检查网络或提供本地模型路径。")

    def load_model(self):
        try:
            model_path = self._download_model()
            # use cpu to be safe in sandbox, compute_type int8 for speed
            self.model = WhisperModel(model_path, device="cpu", compute_type="int8")
        except Exception as e:
            raise RuntimeError(f"模型加载异常: {e}\n诊断建议: 检查网络连接或尝试手动下载。")

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds into HH:MM:SS,mmm"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def generate_srt(self, segments: List[Dict]) -> str:
        """Generate standard SRT format subtitle"""
        srt_lines = []
        for i, seg in enumerate(segments):
            start = self._format_srt_time(seg['start'])
            end = self._format_srt_time(seg['end'])
            text = seg['text'].strip()

            srt_lines.append(f"{i+1}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")
        return "\n".join(srt_lines)

    def transcribe_stream(self, filepath: str) -> Generator[Dict[str, Any], None, None]:
        """
        Transcribes audio and yields segments in real-time.
        Includes sliding window hallucination deduplication.
        """
        if not self.model:
            self.load_model()

        try:
            segments, info = self.model.transcribe(filepath, language="zh", beam_size=5, vad_filter=True)
        except Exception as e:
            raise RuntimeError(f"转写失败: {e}\n诊断建议: 检查音频文件是否损坏，或重试。")

        last_texts = []
        window_size = 3

        for segment in segments:
            text = segment.text.strip()

            # Sliding window deduplication
            if text in last_texts:
                continue # Skip hallucinated repeat

            last_texts.append(text)
            if len(last_texts) > window_size:
                last_texts.pop(0)

            yield {
                "start": segment.start,
                "end": segment.end,
                "text": text
            }
