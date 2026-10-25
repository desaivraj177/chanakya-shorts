import os, json, asyncio, requests, subprocess
import google.generativeai as genai
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. Check Secrets First
required_keys = ["GEMINI_API_KEY", "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
for k in required_keys:
    if not os.environ.get(k):
        raise ValueError(f"ERROR: GitHub Secrets में '{k}' नहीं मिला! कृपया Settings -> Secrets में जाकर इसे सही नाम से डालें।")

# 2. topics.txt से आज का टॉपिक उठाना
with open("topics.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

if not lines:
    print("सारे टॉपिक्स खत्म हो गए!")
    exit()

current_topic = lines[0]
remaining_lines = lines[1:]
print("Making video on:", current_topic)

# 3. Gemini AI से 5 सीन की स्क्रिप्ट बनवाना (Auto Fallback Model के साथ)
genai.configure(api_key=os.environ["GEMINI_API_KEY"].strip())

prompt = f"""
Topic: {current_topic} (Chanakya Niti Dark Psychology)
Create a viral 40-second Hindi YouTube Short script divided into 5 scenes.
Return ONLY valid JSON in this exact format (no markdown, no backticks):
{{
  "title": "Chanakya Niti: कड़वा सच! #shorts #chanakyaniti",
  "description": "Chanakya Niti lesson in Hindi #shorts #motivation #darkpsychology",
  "scenes": [
    {{
      "text": "Scene 1 short suspenseful Hindi line in Devanagari (max 15 words)",
      "image_prompt": "Ancient Indian philosopher Chanakya in dark mysterious palace, 3D animated Pixar style, dramatic lighting, vertical 9:16"
    }},
    {{
      "text": "Scene 2 Hindi line in Devanagari",
      "image_prompt": "3D animated Pixar style scene matching line 2, dark moody lighting, vertical 9:16"
    }},
    {{
      "text": "Scene 3 Hindi line in Devanagari",
      "image_prompt": "3D animated Pixar style scene matching line 3, dramatic shadows, vertical 9:16"
    }},
    {{
      "text": "Scene 4 Hindi line in Devanagari",
      "image_prompt": "3D animated Pixar style scene matching line 4, glowing eyes, intense, vertical 9:16"
    }},
    {{
      "text": "Scene 5 final powerful twist line in Hindi",
      "image_prompt": "3D animated Pixar style Chanakya smiling mysteriously in shadows, epic lighting, vertical 9:16"
    }}
  ]
}}
"""

response = None
for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        if response and response.text:
            print("Used model:", model_name)
            break
    except Exception as e:
        print(f"Model {model_name} skipped:", e)

clean_json = response.text.strip()
if "```" in clean_json:
    clean_json = clean_json.split("```")[1].replace("json", "", 1).strip()

data = json.loads(clean_json)

# 4. हर सीन की आवाज़ + सबटाइटल + 3D Cartoon Photo + Zoom Animation बनाना
clip_files = []

def format_srt_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

for i, scene in enumerate(data["scenes"]):
    voice_file = f"voice_{i}.mp3"
    sub_file = f"sub_{i}.srt"
    img_file = f"img_{i}.jpg"
    clip_file = f"clip_{i}.mp4"

    # A. आवाज़ बनाना (बिना क्रैश हुए)
    async def make_scene_audio():
        communicate = edge_tts.Communicate(scene["text"], "hi-IN-MadhurNeural", rate="+8%", pitch="-5Hz")
        await communicate.save(voice_file)

    asyncio.run(make_scene_audio())

    # ऑडियो की लंबाई निकालना
    dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", voice_file]
    duration = float(subprocess.check_output(dur_cmd).decode().strip())
    frames = max(int(duration * 25), 25)

    # B. कस्टम SRT सबटाइटल बनाना (100% Error-Free)
    words = scene["text"].split()
    mid = max(len(words) // 2, 1)
    part1 = " ".join(words[:mid])
    part2 = " ".join(words[mid:])
    with open(sub_file, "w", encoding="utf-8") as sf:
        if part2:
            sf.write(f"1\n00:00:00,000 --> {format_srt_time(duration/2)}\n{part1}\n\n")
            sf.write(f"2\n{format_srt_time(duration/2)} --> {format_srt_time(duration)}\n{part2}\n")
        else:
            sf.write(f"1\n00:00:00,000 --> {format_srt_time(duration)}\n{part1}\n")

    # C. Pollinations AI से 3D Animated फोटो डाउनलोड करना
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(scene['image_prompt'])}?width=1080&height=1920&nologo=true&seed={i+500}"
    img_Success = False
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(img_file, "wb") as f:
                    f.write(r.content)
                img_Success = True
                break
        except Exception as e:
            print("Image retry:", e)

    if not img_Success:
        # अगर इंटरनेट स्लो हो तो डार्क बैकग्राउंड बना दे ताकि वीडियो रुके नहीं
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1", "-frames:v", "1", img_file], check=True)

    # D. फोटो पर Zoom Effect + पीले Subtitles लगाना
    zoom_expr = "min(zoom+0.0025,1.35)" if i % 2 == 0 else "if(eq(on,1),1.35,max(1.0,zoom-0.0025))"
    vf_filter = (
        f"scale=2160:3840,"
        f"zoompan=z='{zoom_expr}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=25,"
        f"subtitles={sub_file}:force_style='FontName=Noto Sans Devanagari,FontSize=18,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=2,Alignment=10,Bold=1'"
    )

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", img_file, "-i", voice_file,
        "-vf", vf_filter, "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-shortest", clip_file
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    clip_files.append(f"file '{clip_file}'")

# 5. सारे 5 सीन्स को जोड़कर Final Short बनाना
with open("concat.txt", "w") as f:
    f.write("\n".join(clip_files))

subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "final_short.mp4"], check=True)

# 6. YouTube पर ऑटोमैटिक अपलोड करना
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
        "tags": ["chanakyaniti", "shorts", "darkpsychology", "hindifacts"],
        "categoryId": "27"
    },
    "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
}

media = MediaFileUpload("final_short.mp4", chunksize=-1, resumable=True)
youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()

# 7. इस्तेमाल हो चुके टॉपिक को हटाकर फाइल अपडेट करना
with open("topics.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(remaining_lines))

print("Successfully created and uploaded:", data["title"])
