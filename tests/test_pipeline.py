import pytest
import os
from src.audio_utils import AudioUtils
from src.transcriber import Transcriber
from src.analyzer import Analyzer

# Test 1: Generate real audio, test full pipeline
def test_full_pipeline_with_real_audio(real_audio_file):
    # Preprocessing
    mp3_path = real_audio_file["mp3"]
    meta = AudioUtils.get_metadata(mp3_path)
    assert meta["duration"] > 0
    assert meta["format"] == "mp3"

    # Transcription
    # Use "tiny" for speed in CI
    transcriber = Transcriber(model_size="tiny")

    # This tests the download fallback and execution
    segments_gen = transcriber.transcribe_stream(mp3_path)
    segments = list(segments_gen)

    assert len(segments) > 0

    # 4 Outputs
    analyzer = Analyzer()
    txt, md_conv, md_sum, md_req = analyzer.analyze(segments)

    assert len(txt) > 0
    assert "需求" in md_req or "安全" in md_sum
    assert "# 会议对话记录" in md_conv

# Test 2: Pure silence VAD and hallucination check
def test_pure_silence_audio(silent_audio_file):
    transcriber = Transcriber(model_size="tiny")
    segments_gen = transcriber.transcribe_stream(silent_audio_file)
    segments = list(segments_gen)

    # Due to VAD, segments should be empty or at least not crash
    assert len(segments) == 0

# Test 3: Chinese special characters and deep path stress test
def test_complex_path(complex_path_audio_file):
    # Ensure safe path generation works
    safe_path = AudioUtils.get_safe_path(complex_path_audio_file)
    assert os.path.exists(safe_path)
    # The new path should be ascii only (uuid)
    assert safe_path.isascii()

    meta = AudioUtils.get_metadata(safe_path)
    assert meta["duration"] > 0

# Test 4: SRT subtitle format verification
def test_srt_generation():
    transcriber = Transcriber()
    mock_segments = [
        {"start": 1.234, "end": 4.567, "text": " 第一句话"},
        {"start": 3601.0, "end": 3605.999, "text": "一个小时后的话"}
    ]

    srt = transcriber.generate_srt(mock_segments)

    # Check proper formatting (00:00:00,000)
    assert "00:00:01,234 --> 00:00:04,567" in srt
    assert "01:00:01,000 --> 01:00:05,998" in srt
    assert "第一句话" in srt

# Test 5: Offline fallback disaster recovery
def test_offline_fallback():
    mock_segments = [{"start": 0, "end": 2, "text": "我们需要把系统测通。"}]

    # Initialize with mock API key to force the API try and fail
    analyzer = Analyzer(api_key="mock_invalid_key_for_test")

    # Should not raise exception, should silently fallback to offline
    txt, md_conv, md_sum, md_req = analyzer.analyze(mock_segments)

    assert "把系统测通" in txt
    assert "# 会议纪要" in md_sum
    assert "# 客户需求清单" in md_req
