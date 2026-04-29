from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import shutil
import subprocess
import tempfile
import hashlib  # ✅ NEW

# Import your existing logic
from utils.transcribe import transcribe_audio
from utils.chunk import create_chunks
from utils.embeddings import create_embeddings_from_chunks
from utils.qa import ask_question, generate_answer, is_video_question

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

# ✅ NEW: GLOBAL PROGRESS TRACKER
UPLOAD_PROGRESS = {
    "progress": 0,
    "status": "Idle"
}

# ✅ NEW helper function
def get_file_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


# ✅ NEW: Progress endpoint
@app.get("/progress/")
def get_progress():
    return UPLOAD_PROGRESS

# 🌐 UI Route (UPDATED ONLY THIS PART)
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    global GLOBAL_CHUNKS

    # 🔄 RESET SESSION ON PAGE LOAD
    GLOBAL_CHUNKS = []

    if os.path.exists(TRANSCRIPT_PATH):
        os.remove(TRANSCRIPT_PATH)

    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)

    return templates.TemplateResponse("index.html", {"request": request})


# 🎥 Upload + Full Pipeline
@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):
    global GLOBAL_CHUNKS, LAST_FILE_HASH, UPLOAD_PROGRESS

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
        "-ar", "16000", "-ac", "1",
        "-c:a", "pcm_s16le",
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


# 💬 Chat endpoint
@app.post("/chat/")
async def chat(query: str):

    if is_video_question(query) and not GLOBAL_CHUNKS:
        return {"answer": "⚠️ Please upload a video first."}

    if is_video_question(query):
        results = ask_question(query, GLOBAL_CHUNKS)
        context = "\n\n".join(results[:3])
        answer = generate_answer(context, query, True)
    else:
        answer = generate_answer("", query, False)

    return {"answer": answer}


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