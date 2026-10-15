import pytest
import os
from pydub import AudioSegment
from src.audio_utils import AudioUtils
from src.transcriber import Transcriber
from src.analyzer import Analyzer

@pytest.fixture(scope="module")
def multi_format_audio(tmp_path_factory):
    """Generate very short audio in various formats for fast metadata parsing check."""
    temp_dir = tmp_path_factory.mktemp("multi_audio")

    # 0.5s short beep
    beep = AudioSegment.silent(duration=500)

    formats = ["mp3", "wav", "flac"]
    paths = {}

    for fmt in formats:
        p = temp_dir / f"test.{fmt}"
        beep.export(str(p), format=fmt)
        paths[fmt] = str(p)

    return paths

def test_metadata_multiple_formats(multi_format_audio):
    """Test the metadata parser handles various audio formats correctly."""
    for fmt, path in multi_format_audio.items():
        meta = AudioUtils.get_metadata(path)
        assert meta["format"] == fmt
        assert 0.4 < meta["duration"] < 0.6  # approx 0.5s
        assert meta["channels"] > 0
        assert meta["file_size"] > 0

def test_extreme_short_audio_transcription(multi_format_audio):
    """Test transcriber doesn't crash on extremely short (<1s) audio."""
    transcriber = Transcriber(model_size="tiny")
    path = multi_format_audio["wav"]

    segments = list(transcriber.transcribe_stream(path))

    # Should complete without crashing, returning 0 segments for silence
    assert len(segments) == 0

def test_consecutive_transcription_stability(real_audio_file):
    """Ensure consecutive transcriptions do not leak memory/state causing clashes."""
    transcriber = Transcriber(model_size="tiny")
    path = real_audio_file["mp3"]

    # Run twice
    for i in range(2):
        segments = list(transcriber.transcribe_stream(path))
        assert len(segments) > 0
        assert "工业" in segments[0]["text"] or "测试" in segments[0]["text"] or "安全" in segments[0]["text"] or "数据" in segments[0]["text"] or "需求" in segments[0]["text"] or "互联网" in segments[0]["text"]

def test_diarization_edge_cases():
    """Test role alignment behavior in edge cases."""
    analyzer = Analyzer()

    # Case 1: Single Speaker (no gaps > 2 seconds)
    segments_single = [
        {"start": 0.0, "end": 1.0, "text": " 第一句话"},
        {"start": 1.5, "end": 2.5, "text": " 接着说"},
        {"start": 3.0, "end": 4.0, "text": " 需求是上线"}
    ]
    txt, md_conv, md_sum, md_req = analyzer.analyze(segments_single)
    # They should all be Speaker A
    assert "**发言人A**" in md_conv
    assert "**发言人B**" not in md_conv
    assert "需求是上线" in md_req

    # Case 2: Fast toggles (> 2 seconds apart triggers alternate)
    segments_toggle = [
        {"start": 0.0, "end": 1.0, "text": " 你好"},
        {"start": 3.5, "end": 4.5, "text": " 总结一下，你好"},
        {"start": 7.0, "end": 8.0, "text": " 好的，需要什么？"}
    ]
    txt2, md_conv2, md_sum2, md_req2 = analyzer.analyze(segments_toggle)
    # Should toggle A -> B -> A
    assert "**发言人A**" in md_conv2
    assert "**发言人B**" in md_conv2
    assert "需要什么" in md_req2
    assert "总结一下" in md_sum2
