#!/usr/bin/env python3
"""Add original voiceover, music, and SFX to a pre-sortie briefing video."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np


SR = 48000
VOICE = "Microsoft David Desktop"
EDGE_VOICE = "en-US-GuyNeural"
MIN_VOICE_GAP_S = 0.42
DEFAULT_VOICE_LINES = [
    (0.8, "Pilots, the briefing is complete. The mission now demands unreasonable confidence."),
    (5.4, "Threats are marked. Routes are set. The target area is waiting."),
    (12.2, "Strike flights will push through the planned lanes while the fighters keep the sky honest."),
    (21.2, "Use the terrain, trust the timing, and do not donate altitude to the enemy."),
    (29.2, "The weather picture is known. The radios are set. The package is aligned."),
    (37.1, "This is the part where the map stops being theory and becomes noise, speed, and discipline."),
    (44.0, "Speak with purpose. Shoot with judgment. Move like the entire war is embarrassed to be in your way."),
    (50.4, "Execute the plan. Break the target. Come home loud."),
]
SCENE_CUTS = [0.0, 5.0, 14.0, 22.0, 30.0, 37.0, 43.0, 50.0]


def synthesize_voice_windows(text: str, out_path: Path, voice_name: str, rate: int, volume: int) -> None:
    script = out_path.with_suffix(".ps1")
    script.write_text(
        """
param([string]$Text, [string]$Out, [string]$Voice, [int]$Rate, [int]$Volume)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($Voice)
$s.Rate = $Rate
$s.Volume = $Volume
$s.SetOutputToWaveFile($Out)
$s.Speak($Text)
$s.Dispose()
""".strip(),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-Text",
            text,
            "-Out",
            str(out_path),
            "-Voice",
            voice_name,
            "-Rate",
            str(rate),
            "-Volume",
            str(volume),
        ],
        check=True,
    )


def synthesize_voice_edge(text: str, out_path: Path, voice_name: str, rate: str, volume: str) -> None:
    media_path = out_path.with_suffix(".mp3")
    subprocess.run(
        [
            "python",
            "-m",
            "edge_tts",
            "--voice",
            voice_name,
            "--rate",
            rate,
            "--volume",
            volume,
            "--text",
            text,
            "--write-media",
            str(media_path),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(media_path),
            "-ar",
            str(SR),
            "-ac",
            "1",
            str(out_path),
        ],
        check=True,
    )


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sr = wav.getframerate()
        width = wav.getsampwidth()
        frames = wav.readframes(wav.getnframes())
    if width == 2:
        data = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 1:
        data = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported WAV sample width {width} in {path}")
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data, sr


def read_audio_with_ffmpeg(path: Path, work_dir: Path, *, duration: float | None = None) -> tuple[np.ndarray, int]:
    wav_path = work_dir / f"{path.stem}_decoded.wav"
    command = ["ffmpeg", "-y", "-v", "error", "-i", str(path)]
    if duration:
        command.extend(["-t", str(duration)])
    command.extend(["-ar", str(SR), "-ac", "2", str(wav_path)])
    subprocess.run(command, check=True)
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        sr = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    return audio.reshape(-1, channels), sr


def resample(audio: np.ndarray, src_sr: int, dst_sr: int = SR) -> np.ndarray:
    if src_sr == dst_sr:
        return audio.astype(np.float32)
    if len(audio) == 0:
        return audio.astype(np.float32)
    old_x = np.linspace(0.0, 1.0, len(audio), endpoint=False)
    new_len = max(1, int(round(len(audio) * dst_sr / src_sr)))
    new_x = np.linspace(0.0, 1.0, new_len, endpoint=False)
    return np.interp(new_x, old_x, audio).astype(np.float32)


def resample_stereo(audio: np.ndarray, src_sr: int, dst_sr: int = SR) -> np.ndarray:
    if src_sr == dst_sr:
        return audio.astype(np.float32)
    return np.column_stack([resample(audio[:, 0], src_sr, dst_sr), resample(audio[:, 1], src_sr, dst_sr)]).astype(np.float32)


def bandlimit_voice(audio: np.ndarray) -> np.ndarray:
    if len(audio) == 0:
        return audio
    spec = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1.0 / SR)
    mask = (freqs >= 90.0) & (freqs <= 5200.0)
    spec *= mask
    filtered = np.fft.irfft(spec, n=len(audio)).astype(np.float32)
    return np.tanh(filtered * 1.28) * 0.80


def pitch_down(audio: np.ndarray, factor: float = 0.86) -> np.ndarray:
    if len(audio) == 0:
        return audio
    new_len = max(1, int(round(len(audio) / factor)))
    old_x = np.linspace(0.0, 1.0, len(audio), endpoint=False)
    new_x = np.linspace(0.0, 1.0, new_len, endpoint=False)
    return np.interp(new_x, old_x, audio).astype(np.float32)


def envelope(signal: np.ndarray, attack: int = 1600, release: int = 9600) -> np.ndarray:
    env = np.abs(signal)
    out = np.zeros_like(env)
    value = 0.0
    for i, sample in enumerate(env):
        coeff = 1.0 / (attack if sample > value else release)
        value += (sample - value) * coeff
        out[i] = value
    peak = float(out.max()) if out.size else 0.0
    if peak > 0:
        out = np.clip(out / peak, 0.0, 1.0)
    return out


def add_pulse(track: np.ndarray, start_s: float, freq: float, amp: float, dur_s: float, pan: float = 0.0) -> None:
    start = int(start_s * SR)
    length = int(dur_s * SR)
    if start >= len(track):
        return
    length = min(length, len(track) - start)
    t = np.arange(length, dtype=np.float32) / SR
    env = np.exp(-t * 7.5)
    tone = np.sin(2 * math.pi * freq * t) * env * amp
    left = math.cos((pan + 1.0) * math.pi / 4.0)
    right = math.sin((pan + 1.0) * math.pi / 4.0)
    track[start : start + length, 0] += tone * left
    track[start : start + length, 1] += tone * right


def add_noise_hit(track: np.ndarray, start_s: float, amp: float, dur_s: float, pan: float, seed: int) -> None:
    start = int(start_s * SR)
    length = int(dur_s * SR)
    if start >= len(track):
        return
    length = min(length, len(track) - start)
    rng = np.random.default_rng(seed)
    t = np.arange(length, dtype=np.float32) / SR
    noise = rng.normal(0.0, 1.0, size=length).astype(np.float32)
    env = np.exp(-t * 9.0)
    tone = noise * env * amp
    left = math.cos((pan + 1.0) * math.pi / 4.0)
    right = math.sin((pan + 1.0) * math.pi / 4.0)
    track[start : start + length, 0] += tone * left
    track[start : start + length, 1] += tone * right


def saw(freq: float, t: np.ndarray) -> np.ndarray:
    phase = (freq * t) % 1.0
    return (2.0 * phase - 1.0).astype(np.float32)


def add_stab(track: np.ndarray, start_s: float, freqs: list[float], amp: float, dur_s: float, pan: float = 0.0) -> None:
    start = int(start_s * SR)
    length = int(dur_s * SR)
    if start >= len(track):
        return
    length = min(length, len(track) - start)
    t = np.arange(length, dtype=np.float32) / SR
    env = np.minimum(np.clip(t / 0.035, 0.0, 1.0), np.exp(-t * 2.2))
    chord = np.zeros(length, dtype=np.float32)
    for freq in freqs:
        chord += 0.55 * saw(freq, t) + 0.45 * np.sin(2 * math.pi * freq * t)
    chord = np.tanh(chord / max(1, len(freqs)) * 2.2) * env * amp
    left = math.cos((pan + 1.0) * math.pi / 4.0)
    right = math.sin((pan + 1.0) * math.pi / 4.0)
    track[start : start + length, 0] += chord * left
    track[start : start + length, 1] += chord * right


def add_riser(track: np.ndarray, start_s: float, dur_s: float, amp: float, pan: float = 0.0) -> None:
    start = int(start_s * SR)
    length = int(dur_s * SR)
    if start >= len(track):
        return
    length = min(length, len(track) - start)
    t = np.arange(length, dtype=np.float32) / SR
    progress = t / max(dur_s, 0.001)
    freq = 220.0 + progress**1.7 * 1260.0
    phase = np.cumsum(freq) / SR
    tone = np.sin(2 * math.pi * phase) * progress**1.4 * amp
    noise = np.random.default_rng(int(start_s * 1000)).normal(0.0, 0.05, size=length).astype(np.float32)
    tone = (tone + noise * progress) * np.clip((1.0 - progress) / 0.18, 0.0, 1.0)
    left = math.cos((pan + 1.0) * math.pi / 4.0)
    right = math.sin((pan + 1.0) * math.pi / 4.0)
    track[start : start + length, 0] += tone * left
    track[start : start + length, 1] += tone * right


def add_note(track: np.ndarray, start_s: float, freq: float, amp: float, dur_s: float, pan: float = 0.0) -> None:
    start = int(start_s * SR)
    length = int(dur_s * SR)
    if start >= len(track):
        return
    length = min(length, len(track) - start)
    t = np.arange(length, dtype=np.float32) / SR
    env = np.minimum(np.clip(t / 0.018, 0.0, 1.0), np.exp(-t * 8.0))
    tone = (
        0.52 * saw(freq, t)
        + 0.36 * np.sin(2 * math.pi * freq * t)
        + 0.12 * np.sin(2 * math.pi * freq * 2.0 * t + 0.3)
    )
    tone = np.tanh(tone * 1.7) * env * amp
    left = math.cos((pan + 1.0) * math.pi / 4.0)
    right = math.sin((pan + 1.0) * math.pi / 4.0)
    track[start : start + length, 0] += tone * left
    track[start : start + length, 1] += tone * right


def make_music_and_sfx(duration: float) -> np.ndarray:
    n = int(duration * SR)
    t = np.arange(n, dtype=np.float32) / SR
    track = np.zeros((n, 2), dtype=np.float32)

    fade_in = np.clip(t / 4.0, 0.0, 1.0)
    fade_out = np.clip((duration - t) / 4.0, 0.0, 1.0)
    env = np.minimum(fade_in, fade_out)
    lfo = 0.72 + 0.28 * np.sin(2 * math.pi * 0.045 * t)
    chord_roots = [55.0, 51.91, 43.65, 48.99]
    drone = np.zeros(n, dtype=np.float32)
    for i, root in enumerate(chord_roots):
        start = int(i * duration / len(chord_roots) * SR)
        end = int((i + 1) * duration / len(chord_roots) * SR)
        tt = t[: end - start]
        chord = (
            0.24 * np.sin(2 * math.pi * root * tt)
            + 0.15 * np.sin(2 * math.pi * root * 1.5 * tt + 0.4)
            + 0.14 * saw(root * 2.0, tt)
            + 0.07 * np.sin(2 * math.pi * root * 3.0 * tt + 1.7)
        )
        drone[start:end] = chord[: end - start]
    choir = (
        0.070 * np.sin(2 * math.pi * 220.0 * t + 0.2)
        + 0.055 * np.sin(2 * math.pi * 261.63 * t + 0.7)
        + 0.045 * np.sin(2 * math.pi * 329.63 * t + 1.4)
        + 0.030 * np.sin(2 * math.pi * 392.0 * t + 2.0)
    ) * (0.55 + 0.45 * np.sin(2 * math.pi * 0.08 * t))
    drone = (drone + choir) * env * lfo
    track[:, 0] += drone * 1.10
    track[:, 1] += drone * 1.22

    rng = np.random.default_rng(740)
    static = rng.normal(0.0, 0.011, size=n).astype(np.float32)
    static *= env * (0.55 + 0.45 * np.sin(2 * math.pi * 0.11 * t + 0.5))
    track[:, 0] += static * 0.55
    track[:, 1] += static * 0.45

    for cut in SCENE_CUTS:
        add_riser(track, max(0.0, cut - 1.8), 1.72, 0.16, pan=0.0)
        add_pulse(track, cut + 0.01, 38.0, 0.98, 1.65, pan=-0.1)
        add_pulse(track, cut + 0.03, 76.0, 0.52, 1.12, pan=0.22)
        add_noise_hit(track, cut + 0.03, 0.34, 0.52, pan=0.12, seed=int(cut * 100 + 7))
        add_pulse(track, cut + 0.18, 880.0, 0.22, 0.18, pan=0.45)
        add_pulse(track, cut + 0.34, 1320.0, 0.16, 0.13, pan=-0.5)

    brass_chords = [
        [110.0, 164.81, 196.0, 261.63],
        [98.0, 146.83, 196.0, 246.94],
        [87.31, 130.81, 174.61, 220.0],
        [98.0, 155.56, 196.0, 261.63],
    ]
    for i, beat in enumerate(np.arange(6.0, duration - 2.0, 4.0)):
        add_stab(track, float(beat), brass_chords[i % len(brass_chords)], 0.44, 1.55, pan=float(np.sin(beat * 0.5) * 0.25))
        add_stab(track, float(beat + 1.5), brass_chords[i % len(brass_chords)], 0.24, 0.92, pan=float(np.cos(beat * 0.4) * 0.25))

    ostinato_roots = [220.0, 207.65, 174.61, 196.0]
    for i, beat in enumerate(np.arange(10.0, duration - 1.0, 0.375)):
        section = min(len(ostinato_roots) - 1, int(beat / max(duration, 0.01) * len(ostinato_roots)))
        root = ostinato_roots[section]
        note = root * [1.0, 1.5, 2.0, 1.5][i % 4]
        intensity = 0.035 + 0.055 * min(1.0, beat / max(duration - 8.0, 1.0))
        add_note(track, float(beat), note, intensity, 0.22, pan=float(np.sin(i * 0.6) * 0.35))

    for ping in np.arange(7.0, duration - 1.0, 2.65):
        add_pulse(track, float(ping), 1040.0, 0.075, 0.10, pan=float(np.sin(ping)))

    for beat in np.arange(8.0, duration - 1.0, 0.75):
        accent = 0.34 if int(beat * 2) % 4 == 0 else 0.18
        add_pulse(track, float(beat), 46.0 if int(beat * 2) % 4 == 0 else 72.0, accent, 0.34, pan=0.0)
    for beat in np.arange(14.0, duration - 1.0, 1.5):
        add_noise_hit(track, float(beat), 0.12, 0.11, pan=float(np.sin(beat)), seed=int(beat * 99))

    for beat in np.arange(46.0, duration - 0.8, 0.75):
        add_stab(track, float(beat), brass_chords[int(beat) % len(brass_chords)], 0.30, 0.45, pan=0.0)

    return track


def fit_external_music(path: Path, duration: float, work_dir: Path) -> np.ndarray:
    music, src_sr = read_audio_with_ffmpeg(path, work_dir)
    music = resample_stereo(music, src_sr)
    target_len = int(duration * SR)
    if len(music) == 0:
        return np.zeros((target_len, 2), dtype=np.float32)
    if len(music) < target_len:
        reps = int(math.ceil(target_len / len(music)))
        music = np.tile(music, (reps, 1))
    music = music[:target_len].astype(np.float32)
    fade_len = min(int(2.0 * SR), target_len // 4)
    if fade_len > 0:
        fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
        fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
        music[:fade_len] *= fade_in[:, None]
        music[-fade_len:] *= fade_out[:, None]
    peak = max(0.01, float(np.max(np.abs(music))))
    return music / peak


def write_wav(path: Path, audio: np.ndarray) -> None:
    audio = np.clip(audio, -0.98, 0.98)
    pcm = (audio * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SR)
        wav.writeframes(pcm.tobytes())


def load_voice_lines(path: Path | None) -> list[tuple[float, str]]:
    if path is None:
        return DEFAULT_VOICE_LINES
    if not path.is_file():
        raise FileNotFoundError(f"Voice line file not found: {path}")
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        raw_lines = payload.get("voice_lines", payload) if isinstance(payload, dict) else payload
        lines: list[tuple[float, str]] = []
        for item in raw_lines:
            if isinstance(item, dict):
                start = float(item["start"])
                text = str(item["text"])
            else:
                start = float(item[0])
                text = str(item[1])
            lines.append((start, text))
        return lines
    lines = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        start_text = line.split("|", 1) if "|" in line else line.split(None, 1)
        if len(start_text) != 2:
            raise ValueError(f"Expected '<start>|<text>' voice line, got: {raw}")
        lines.append((float(start_text[0]), start_text[1].strip()))
    return lines


def build_audio(
    duration: float,
    work_dir: Path,
    voice_name: str,
    voice_provider: str,
    music_file: Path | None,
    voice_lines: list[tuple[float, str]],
    *,
    voice_gain: float,
    music_gain: float,
    sfx_gain: float,
    duck_strength: float,
) -> Path:
    n = int(duration * SR)
    voice_mix = np.zeros(n, dtype=np.float32)
    next_available = 0.0
    placements: list[str] = []
    for index, (start_s, text) in enumerate(voice_lines):
        raw_path = work_dir / f"voice_{index:02d}_raw.wav"
        if voice_provider == "edge":
            synthesize_voice_edge(text, raw_path, voice_name, rate="+12%", volume="+18%")
        else:
            synthesize_voice_windows(text, raw_path, voice_name, rate=1, volume=100)
        audio, src_sr = read_wav(raw_path)
        pitch_factor = 0.95 if voice_provider == "edge" else 0.86
        audio = bandlimit_voice(pitch_down(resample(audio, src_sr), factor=pitch_factor))
        echo_delay = int(0.045 * SR)
        if len(audio) > echo_delay:
            echo = np.zeros_like(audio)
            echo[echo_delay:] = audio[:-echo_delay] * 0.15
            audio = np.clip(audio + echo, -0.95, 0.95)
        placed_start_s = max(start_s, next_available)
        start = int(placed_start_s * SR)
        end = min(n, start + len(audio))
        if end > start:
            voice_mix[start:end] += audio[: end - start]
        next_available = end / SR + MIN_VOICE_GAP_S
        placements.append(f"{index:02d} {placed_start_s:05.2f}-{end / SR:05.2f} {text}")
    (work_dir / "voice_placements.txt").write_text("\n".join(placements) + "\n", encoding="utf-8")

    voice_mix = np.clip(voice_mix, -0.95, 0.95)
    voice_env = envelope(voice_mix)
    if music_file:
        music = fit_external_music(music_file, duration, work_dir)
        sfx = make_music_and_sfx(duration)
        music = music * music_gain + sfx * sfx_gain
    else:
        music = make_music_and_sfx(duration) * music_gain
    duck = 1.0 - max(0.0, min(0.95, duck_strength)) * voice_env[:, None]
    stereo_voice = np.column_stack([voice_mix, voice_mix])
    final = music * duck + stereo_voice * voice_gain
    final += np.column_stack([voice_env, voice_env]) * 0.018
    peak = max(0.01, float(np.max(np.abs(final))))
    final = final / peak * 0.92
    out = work_dir / "pre_sortie_voice_music_sfx.wav"
    write_wav(out, final)
    return out


def mux(video: Path, audio: Path, out: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(out),
        ],
        check=True,
    )


def duration_of(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--voice-provider", choices=("edge", "windows"), default="edge")
    parser.add_argument("--voice", default="", help="Voice name. Defaults to en-US-GuyNeural for Edge or Microsoft David Desktop for Windows.")
    parser.add_argument("--music-file", type=Path, help="Optional real music bed to loop/trim under the VO and SFX.")
    parser.add_argument("--voice-lines", type=Path, help="Optional JSON or text file with mission-specific voice lines. JSON may be a list or {'voice_lines': [...]}; text uses '<start>|<text>'.")
    parser.add_argument("--voice-gain", type=float, default=1.58, help="Voice gain before final limiting.")
    parser.add_argument("--music-gain", type=float, default=0.44, help="Music-bed gain before final limiting.")
    parser.add_argument("--sfx-gain", type=float, default=0.14, help="Generated SFX gain before final limiting.")
    parser.add_argument("--duck-strength", type=float, default=0.78, help="How strongly music/SFX duck under voice, from 0 to 0.95.")
    parser.add_argument("--keep-work", type=Path, help="Optional folder to keep generated WAV stems.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.keep_work:
        work_dir = args.keep_work
        work_dir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        work_dir = Path(tempfile.mkdtemp(prefix="pre_sortie_audio_"))
        cleanup = True
    try:
        voice_name = args.voice or (EDGE_VOICE if args.voice_provider == "edge" else VOICE)
        audio = build_audio(
            duration_of(args.video),
            work_dir,
            voice_name,
            args.voice_provider,
            args.music_file,
            load_voice_lines(args.voice_lines),
            voice_gain=args.voice_gain,
            music_gain=args.music_gain,
            sfx_gain=args.sfx_gain,
            duck_strength=args.duck_strength,
        )
        mux(args.video, audio, args.out)
    finally:
        if cleanup:
            shutil.rmtree(work_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
