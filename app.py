from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import shutil
import subprocess
import tempfile
import hashlib 
import glob
import re
import yt_dlp


# Import your existing logic
from utils.transcribe import transcribe_audio
from utils.chunk import create_chunks
from utils.embeddings import create_embeddings_from_chunks
from utils.qa import ask_question, generate_answer, is_video_question,is_follow_up_query

app = FastAPI()

# ✅ NEW: template & static setup
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_FOLDER = "data/videos"
TRANSCRIPT_PATH = "data/transcripts/transcript.txt"
INDEX_PATH = "data/index/index.faiss"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("data/transcripts", exist_ok=True)
os.makedirs("data/index", exist_ok=True)

GLOBAL_CHUNKS = []
LAST_FILE_HASH = None  # ✅ NEW

#FOLLOW UP CONVERSATIONS
CHAT_HISTORY = []


LAST_CONTEXT = ""

# ✅ NEW: GLOBAL PROGRESS TRACKER
UPLOAD_PROGRESS = {
    "progress": 0,
    "status": "Idle"
}

#DOWNLOAD THROUGH LINKS
def download_youtube_audio(url):
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, "%(id)s.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'noplaylist': True,
        'geo_bypass': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android']
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        return os.path.splitext(filename)[0] + ".wav"

# ✅ NEW helper function
def get_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

#PRONOUNS function
def resolve_pronouns(question, topic):
    if not topic:
        return question

    pronouns = ["it", "this", "that", "they", "them", "he", "she"]

    words = question.split()
    new_words = []

    for w in words:
        clean = w.lower().strip(".,!?")

        if clean in pronouns:
            new_words.append(topic)
        else:
            new_words.append(w)

    return " ".join(new_words)


# ✅ NEW: Progress endpoint
@app.get("/progress/")
def get_progress():
    return UPLOAD_PROGRESS

# 🌐 UI Route (UPDATED ONLY THIS PART)
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    global GLOBAL_CHUNKS, CHAT_HISTORY   # ✅ ADD
    
    # 🔥 RESET MEMORY and GLOBAL CHUNKS
    GLOBAL_CHUNKS = []
    CHAT_HISTORY = []   

    if os.path.exists(TRANSCRIPT_PATH):
        os.remove(TRANSCRIPT_PATH)

    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)

    return templates.TemplateResponse("index.html", {"request": request})


# 🎥 Upload + Full Pipeline
@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):
    global GLOBAL_CHUNKS, LAST_FILE_HASH, UPLOAD_PROGRESS, CHAT_HISTORY
    
    global LAST_CONTEXT
    LAST_CONTEXT = ""
    
    CHAT_HISTORY = []
    
    # 🔄 Start progress
    UPLOAD_PROGRESS["progress"] = 5
    UPLOAD_PROGRESS["status"] = "Uploading video..."

    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)

    # temp video
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        shutil.copyfileobj(file.file, temp_video)
        temp_video_path = temp_video.name

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 20
    UPLOAD_PROGRESS["status"] = "Checking video..."

    # duplicate check
    current_hash = get_file_hash(temp_video_path)

    if LAST_FILE_HASH == current_hash:
        os.remove(temp_video_path)
        return {"message": "⚠️ This video is already processed. Please upload a new one."}

    LAST_FILE_HASH = current_hash

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 30
    UPLOAD_PROGRESS["status"] = "Extracting audio..."

    # convert to audio
    temp_audio_path = temp_video_path.replace(".mp4", ".wav")

    subprocess.run([
    "ffmpeg", "-i", temp_video_path,
    "-vn",                    # 🔥 ignore video completely
    "-acodec", "pcm_s16le",
    "-ar", "16000",
    "-ac", "1",
    temp_audio_path
])

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 50
    UPLOAD_PROGRESS["status"] = "Transcribing audio..."

    # transcribe
    transcript, language = transcribe_audio(temp_audio_path)

    if transcript is None:
        os.remove(temp_video_path)
        os.remove(temp_audio_path)

        return {
            "message": "❌ This app supports only English, Hindi, and Assamese videos."
        }

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 70
    UPLOAD_PROGRESS["status"] = "Saving transcript..."

    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(transcript)

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 80
    UPLOAD_PROGRESS["status"] = "Creating chunks..."

    # chunk
    GLOBAL_CHUNKS = create_chunks(transcript)

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 90
    UPLOAD_PROGRESS["status"] = "Generating embeddings..."

    # embeddings
    create_embeddings_from_chunks(GLOBAL_CHUNKS)

    # 🔄 Done
    UPLOAD_PROGRESS["progress"] = 100
    UPLOAD_PROGRESS["status"] = "Done"

    # cleanup
    os.remove(temp_video_path)
    os.remove(temp_audio_path)

    return {"message": "✅ Video processed successfully"}

#UPLOAD THROUGH LINKS
@app.post("/upload-youtube/")
async def upload_youtube(url: str):

    global GLOBAL_CHUNKS, LAST_FILE_HASH, UPLOAD_PROGRESS, CHAT_HISTORY, LAST_CONTEXT

    LAST_CONTEXT = ""
    CHAT_HISTORY = []

    UPLOAD_PROGRESS["progress"] = 5
    UPLOAD_PROGRESS["status"] = "Downloading YouTube audio..."

    try:
        audio_path = download_youtube_audio(url)   # 🔥 returns .wav
    except Exception as e:
        return {"message": f"❌ Failed to download video: {str(e)}"}

    # hash check
    UPLOAD_PROGRESS["progress"] = 20
    UPLOAD_PROGRESS["status"] = "Checking content..."

    current_hash = get_file_hash(audio_path)

    if LAST_FILE_HASH == current_hash:
        os.remove(audio_path)
        return {"message": "⚠️ This video is already processed."}

    LAST_FILE_HASH = current_hash

    # 🔥 NO FFMPEG HERE
    UPLOAD_PROGRESS["progress"] = 30
    UPLOAD_PROGRESS["status"] = "Preparing audio..."

    # transcription
    UPLOAD_PROGRESS["progress"] = 50
    UPLOAD_PROGRESS["status"] = "Transcribing..."

    transcript, language = transcribe_audio(audio_path)

    if transcript is None:
        os.remove(audio_path)
        return {"message": "❌ Unsupported language."}

    # save transcript
    UPLOAD_PROGRESS["progress"] = 70
    UPLOAD_PROGRESS["status"] = "Saving transcript..."

    with open(TRANSCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(transcript)

    # chunking
    UPLOAD_PROGRESS["progress"] = 80
    UPLOAD_PROGRESS["status"] = "Chunking..."

    GLOBAL_CHUNKS = create_chunks(transcript)

    # embeddings
    UPLOAD_PROGRESS["progress"] = 90
    UPLOAD_PROGRESS["status"] = "Creating embeddings..."

    create_embeddings_from_chunks(GLOBAL_CHUNKS)

    UPLOAD_PROGRESS["progress"] = 100
    UPLOAD_PROGRESS["status"] = "Done"

    # cleanup
    os.remove(audio_path)

    return {"message": "✅ YouTube video processed successfully"}

#SPLIT QUESTIONS
def split_questions(query):
    parts = re.split(r'\?|\.\s+', query)
    return [q.strip() for q in parts if q.strip()]

# 💬 Chat endpoint
@app.post("/chat/")
async def chat(query: str):

    global CHAT_HISTORY, LAST_CONTEXT  # ✅ UPDATED

    if is_video_question(query) and not GLOBAL_CHUNKS:
        return {"answer": "⚠️ Please upload a video first."}

    # ✅ STEP 2 — Build history (UNCHANGED)
    history_text = ""
    for q_hist, a_hist in CHAT_HISTORY[-3:]:
        history_text += f"Student: {q_hist}\nTeacher: {a_hist}\n"

    # 🔥 NEW — split questions
    questions = split_questions(query)
    answers = []

    current_topic = ""  # 🔥 track topic

    for q in questions:

        original_q = q  # keep original

        # 🔥 STEP 1 — detect follow-up
        is_follow_up = is_follow_up_query(original_q)

        # 🔥 STEP 2 — update topic (only for non-follow-up)
        if not is_follow_up:
            if "fiber" in q.lower():
                current_topic = "fiber internet"
            elif "cable" in q.lower():
                current_topic = "cable internet"
            elif len(q.split()) > 4:
                # 🔥 FIXED — extract only topic words
                current_topic = " ".join(q.split()[-2:])

        elif not current_topic and CHAT_HISTORY:
            current_topic = CHAT_HISTORY[-1][0]

        # 🔥 STEP 3 — resolve pronouns
        if is_follow_up and current_topic:
            q = resolve_pronouns(q, current_topic)

            # 🔥 IMPORTANT FIX — now treat as normal query
            is_follow_up = False

        if is_video_question(q):
    
          # 🔥 ALWAYS retrieve (no break in old logic)
            results = ask_question(q, GLOBAL_CHUNKS, chat_history=CHAT_HISTORY)
            new_context = "\n\n".join(results[:3])

          # 🔥 HYBRID CONTEXT (key change)
            if is_follow_up and LAST_CONTEXT:
               context = LAST_CONTEXT + "\n\n" + new_context
            else:
               context = new_context
          
          # 🔥 SAFETY LIMIT
            context = context[-3000:]
          
          # 🔥 update memory (same as before)
            LAST_CONTEXT = context

            # 🟢 MODE 1 — RAG
            if not is_follow_up:
                results = ask_question(q, GLOBAL_CHUNKS, chat_history=CHAT_HISTORY)
                new_context = "\n\n".join(results[:3])

                context = new_context
                LAST_CONTEXT = context

            # 🔵 MODE 2 — Follow-up (fallback)
            else:
                context = LAST_CONTEXT

            last_topic = CHAT_HISTORY[-1][0] if CHAT_HISTORY else ""
            full_context = f"""
Previous Topic:
{last_topic}

Conversation:
{history_text}

Context:
{context}
"""

            ans = generate_answer(full_context, q, True)

        else:
            # ✅ Non-video question
            full_context = history_text
            ans = generate_answer(full_context, q, False)

        answers.append(ans)

    # 🔥 combine answers
    final_answer = "\n\n".join(answers)

    # ✅ Save conversation
    CHAT_HISTORY.append((query, final_answer))

    if len(CHAT_HISTORY) > 10:
        CHAT_HISTORY.pop(0)

    return {"answer": final_answer}

# ⚡ Summary
@app.get("/summary/")
async def summary():

    global GLOBAL_CHUNKS

    if not GLOBAL_CHUNKS:
        return {"summary": "⚠️ Please upload a video first."}

    if not os.path.exists(TRANSCRIPT_PATH):
        return {"summary": "⚠️ Transcript missing. Please re-upload the video."}

    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        return {"summary": "⚠️ Transcript is empty. Please upload video again."}

    prompt = f"""
Summarize this video in a short, engaging way.

Make it slightly unique and varied each time.

Text:
{text}
"""

    summary = generate_answer("", prompt, False)

    return {"summary": summary}


# 📝 Quiz generator
@app.get("/quiz/")
async def quiz():

    global GLOBAL_CHUNKS

    if not GLOBAL_CHUNKS:
        return {"quiz": "⚠️ Please upload a video first."}

    if not os.path.exists(TRANSCRIPT_PATH):
        return {"quiz": "⚠️ Transcript missing. Please re-upload the video."}

    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    # 🔥 LIMIT INPUT SIZE (prevents confusion for long videos)
    if len(text) > 3000:
        text = text[:3000]

    if not text.strip():
        return {"quiz": "⚠️ Transcript is empty. Please upload video again."}

    prompt = f"""
You are an AI teacher.

Generate 5 quiz questions.

Make the questions slightly different each time while staying relevant.

STRICT RULES:
- Exactly 5 questions
- No answers
- No explanation

Text:
{text}
"""

    questions = generate_answer("", prompt, False)

    # 🛑 Safety guard
    if "summary" in questions.lower() or len(questions.strip()) < 20:
        questions = "⚠️ Quiz generation failed. Try again or upload clearer content."

    return {"quiz": questions}