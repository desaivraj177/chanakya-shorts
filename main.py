import os, json, asyncio, requests, subprocess
import google.generativeai as genai
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. Check Secrets Safely
required_keys = ["GEMINI_API_KEY", "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"]
for k in required_keys:
    if not os.environ.get(k):
        raise ValueError(f"ERROR: GitHub Secrets mein '{k}' nahi mila!")

# 2. Read Topic safely
try:
    with open("topics.txt", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
except Exception as e:
    print("topics.txt padhne me error:", e)
    exit(0)

if not lines:
    print("Sare topics khatam ho gaye!")
    exit(0)

current_topic = lines[0]
remaining_lines = lines[1:]
print("Current Topic:", current_topic)

# 3. Gemini AI Call with Updated Model Names
genai.configure(api_key=os.environ["GEMINI_API_KEY"].strip())

prompt = f"""
Topic: {current_topic} (Chanakya Niti Dark Psychology)
Create a viral 40-second Hindi YouTube Short script divided into 5 scenes.
Return ONLY valid JSON in this exact format (no markdown, no backticks, start with {{ and end with }}):
{{
  "title": "Chanakya Niti: Kadwa Sach! #shorts #chanakyaniti",
  "description": "Chanakya Niti lesson in Hindi #shorts #motivation #darkpsychology",
  "scenes": [
    {{
      "text": "असंभव को संभव बनाने का चाणक्य का यह नियम जान लो",
      "image_prompt": "Ancient Indian philosopher Chanakya in dark mysterious palace, 3D animated Pixar style, vertical 9:16"
    }},
    {{
      "text": "मूर्ख व्यक्ति से कभी बहस मत करो क्योंकि समय बर्बाद होता है",
      "image_prompt": "3D animated Pixar style scene matching line 2, dark moody lighting, vertical 9:16"
    }},
    {{
      "text": "अपना राज़ कभी किसी को मत बताओ वरना पछताओगे",
      "image_prompt": "3D animated Pixar style scene matching line 3, dramatic shadows, vertical 9:16"
    }},
    {{
      "text": "बुरा वक्त इंसान को असली और झूठे लोगों की पहचान कराता है",
      "image_prompt": "3D animated Pixar style scene matching line 4, glowing eyes, intense, vertical 9:16"
    }},
    {{
      "text": "सफलता पाने के लिए चुपचाप मेहनत करो और शोर मत मचाओ",
      "image_prompt": "3D animated Pixar style Chanakya smiling mysteriously in shadows, epic lighting, vertical 9:16"
    }}
  ]
}}
"""

response_text = ""
models_to_try = ["gemini-3.8-flash", "gemini-3.1-pro-preview", "gemini-1.5-flash", "gemini-pro"]

for model_name in models_to_try:
    try:
        print(f"Trying Gemini model: {model_name}...")
        model = genai.GenerativeModel(model_name)
        res = model.generate_content(prompt)
        if res and res.text:
            response_text = res.text.strip()
            print(f"Success with model: {model_name}")
            break
    except Exception as e:
        print(f"Glitch with {model_name}: {e}. Trying next...")

if not response_text:
    print("Warning: Gemini se response nahi mila. Default backup script use ki ja rahi hai.")
    response_text = json.dumps({
        "title": "Chanakya Niti Rahasya #shorts #chanakyaniti",
        "description": "Best Chanakya Niti motivation #shorts",
        "scenes": [
            {"text": current_topic, "image_prompt": "Ancient Indian philosopher Chanakya dark mystery 3D Pixar style vertical 9:16"},
            {"text": "यह बात हमेशा याद रखना जीवन बदल जाएगी", "image_prompt": "Dark psychology ancient India dramatic lighting vertical 9:16"},
            {"text": "अपनी कमजोरी किसी को मत बताओ", "image_prompt": "Mysterious shadows ancient India vertical 9:16"},
            {"text": "समय सबसे बड़ा बलवान है", "image_prompt": "Powerful ancient king dark background vertical 9:16"},
            {"text": "चुपचाप मेहनत करो सफलता शोर मचाएगी", "image_prompt": "Chanakya smiling epic lighting vertical 9:16"}
        ]
    })

if "```" in response_text:
    response_text = response_text.split("```")[1].replace("json", "", 1).strip()

try:
    data = json.loads(response_text)
except Exception as e:
    print("JSON parsing error, fixing automatically:", e)
    data = {
        "title": f"Chanakya Niti #shorts",
        "description": "Motivational short",
        "scenes": [
            {"text": current_topic, "image_prompt": "Chanakya dark Pixar style vertical 9:16"},
            {"text": "यह नियम जीवन बदल देगा", "image_prompt": "Dark psychology vertical 9:16"},
            {"text": "मुसीबत में हिम्मत न हारें", "image_prompt": "Mysterious ancient India vertical 9:16"},
            {"text": "सच हमेशा कड़वा होता है", "image_prompt": "Epic lighting vertical 9:16"},
            {"text": "सफलता आपकी होगी", "image_prompt": "Chanakya smiling vertical 9:16"}
        ]
    }

clip_files = []

def format_srt_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

# 4. Generate Audio, Images & Video Clips with Glitch Protection
for i, scene in enumerate(data["scenes"]):
    voice_file = f"voice_{i}.mp3"
    sub_file = f"sub_{i}.srt"
    img_file = f"img_{i}.jpg"
    clip_file = f"clip_{i}.mp4"

    for attempt in range(3):
        try:
            async def make_scene_audio():
                communicate = edge_tts.Communicate(scene["text"], "hi-IN-MadhurNeural", rate="+8%", pitch="-5Hz")
                await communicate.save(voice_file)
            asyncio.run(make_scene_audio())
            break
        except Exception as e:
            print(f"Audio glitch on attempt {attempt+1}: {e}")

    try:
        dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", voice_file]
        duration = float(subprocess.check_output(dur_cmd).decode().strip())
    except:
        duration = 4.0
    
    frames = max(int(duration * 25), 25)

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

    img_success = False
    for attempt in range(3):
        try:
            url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(scene['image_prompt'])}?width=1080&height=1920&nologo=true&seed={i+500}"
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 500:
                with open(img_file, "wb") as f:
                    f.write(r.content)
                img_success = True
                break
        except Exception as e:
            print(f"Image download glitch on attempt {attempt+1}: {e}")

    if not img_success:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1", "-frames:v", "1", img_file], check=True)

    zoom_expr = "min(zoom+0.0025,1.35)" if i % 2 == 0 else "if(eq(on,1),1.35,max(1.0,zoom-0.0025))"
    vf_filter = (
        f"scale=2160:3840,"
        f"zoompan=z='{zoom_expr}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(iw/zoom/2)':s=1080x1920:fps=25,"
        f"subtitles={sub_file}:force_style='FontName=Noto Sans Devanagari,FontSize=18,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=2,Alignment=10,Bold=1'"
    )

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", img_file, "-i", voice_file,
        "-vf", vf_filter, "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-shortest", clip_file
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    clip_files.append(f"file '{clip_file}'")

with open("concat.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(clip_files))

subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "final_short.mp4"], check=True)

# 5. YouTube Upload with Glitch Protection
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
            "tags": ["chanakyaniti", "shorts", "darkpsychology", "hindifacts"],
            "categoryId": "27"
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }

    media = MediaFileUpload("final_short.mp4", chunksize=-1, resumable=True)
    youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    print("Video successfully uploaded to YouTube!")
except Exception as e:
    print("YouTube upload glitch:", e)

# 6. Update Topics List safely
try:
    with open("topics.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(remaining_lines))
    print("Topics list updated successfully!")
except Exception as e:
    print("Topics list update error:", e)

print("Job completed successfully!")
