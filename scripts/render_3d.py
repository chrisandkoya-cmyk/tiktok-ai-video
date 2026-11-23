#!/usr/bin/env python3
"""
สคริปต์เรนเดอร์แอนิเมชัน 3D Roblox R6 ทีละเฟรมด้วย Playwright + Three.js
แล้วส่งเฟรมเข้า FFmpeg โดยตรงเพื่อสร้างไฟล์วิดีโอ MP4 แนวตั้ง 1080x1920
"""

import json
import math
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def render_3d_video(
    scene_html: Path,
    timeline_json: Path,
    out_mp4: Path,
    render_w: int = 540,
    render_h: int = 960,
    out_w: int = 1080,
    out_h: int = 1920,
    fps: int = 24,
) -> None:
    """เปิดหน้า Three.js แบบ headless และจับภาพทีละเฟรมส่งเข้า FFmpeg"""
    timeline = json.loads(timeline_json.read_text(encoding="utf-8"))
    duration = float(timeline["duration"])
    total_frames = max(1, int(math.ceil(duration * fps)))

    # เปิด FFmpeg รอรับภาพ JPEG ทีละเฟรมผ่าน stdin
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-framerate", str(fps),
        "-i", "-",
        "-vf", f"scale={out_w}:{out_h}:flags=lanczos,vignette=PI/5,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-an",
        str(out_mp4),
    ]
    ff = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/google-chrome",
                args=[
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--enable-webgl",
                    "--ignore-gpu-blocklist",
                    "--no-sandbox",
                ],
            )
            page = browser.new_page(viewport={"width": render_w, "height": render_h})
            page.goto(scene_html.resolve().as_uri(), wait_until="load")
            page.evaluate("(data) => window.setTimeline(data)", timeline)

            for i in range(total_frames):
                t = i / fps
                page.evaluate("(t) => window.renderAt(t)", t)
                jpg_bytes = page.screenshot(type="jpeg", quality=92)
                ff.stdin.write(jpg_bytes)
                if (i + 1) % 150 == 0 or (i + 1) == total_frames:
                    pct = int((i + 1) * 100 / total_frames)
                    print(f"   เรนเดอร์ 3D: {i + 1}/{total_frames} เฟรม ({pct}%)", flush=True)

            browser.close()
    finally:
        if ff.stdin:
            ff.stdin.close()

    stderr_out = ff.stderr.read().decode("utf-8", errors="replace") if ff.stderr else ""
    ret = ff.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg เรนเดอร์ 3D ล้มเหลว:\n{stderr_out}")


def main() -> None:
    if len(sys.argv) < 4:
        print("การใช้งาน: python3 scripts/render_3d.py <scene.html> <timeline.json> <out.mp4>")
        sys.exit(1)
    render_3d_video(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))


if __name__ == "__main__":
    main()
