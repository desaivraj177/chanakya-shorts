import os, json, requests, subprocess
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("Starting Fast YouTube Automation Script...")

# 1. Read topic from topics.txt
try:
    with open("topics.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
except:
    lines = []

current_topic = lines[0] if lines else "चाणक्य नीति के अनमोल वचन"
remaining_lines = lines[1:] if len(lines) > 1 else ["सफलता का रहस्य"]

print("Current Topic:", current_topic)

# 2. Generate title/description using Gemini AI
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
        "title": f"Chanakya Niti: {current_topic} #shorts",
        "description": "Chanakya Niti motivational short #shorts #motivation"
    }

# 3. Create a clean vertical short video locally using FFmpeg
print("Creating video file...")
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", 
    "-i", "color=c=black:s=1080x1920:d=10", 
    "-t", "10", 
    "-c:v", "libx264", "-pix_fmt", "yuv420p", 
    "final_short.mp4"
], check=True)

# 4. Upload directly to your YouTube Channel via API
print("Uploading to YouTube...")
try:
    creds = Credentials(
        None, 
        refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(), 
        token_uri="https://oauth2.googleapis.com/token", 
        client_id=os.environ["YT_CLIENT_ID"].strip(), 
        client_secret=os.environ["YT_CLIENT_SECRET"].strip()
    )
    youtube = build("youtube", "v3", credentials=creds)
    
    body = {
        "snippet": {
            "title": data["title"][:95], 
            "description": data["description"], 
            "tags": ["shorts", "chanakyaniti", "motivation"], 
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
    
    print("SUCCESS! Video uploaded, ID:", response.get("id"))
except Exception as e:
    print("YouTube API Upload Error:", e)

# 5. Remove processed topic from topics.txt
try:
    with open("topics.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(remaining_lines))
    print("topics.txt updated successfully.")
except Exception as e:
    print("Topics update warning:", e)

print("Workflow completed successfully!")
