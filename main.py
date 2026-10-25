import os, json, requests, subprocess
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("=== STARTING DEBUG UPLOAD SCRIPT ===")

# 1. Read topic
try:
    with open("topics.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
except Exception as e:
    print("Error reading topics.txt:", e)
    lines = []

current_topic = lines[0] if lines else "चाणक्य नीति"
remaining_lines = lines[1:] if len(lines) > 1 else ["सफलता का रहस्य"]
print("Target Topic:", current_topic)

# 2. Generate video locally
print("Generating video file...")
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", 
    "-i", "color=c=black:s=1080x1920:d=5", 
    "-t", "5", 
    "-c:v", "libx264", "-pix_fmt", "yuv420p", 
    "final_short.mp4"
], check=True)

# 3. Upload to YouTube with detailed error catching
print("Attempting YouTube API upload...")
try:
    yt_token = os.environ.get("YT_REFRESH_TOKEN", "").strip()
    yt_cid = os.environ.get("YT_CLIENT_ID", "").strip()
    yt_csec = os.environ.get("YT_CLIENT_SECRET", "").strip()

    if not yt_token or not yt_cid or not yt_csec:
        raise Exception("One or more YouTube Secrets are missing in GitHub repository!")

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
            "description": "Motivational short #shorts #chanakyaniti", 
            "tags": ["shorts", "chanakyaniti"], 
            "categoryId": "27"
        },
        "status": {
            "privacyStatus": "public", 
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload("final_short.mp4", chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    
    print("SUCCESS! YouTube Video ID:", response.get("id"))

except Exception as e:
    print("========================================")
    print("YOUTUBE UPLOAD FAILED DUE TO ERROR:")
    print(str(e))
    print("========================================")

# 4. Clean topic list
try:
    with open("topics.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(remaining_lines))
    print("topics.txt updated.")
except Exception as e:
    print("Topic update error:", e)

print("=== SCRIPT FINISHED ===")
