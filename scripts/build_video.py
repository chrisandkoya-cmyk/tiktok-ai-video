#!/usr/bin/env python3
"""
สคริปต์สร้างคลิปสั้นแนวตั้งสำหรับ TikTok อัตโนมัติ (9:16)
ขั้นตอน:
1. สร้างเสียงพากย์ภาษาไทยทีละท่อนด้วย edge-tts
2. คำนวณเวลาและสร้างไฟล์ซับไตเติล ASS (ตำแหน่งปลอดภัยสำหรับ TikTok)
3. สร้างซาวด์บรรยากาศหลอนๆ และเสียงกระแทกตอนหักมุมด้วย NumPy
4. ตัดต่อภาพพร้อมเอฟเฟกต์ซูม/แพน + ขอบมืด + ซับไตเติล + เสียง ด้วย FFmpeg
"""

import asyncio
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts
import numpy as np


def run_cmd(cmd: list[str]) -> str:
    """รันคำสั่งภายนอกและคืนค่า stdout"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"คำสั่งล้มเหลว: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def get_audio_duration(audio_path: Path) -> float:
    """อ่านความยาวไฟล์เสียงเป็นวินาทีด้วย ffprobe"""
    out = run_cmd([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ])
    return float(out)


async def generate_tts_line(text: str, out_mp3: Path, voice: str, rate: str, pitch: str) -> None:
    """สร้างเสียงพากย์ 1 ท่อนด้วย edge-tts"""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(out_mp3))


def format_ass_time(seconds: float) -> str:
    """แปลงวินาทีเป็นรูปแบบเวลา ASS (H:MM:SS.cs)"""
    cs_total = max(0, int(round(seconds * 100)))
    cs = cs_total % 100
    s_total = cs_total // 100
    s = s_total % 60
    m_total = s_total // 60
    m = m_total % 60
    h = m_total // 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def wrap_thai_subtitle(text: str, max_chars: int = 24) -> str:
    """ตัดบรรทัดซับภาษาไทยให้พอดีจอมือถือแนวตั้ง"""
    if len(text) <= max_chars:
        return text
    # พยายามแบ่งตรงช่องว่างใกล้กึ่งกลางก่อน
    mid = len(text) // 2
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    if spaces:
        best = min(spaces, key=lambda idx: abs(idx - mid))
        if 6 <= best <= len(text) - 6:
            return text[:best].strip() + r"\N" + text[best + 1:].strip()
    return text


def build_ass_file(subtitles: list[dict], out_ass: Path, width: int, height: int) -> None:
    """สร้างไฟล์ซับไตเติล ASS สไตล์ TikTok ตัวหนา อ่านง่าย"""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Loma,62,&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,6,3,2,90,90,460,1
Style: Accent,Loma,66,&H0038D5FF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,6,3,2,90,90,460,1
Style: Horror,Loma,74,&H002828FF,&H000000FF,&H00000000,&HB0000000,-1,0,0,0,100,100,1,0,1,7,4,2,80,80,460,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    style_map = {
        "default": "Default",
        "accent": "Accent",
        "horror": "Horror",
    }
    lines = [header]
    for sub in subtitles:
        st = format_ass_time(sub["start"])
        et = format_ass_time(sub["end"])
        style_name = style_map.get(sub.get("style", "default"), "Default")
        wrapped = wrap_thai_subtitle(sub["text"])
        # ใส่เอฟเฟกต์เฟดเข้า-ออกนุ่มนวล และซูมเด้งเล็กน้อยตอนขึ้นข้อความ
        fx = r"{\fad(80,80)\t(0,120,\fscx104\fscy104)\t(120,240,\fscx100\fscy100)}"
        lines.append(f"Dialogue: 0,{st},{et},{style_name},,0,0,0,,{fx}{wrapped}")
    out_ass.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_horror_ambient(duration: float, boom_time: float | None, out_wav: Path, sr: int = 44100) -> None:
    """สังเคราะห์ซาวด์บรรยากาศหลอนๆ (Dark Drone + เสียงหัวใจเต้น + Sub-bass Boom ตอนหักมุม)"""
    n = int(math.ceil(duration * sr))
    t = np.linspace(0.0, duration, n, endpoint=False)

    # โทนเสียงต่ำหลอนๆ แบบซ้อนความถี่ (Dark Drone)
    lfo = 0.5 + 0.5 * np.sin(2.0 * np.pi * 0.14 * t)
    drone = (
        0.38 * np.sin(2.0 * np.pi * 51.0 * t + 0.4 * np.sin(2.0 * np.pi * 0.25 * t))
        + 0.24 * np.sin(2.0 * np.pi * 76.5 * t)
        + 0.12 * np.sin(2.0 * np.pi * 103.2 * t) * lfo
        + 0.06 * np.sin(2.0 * np.pi * 218.0 * t) * (0.3 + 0.7 * np.sin(2.0 * np.pi * 0.09 * t) ** 2)
    )

    # เสียงหัวใจเต้นช้าๆ เพิ่มความกดดัน (ทุก 1.35 วินาที)
    heartbeat = np.zeros(n, dtype=np.float64)
    beat_period = 1.35
    cur = 1.2
    while cur < duration - 1.5:
        for offset, amp in [(0.0, 0.45), (0.24, 0.28)]:
            idx0 = int((cur + offset) * sr)
            pulse_len = int(0.18 * sr)
            if idx0 + pulse_len < n:
                pt = np.linspace(0.0, 0.18, pulse_len, endpoint=False)
                env = np.exp(-pt * 24.0) * np.sin(np.pi * pt / 0.18)
                pulse = amp * env * np.sin(2.0 * np.pi * (62.0 - 20.0 * pt / 0.18) * pt)
                heartbeat[idx0:idx0 + pulse_len] += pulse
        cur += beat_period

    # เสียงลม/หมอกเบาๆ (Filtered Noise)
    rng = np.random.default_rng(42)
    noise = rng.normal(0.0, 1.0, n)
    # กรองความถี่สูงออกด้วยค่าเฉลี่ยเคลื่อนที่ให้เสียงนุ่มเหมือนลมในความมืด
    kernel = np.ones(45) / 45.0
    wind = np.convolve(noise, kernel, mode="same") * 0.25

    mix = 0.45 * drone + 0.55 * heartbeat + 0.35 * wind

    # เสียงกระแทก Sub-bass Boom ตอนเฉลยหักมุม
    if boom_time is not None and 0.0 < boom_time < duration:
        idx0 = int(boom_time * sr)
        boom_len = min(int(1.8 * sr), n - idx0)
        if boom_len > 0:
            bt = np.linspace(0.0, boom_len / sr, boom_len, endpoint=False)
            freq_sweep = 95.0 * np.exp(-bt * 2.2) + 32.0
            phase = 2.0 * np.pi * np.cumsum(freq_sweep) / sr
            boom_env = np.exp(-bt * 1.9) * np.minimum(1.0, bt / 0.015)
            mix[idx0:idx0 + boom_len] += 0.95 * boom_env * np.sin(phase)

    # เฟดเข้า-ออกนุ่มนวล
    fade_in = min(int(1.2 * sr), n)
    fade_out = min(int(1.5 * sr), n)
    mix[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    mix[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)

    # ปรับระดับเสียงไม่ให้แตก (Peak Normalize ที่ 0.85)
    peak = np.max(np.abs(mix)) + 1e-9
    mix = (mix / peak) * 0.85
    pcm = np.int16(mix * 32767)

    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def render_scene_clip(
    image_path: Path,
    duration: float,
    motion: str,
    width: int,
    height: int,
    fps: int,
    out_mp4: Path,
) -> None:
    """เรนเดอร์ 1 ฉากจากภาพนิ่งพร้อมเอฟเฟกต์ซูม/แพนช้าๆ และขอบมืดหลอน"""
    frames = max(1, int(math.ceil(duration * fps)))
    # ขยายภาพก่อนเข้า zoompan เพื่อลดอาการภาพสั่น (jitter)
    up_w, up_h = width * 2, height * 2

    if motion == "zoom_in_fast":
        zp = f"zoompan=z='min(zoom+0.0012,1.22)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}"
    elif motion == "zoom_in_slow":
        zp = f"zoompan=z='min(zoom+0.0005,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}"
    elif motion == "pan_right":
        zp = f"zoompan=z='1.12':x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}"
    else:
        # ค่าเริ่มต้น: ซูมเข้าช้าๆ
        zp = f"zoompan=z='min(zoom+0.0007,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}"

    vf = (
        f"scale={up_w}:{up_h}:force_original_aspect_ratio=increase,"
        f"crop={up_w}:{up_h},"
        f"{zp},"
        f"vignette=PI/4.5,"
        f"format=yuv420p"
    )

    run_cmd([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-an",
        str(out_mp4),
    ])


async def build_episode(episode_dir: Path) -> Path:
    """ฟังก์ชันหลักสำหรับสร้างคลิปครบทุกขั้นตอน"""
    story_path = episode_dir / "story.json"
    story = json.loads(story_path.read_text(encoding="utf-8"))

    audio_dir = episode_dir / "assets" / "audio"
    tmp_dir = episode_dir / "tmp"
    out_dir = episode_dir / "output"
    for d in (audio_dir, tmp_dir, out_dir):
        d.mkdir(parents=True, exist_ok=True)

    voice = story.get("voice", "th-TH-NiwatNeural")
    rate = story.get("rate", "-8%")
    pitch = story.get("pitch", "-8Hz")
    width = int(story.get("width", 1080))
    height = int(story.get("height", 1920))
    fps = int(story.get("fps", 30))

    print("1/5 กำลังสร้างเสียงพากย์ภาษาไทยทีละท่อน...")
    concat_audio_inputs: list[Path] = []
    subtitles: list[dict] = []
    scene_durations: list[tuple[dict, float]] = []
    current_time = 0.0
    boom_time: float | None = None

    # เพิ่มความเงียบสั้นๆ ตอนเปิดคลิป 0.25 วินาที
    intro_sil = tmp_dir / "sil_intro.wav"
    run_cmd([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", "0.25", "-c:a", "pcm_s16le", str(intro_sil),
    ])
    concat_audio_inputs.append(intro_sil)
    current_time += 0.25

    for s_idx, scene in enumerate(story["scenes"], start=1):
        scene_start = current_time
        lines = scene["lines"]
        for l_idx, line in enumerate(lines, start=1):
            mp3_path = audio_dir / f"{scene['id']}_line_{l_idx:02d}.mp3"
            wav_path = tmp_dir / f"{scene['id']}_line_{l_idx:02d}.wav"
            await generate_tts_line(line["text"], mp3_path, voice, rate, pitch)

            # แปลงเป็น WAV 44.1kHz mono เพื่อรวมไฟล์ได้เนียนไม่เพี้ยนเวลา
            run_cmd([
                "ffmpeg", "-y", "-i", str(mp3_path),
                "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path),
            ])
            dur = get_audio_duration(wav_path)

            # บันทึกเวลาสำหรับ Sub-bass Boom ในประโยคหักมุม
            if scene.get("boom_at_last_line") and l_idx == len(lines):
                boom_time = current_time

            subtitles.append({
                "start": current_time,
                "end": current_time + dur + 0.08,
                "text": line["text"],
                "style": line.get("style", "default"),
            })
            concat_audio_inputs.append(wav_path)
            current_time += dur

            pause = float(line.get("pause_after", 0.3))
            if pause > 0:
                sil_path = tmp_dir / f"{scene['id']}_sil_{l_idx:02d}.wav"
                run_cmd([
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", f"{pause:.3f}", "-c:a", "pcm_s16le", str(sil_path),
                ])
                concat_audio_inputs.append(sil_path)
                current_time += pause

        scene_dur = current_time - scene_start
        # ฉากแรกบวกเวลา intro 0.25 วิเข้าไปด้วยเพื่อให้ภาพเริ่มตั้งแต่ 0.00
        if s_idx == 1:
            scene_dur += 0.25
        scene_durations.append((scene, scene_dur))

    total_duration = current_time
    print(f"   ความยาวคลิปรวม: {total_duration:.2f} วินาที")

    # รวมเสียงพากย์ทั้งหมดเป็นไฟล์เดียว
    print("2/5 กำลังรวมเสียงพากย์และสังเคราะห์ซาวด์บรรยากาศหลอน...")
    audio_list_txt = tmp_dir / "audio_list.txt"
    audio_list_txt.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in concat_audio_inputs) + "\n",
        encoding="utf-8",
    )
    voiceover_wav = audio_dir / "voiceover_full.wav"
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(audio_list_txt),
        "-c:a", "pcm_s16le", str(voiceover_wav),
    ])

    ambient_wav = audio_dir / "horror_ambient.wav"
    generate_horror_ambient(total_duration, boom_time, ambient_wav)

    # มิกซ์เสียงพากย์ + เสียงบรรยากาศหลอน
    final_audio_m4a = audio_dir / "final_mix.m4a"
    run_cmd([
        "ffmpeg", "-y",
        "-i", str(voiceover_wav),
        "-i", str(ambient_wav),
        "-filter_complex",
        "[0:a]volume=1.15,acompressor=threshold=-16dB:ratio=3:attack=5:release=60[v];"
        "[1:a]volume=0.22[bg];"
        "[v][bg]amix=inputs=2:duration=first:dropout_transition=2,alimiter=limit=0.95[out]",
        "-map", "[out]",
        "-c:a", "aac", "-b:a", "192k",
        str(final_audio_m4a),
    ])

    # สร้างไฟล์ซับไตเติล ASS
    print("3/5 กำลังสร้างซับไตเติลสไตล์ TikTok...")
    ass_path = tmp_dir / "subtitles.ass"
    build_ass_file(subtitles, ass_path, width, height)

    # เรนเดอร์วิดีโอแต่ละฉาก
    print("4/5 กำลังเรนเดอร์ภาพเคลื่อนไหวทั้ง 6 ฉาก...")
    scene_clips: list[Path] = []
    for scene, dur in scene_durations:
        img_path = episode_dir / scene["image"]
        clip_path = tmp_dir / f"{scene['id']}.mp4"
        render_scene_clip(img_path, dur, scene.get("motion", "zoom_in"), width, height, fps, clip_path)
        scene_clips.append(clip_path)

    # ต่อฉากทั้งหมด + ใส่เฟดดำตอนจบ + ฝังซับไตเติล + รวมเสียง
    print("5/5 กำลังประกอบคลิปสุดท้าย...")
    video_list_txt = tmp_dir / "video_list.txt"
    video_list_txt.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in scene_clips) + "\n",
        encoding="utf-8",
    )
    raw_video = tmp_dir / "raw_concat.mp4"
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(video_list_txt),
        "-c", "copy", str(raw_video),
    ])

    out_mp4 = out_dir / f"{episode_dir.name}.mp4"
    fade_out_start = max(0.0, total_duration - 1.1)
    # หนีอักขระพิเศษใน path สำหรับตัวกรอง ass ของ ffmpeg
    ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", r"\:")
    run_cmd([
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-i", str(final_audio_m4a),
        "-vf", f"ass='{ass_escaped}',fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.2f}:d=1.0",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-shortest",
        str(out_mp4),
    ])

    print(f"เสร็จสมบูรณ์! ไฟล์คลิปอยู่ที่: {out_mp4}")
    return out_mp4


def main() -> None:
    if len(sys.argv) < 2:
        print("การใช้งาน: python3 scripts/build_video.py <โฟลเดอร์ตอน>")
        sys.exit(1)
    episode_dir = Path(sys.argv[1]).resolve()
    asyncio.run(build_episode(episode_dir))


if __name__ == "__main__":
    main()
