import os, json, asyncio, requests, subprocess
import google.generativeai as genai
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("Starting Fast Short Generator...")

with open("topics.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

current_topic = lines[0] if lines else "चाणक्य नीति के अनमोल वचन"
remaining_lines = lines[1:] if len(lines) > 1 else ["सफलता का रहस्य चाणक्य नीति"]

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "").strip())
model = genai.GenerativeModel("gemini-1.5-flash")

prompt = f"""
Topic: {current_topic}
Create 3 short powerful Hindi script lines for a YouTube Short.
Return ONLY valid JSON:
{{
  "title": "Chanakya Niti #shorts",
  "description": "Motivation #shorts",
  "scenes": [
    {{"text": "जीवन का यह कड़वा सच जान लो", "image_prompt": "Ancient Chanakya dark mystery vertical 9:16"}},
    {{"text": "मूर्ख से कभी बहस मत करो", "image_prompt": "Dark psychology moody lighting vertical 9:16"}},
    {{"text": "चुपचाप मेहनत करो सफलता मिलेगी", "image_prompt": "Chanakya smiling epic lighting vertical 9:16"}}
  ]
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
        "title": "Chanakya Niti #shorts",
        "description": "Motivation",
        "scenes": [
            {"text": current_topic, "image_prompt": "Chanakya dark style vertical 9:16"},
            {"text": "यह नियम जीवन बदल देगा", "image_prompt": "Dark psychology vertical 9:16"},
            {"text": "जीत आपकी होगी", "image_prompt": "Chanakya smiling vertical 9:16"}
        ]
    }

clip_files = []

for i, scene in enumerate(data["scenes"]):
    voice_file = f"voice_{i}.mp3"
    sub_file = f"sub_{i}.srt"
    img_file = f"img_{i}.jpg"
    clip_file = f"clip_{i}.mp4"

    # Audio
    async def make_audio():
        comm = edge_tts.Communicate(scene["text"], "hi-IN-MadhurNeural")
        await comm.save(voice_file)
    asyncio.run(make_audio())

    # Duration
    dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", voice_file]
    duration = float(subprocess.check_output(dur_cmd).decode().strip())
    frames = max(int(duration * 25), 25)

    # Subtitle
    with open(sub_file, "w", encoding="utf-8") as sf:
        sf.write(f"1\n00:00:00,000 --> 00:00:0{int(duration)},000\n{scene['text']}\n")

    # Image
    img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(scene['image_prompt'])}?width=1080&height=1920&nologo=true&seed={i+100}"
    try:
        r = requests.get(img_url, timeout=15)
        with open(img_file, "wb") as f:
            f.write(r.content)
    except:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1", "-frames:v", "1", img_file], check=True)

    # Video Clip
    vf = f"scale=2160:3840,zoompan=z='min(zoom+0.002,1.3)':d={frames}:s=1080x1920:fps=25,subtitles={sub_file}:force_style='FontSize=20,PrimaryColour=&H00FFFF&'"
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img_file, "-i", voice_file, "-vf", vf, "-t", str(duration), "-c:v", "libx264", "-c:a", "aac", "-shortest", clip_file], check=True)
    clip_files.append(f"file '{clip_file}'")

# Merge
with open("concat.txt", "w") as f:
    f.write("\n".join(clip_files))
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "final_short.mp4"], check=True)

# Upload to YouTube
try:
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(), token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["YT_CLIENT_ID"].strip(), client_secret=os.environ["YT_CLIENT_SECRET"].strip())
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": data["title"][:95], "description": data["description"], "tags": ["shorts"], "categoryId": "27"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload("final_short.mp4", chunksize=-1, resumable=True)
    youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    print("Uploaded successfully!")
except Exception as e:
    print("Upload note:", e)

# Clean topic
with open("topics.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(remaining_lines))

print("Done in 1 minute!")
