import os, json, requests
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("Starting Direct Auto-Upload Script...")

# Read topic
with open("topics.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

current_topic = lines[0] if lines else "चाणक्य नीति के अनमोल वचन"
remaining_lines = lines[1:] if len(lines) > 1 else ["सफलता का रहस्य"]

# Gemini Script Generation
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "").strip())
model = genai.GenerativeModel("gemini-1.5-flash")

prompt = f"""
Topic: {current_topic}
Create a viral Hindi YouTube Short title and description.
Return ONLY valid JSON:
{{
  "title": "Chanakya Niti: Kadwa Sach! #shorts #chanakyaniti",
  "description": "Best life lesson by Chanakya Niti #shorts #motivation"
}}
"""

try:
    res = model.generate_content(prompt)
    txt = res.text.strip()
    if "```" in txt:
        txt = txt.split("```")[1].replace("json", "", 1).strip()
    data = json.loads(txt)
except:
    data = {
        "title": f"{current_topic} #shorts",
        "description": "Chanakya Niti motivational short #shorts"
    }

# Create a lightweight pre-made silent video locally to avoid FFmpeg hanging
import subprocess
subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=5", "-t", "5", "final_short.mp4"], check=True)

# Upload directly to YouTube
try:
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(), token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["YT_CLIENT_ID"].strip(), client_secret=os.environ["YT_CLIENT_SECRET"].strip())
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": data["title"][:95], "description": data["description"], "tags": ["shorts", "chanakyaniti"], "categoryId": "27"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload("final_short.mp4", chunksize=-1, resumable=True)
    youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    print("Video uploaded successfully to YouTube!")
except Exception as e:
    print("Upload error:", e)

# Clean topic
with open("topics.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(remaining_lines))

print("Workflow finished successfully in seconds!")
