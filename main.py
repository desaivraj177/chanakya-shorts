import os, json, requests, subprocess
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("=== STARTING YOUTUBE AUTOMATION UPLOAD ===")

# 1. Read topic
with open("topics.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

current_topic = lines[0] if lines else "चाणक्य नीति के अनमोल वचन"
remaining_lines = lines[1:] if len(lines) > 1 else ["सफलता का रहस्य"]
print("Current Topic:", current_topic)

# 2. Generate video locally using FFmpeg
print("Generating video file...")
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", 
    "-i", "color=c=black:s=1080x1920:d=10", 
    "-t", "10", 
    "-c:v", "libx264", "-pix_fmt", "yuv420p", 
    "final_short.mp4"
], check=True)

# 3. Upload directly to YouTube Channel using the new Refresh Token
print("Uploading to YouTube...")
yt_token = os.environ.get("YT_REFRESH_TOKEN", "").strip()
yt_cid = os.environ.get("YT_CLIENT_ID", "").strip()
yt_csec = os.environ.get("YT_CLIENT_SECRET", "").strip()

creds = Credentials(
    None, 
    refresh_token=yt_token, 
    token_uri="https://oauth2.googleapis.com/token", 
    client_id=yt_cid, 
    client_secret=yt_csec
)
youtube = build("youtube", "v3", credentials=creds)

body = {
    "snippet": {
        "title": f"Chanakya Niti: {current_topic[:50]} #shorts", 
        "description": "Motivational short by Chanakya Niti #shorts #chanakyaniti #motivation", 
        "tags": ["shorts", "chanakyaniti"], 
        "categoryId": "27"
    },
    "status": {
        "privacyStatus": "public", 
        "selfDeclaredMadeForKids": False
    }
}

media = MediaFileUpload("final_short.mp4", chunksize=-1, resumable=True)
response = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
print("SUCCESS! Video successfully uploaded, YouTube Video ID:", response.get("id"))

# 4. Clean and update topics.txt
with open("topics.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(remaining_lines))

print("=== WORKFLOW COMPLETED SUCCESSFULLY ===")
