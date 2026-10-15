import pytest
import os

# Set headless mode for PyQt5 tests in Linux sandbox
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from gtts import gTTS
from pydub import AudioSegment

@pytest.fixture(scope="session")
def real_audio_file(tmp_path_factory):
    """Generate a real speech audio file using gTTS"""
    # Create temp directory
    temp_dir = tmp_path_factory.mktemp("audio_test")
    mp3_path = temp_dir / "test_speech.mp3"
    wav_path = temp_dir / "test_speech.wav"

    text = "大家好，咱们把工业互联网的采集接口测通，重点是数据安全和客户需求清单。"
    tts = gTTS(text=text, lang='zh')
    tts.save(str(mp3_path))

    # Convert to wav for full coverage
    audio = AudioSegment.from_mp3(str(mp3_path))
    audio.export(str(wav_path), format="wav")

    return {"mp3": str(mp3_path), "wav": str(wav_path)}

@pytest.fixture(scope="session")
def silent_audio_file(tmp_path_factory):
    """Generate a pure silent audio file"""
    temp_dir = tmp_path_factory.mktemp("silent_audio")
    wav_path = temp_dir / "silence.wav"

    # 5 seconds of silence
    silence = AudioSegment.silent(duration=5000)
    silence.export(str(wav_path), format="wav")

    return str(wav_path)

@pytest.fixture(scope="session")
def complex_path_audio_file(real_audio_file, tmp_path_factory):
    """Copy the real audio to a deep, Chinese-named directory"""
    complex_dir = tmp_path_factory.mktemp("深层 目录 测 试") / "层级1" / "层级2 (特殊符号!)"
    complex_dir.mkdir(parents=True)

    complex_path = complex_dir / "测试 音频.mp3"

    audio = AudioSegment.from_mp3(real_audio_file["mp3"])
    audio.export(str(complex_path), format="mp3")

    return str(complex_path)
