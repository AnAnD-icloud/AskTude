import os
from pathlib import Path
from typing import Callable, List
from uuid import uuid4

import librosa
import noisereduce as nr
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from sanic.log import logger
from scipy.io import wavfile

from engine.supports import env
from engine.supports.constants import TEMP_AUDIO_DIR


class __AudioChainProcessor:
    def __init__(self):
        self.filters: List[Callable[[str], str]] = []

    def add_filter(self, func: Callable[[str], str]) -> "__AudioChainProcessor":
        self.filters.append(func)
        return self

    def filter(self, audio_input_path: str) -> str:
        for fnc in self.filters:
            original_audio_file_path = audio_input_path
            try:
                logger.debug(f"audio input: {audio_input_path}")
                audio_input_path = fnc(audio_input_path)
                if Path(original_audio_file_path).exists():
                    os.remove(original_audio_file_path)
                logger.debug(f"audio output: {audio_input_path}")
            except Exception as e:
                raise e

        return audio_input_path


def mp4_to_wav(audio_input_path: str) -> str:
    return __sound_converter(audio_input_path, "mp4", "wav")


def __sound_converter(
    audio_input_path: str, input_format: str, output_format: str, codec: str = None
) -> str:
    audio_output_file = os.path.join(TEMP_AUDIO_DIR, f"{uuid4()}.{output_format}")
    sound = AudioSegment.from_file(audio_input_path, format=input_format)
    sound.export(audio_output_file, format=output_format, codec=codec)
    return audio_output_file


def wav_to_webm(audio_input_path: str) -> str:
    return __sound_converter(audio_input_path, "wav", "webm", "libopus")


def remove_music(audio_input_path: str) -> str:
    audio_output_file = os.path.join(TEMP_AUDIO_DIR, f"{uuid4()}.wav")
    y, sr = librosa.load(audio_input_path, sr=None, mono=False)
    if len(y.shape) > 1:
        y = librosa.to_mono(y.T)
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    sf.write(audio_output_file, y_harmonic, sr)
    return audio_output_file


def denoise(audio_path: str) -> str:
    rate, data = wavfile.read(audio_path)
    if data.ndim == 1:
        reduced_noise = nr.reduce_noise(y=data, sr=rate)
    else:
        channels = []
        for i in range(data.shape[1]):
            raw_data = data[:, i]
            reduced_noise_channel = nr.reduce_noise(y=raw_data, sr=rate)
            channels.append(reduced_noise_channel)
        reduced_noise = np.stack(channels, axis=1)
    audio_output_file = os.path.join(TEMP_AUDIO_DIR, f"{uuid4()}.wav")
    wavfile.write(audio_output_file, rate, reduced_noise.astype(np.int16))
    return audio_output_file


def process_audio(audio_path: str) -> str:
    if env.AUDIO_ENHANCE_ENABLED in ["yes", "on", "enabled"]:
        return (
            __AudioChainProcessor()
            .add_filter(mp4_to_wav)
            .add_filter(denoise)
            .add_filter(remove_music)
            .filter(audio_path)
        )
    else:
        return __AudioChainProcessor().add_filter(mp4_to_wav).filter(audio_path)
