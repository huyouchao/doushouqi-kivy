"""
sound_manager.py - 跨平台音效管理器（Kivy 版）
用纯 Python 生成 WAV 文件，用 Kivy SoundLoader 播放
替代原版的 winsound（Windows 专有）
"""
import math
import os
import struct
import wave

from kivy.core.audio import SoundLoader

from platform_services.storage import get_cache_dir


SOUND_PROFILES = {
    "move": [(720, 0.08, 0.40), (860, 0.10, 0.35)],
    "capture": [(520, 0.08, 0.55), (410, 0.08, 0.55), (280, 0.12, 0.60)],
    "jump": [(660, 0.07, 0.45), (920, 0.11, 0.50), (1120, 0.08, 0.45)],
    "rat_water": [(440, 0.09, 0.35), (520, 0.09, 0.30), (460, 0.11, 0.28)],
    "trap": [(300, 0.08, 0.45), (220, 0.12, 0.50)],
    "win": [(760, 0.11, 0.50), (960, 0.12, 0.50), (1240, 0.18, 0.55)],
    "lose": [(620, 0.10, 0.42), (420, 0.12, 0.45), (240, 0.18, 0.45)],
    "draw": [(540, 0.08, 0.35), (540, 0.08, 0.35), (620, 0.12, 0.30)],
}


class SoundManager:
    """跨平台音效管理器"""

    def __init__(self):
        self.enabled = True
        self.sound_dir = get_cache_dir("sounds")
        self.sound_files = {}     # {name: wav文件路径}
        self._loaded_sounds = {}  # {name: Sound对象}（缓存）
        self._ensure_sound_files()

    def set_enabled(self, enabled):
        """开关音效"""
        self.enabled = enabled

    def play(self, sound_name):
        """播放指定音效（异步，不阻塞）"""
        if not self.enabled:
            return

        # 尝试从缓存中获取 Sound 对象
        sound = self._loaded_sounds.get(sound_name)
        if sound is None:
            # 首次播放时加载
            file_path = self.sound_files.get(sound_name)
            if not file_path or not os.path.exists(file_path):
                return
            sound = SoundLoader.load(file_path)
            if sound is None:
                return
            self._loaded_sounds[sound_name] = sound

        # 从头播放
        sound.stop()
        sound.play()

    def stop(self):
        """停止所有音效"""
        for sound in self._loaded_sounds.values():
            if sound:
                sound.stop()

    def _ensure_sound_files(self):
        """确保所有音效 WAV 文件已生成"""
        os.makedirs(self.sound_dir, exist_ok=True)
        for name, notes in SOUND_PROFILES.items():
            file_path = os.path.join(self.sound_dir, f"{name}.wav")
            if not os.path.exists(file_path):
                self._write_wave(file_path, notes)
            self.sound_files[name] = file_path

    def _write_wave(self, file_path, notes):
        """用纯 Python 生成 WAV 音效文件（与原版逻辑完全一致）"""
        sample_rate = 22050
        frames = []
        for frequency, duration, amplitude in notes:
            note_frames = int(sample_rate * duration)
            fade = max(1, int(note_frames * 0.08))
            for index in range(note_frames):
                envelope = 1.0
                if index < fade:
                    envelope = index / fade
                elif index > note_frames - fade:
                    envelope = max(0.0, (note_frames - index) / fade)
                sample = amplitude * envelope * math.sin(
                    2 * math.pi * frequency * index / sample_rate
                )
                frames.append(struct.pack("<h", int(sample * 32767)))
            silence_frames = int(sample_rate * 0.02)
            for _ in range(silence_frames):
                frames.append(struct.pack("<h", 0))

        with wave.open(file_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"".join(frames))
