# TikTok AI Video Studio

โปรเจกต์สร้างคลิปสั้นแนวตั้ง `9:16` (`1080x1920`) สำหรับ TikTok อัตโนมัติแบบฟรี 100%

## โครงสร้างโปรเจกต์

```text
tiktok-ai-video/
├── scripts/
│   └── build_video.py          # สคริปต์หลัก: พากย์เสียง + ซาวด์หลอน + ซับไตเติล + เรนเดอร์ MP4
├── episodes/
│   └── ep01-server-3am/        # ตอนที่ 1: อย่าเข้าเซิร์ฟเวอร์ที่มีผู้เล่นแค่ 1 คนตอนตี 3
│       ├── story.json          # สคริปต์และจังหวะเวลาแต่ละฉาก
│       ├── assets/images/      # ภาพ AI แนวตั้ง 9:16
│       ├── assets/audio/       # เสียงพากย์และซาวด์ประกอบ
│       └── output/             # ไฟล์วิดีโอ MP4 พร้อมลง TikTok
└── requirements.txt
```

## วิธีใช้งาน

1. ติดตั้ง `ffmpeg` และไลบรารี Python:
   ```bash
   pip install -r requirements.txt
   ```
2. สั่งสร้างคลิปจากโฟลเดอร์ตอนที่ต้องการ:
   ```bash
   python3 scripts/build_video.py episodes/ep01-server-3am
   ```
3. ไฟล์คลิปสำเร็จรูปจะอยู่ที่ `episodes/<ชื่อตอน>/output/<ชื่อตอน>.mp4`
