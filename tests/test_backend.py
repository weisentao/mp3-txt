import pytest
import os
import shutil
from src.audio_utils import AudioUtils
from src.transcriber import Transcriber
from src.analyzer import Analyzer

def test_safe_path_isolation_complex(real_audio_file, tmp_path):
    # Create a complex path
    complex_dir = tmp_path / "测试#音频&文件 (2026)!/子目录/"
    complex_dir.mkdir(parents=True)
    complex_path = complex_dir / "复杂的 音频 名字.mp3"

    shutil.copy(real_audio_file['mp3'], complex_path)

    # Call the isolation function
    safe_path = AudioUtils.get_safe_path(str(complex_path))

    # Verify the safe path is generated, is pure ascii and exists
    assert os.path.exists(safe_path)
    assert safe_path.isascii()

    # Verify contents match
    with open(complex_path, "rb") as f1, open(safe_path, "rb") as f2:
        assert f1.read() == f2.read()

def test_sliding_window_deduplication(mocker):
    transcriber = Transcriber(model_size="tiny")
    # Mock load model so we don't actually download it for this pure logic test
    mocker.patch.object(transcriber, 'load_model')
    transcriber.model = mocker.Mock()

    # Create mock segments (NamedTuples or similar that Whisper outputs)
    class MockSegment:
        def __init__(self, start, end, text):
            self.start = start
            self.end = end
            self.text = text

    mock_segments = [
        MockSegment(0.0, 2.0, "大家好。"),
        MockSegment(2.0, 4.0, "欢迎来到测试。"),
        MockSegment(4.0, 6.0, "欢迎来到测试。"), # Hallucination (repeat)
        MockSegment(6.0, 8.0, "欢迎来到测试。"), # Hallucination (repeat)
        MockSegment(8.0, 10.0, "我们继续讲。"),
        MockSegment(10.0, 12.0, "大家好。"), # Later valid repeat
    ]

    # Mock transcribe to yield these segments
    transcriber.model.transcribe.return_value = (mock_segments, None)

    # Run the generator
    results = list(transcriber.transcribe_stream("mock_path.mp3"))

    # Should be 3 segments, because "大家好。" is in the last_texts window of size 3 when it appears again
    assert len(results) == 3
    texts = [r['text'] for r in results]
    assert texts == ["大家好。", "欢迎来到测试。", "我们继续讲。"]

def test_diarization_and_extraction_accuracy():
    analyzer = Analyzer()

    mock_segments = [
        {"start": 0.0, "end": 5.0, "text": "我是发言人第一位。"},
        # Gap is 3.0 seconds, so > 2.0 -> speaker change
        {"start": 8.0, "end": 10.0, "text": "确实，我是第二个发言人。我们要总结一下目前的进度。"},
        # Gap is 0.5 seconds, so <= 2.0 -> same speaker
        {"start": 10.5, "end": 15.0, "text": "现在的核心需求是提高性能。"},
        # Gap is 5 seconds, so > 2.0 -> speaker change
        {"start": 20.0, "end": 22.0, "text": "好的，这个需要尽快落实。"}
    ]

    txt, md_conv, md_sum, md_req = analyzer._offline_diarize_and_summarize(mock_segments)

    # Test Diarization alternates properly on >2s gaps
    # seg 0: 发言人A
    # seg 1: 发言人B
    # seg 2: 发言人B
    # seg 3: 发言人A

    assert "**发言人A** (00:00:00 - 00:00:05): 我是发言人第一位。" in md_conv
    assert "**发言人B** (00:00:08 - 00:00:10): 确实，我是第二个发言人。我们要总结一下目前的进度。" in md_conv
    assert "**发言人B** (00:00:10 - 00:00:15): 现在的核心需求是提高性能。" in md_conv
    assert "**发言人A** (00:00:20 - 00:00:22): 好的，这个需要尽快落实。" in md_conv

    # Test Extraction accuracy
    assert "- 确实，我是第二个发言人。我们要总结一下目前的进度。" in md_sum
    assert "- 现在的核心需求是提高性能。" in md_req
    assert "- 好的，这个需要尽快落实。" in md_req

def test_multiple_consecutive_transcriptions(real_audio_file):
    transcriber = Transcriber(model_size="tiny")
    analyzer = Analyzer()

    # Run consecutively 3 times to ensure no memory/state pollution
    for i in range(3):
        segments = list(transcriber.transcribe_stream(real_audio_file['mp3']))
        assert len(segments) > 0

        txt, md_conv, md_sum, md_req = analyzer.analyze(segments)
        assert len(txt) > 0
        assert "需求" in md_req or "安全" in md_sum
        assert "# 会议对话记录" in md_conv
