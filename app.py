from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from youtube_transcript_api import (
    YouTubeTranscriptApi
)
from utils.exam_profiles import EXAM_CONFIGS
import os
import shutil
import subprocess
import tempfile
import hashlib 
import glob
import re
import yt_dlp
import random
import time
import requests
import numpy as np
from http.cookiejar import MozillaCookieJar

# Import your existing logic
from utils.transcribe import transcribe_audio
from utils.chunk import create_chunks
from utils.embeddings import create_embeddings_from_chunks,get_embedding,get_embeddings_batch
from utils.qa import ask_question, generate_answer, is_video_question,is_follow_up_query,generate_summary_openai,generate_quiz_openai,get_quiz_context

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
VIDEO_UPLOADED = False
CURRENT_EXAM = "upsc"
SENTENCE_MAP = []
SENTENCE_EMBEDDINGS = None

HASH_PATH = "data/index/last_video_hash.txt"
#FOLLOW UP CONVERSATIONS
CHAT_HISTORY = []


LAST_CONTEXT = ""

# ✅ NEW: GLOBAL PROGRESS TRACKER
UPLOAD_PROGRESS = {
    "progress": 0,
    "status": "Idle"
}

def seconds_to_timestamp(seconds):
    
    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (
        seconds % 3600
    ) // 60

    secs = seconds % 60

    if hours > 0:

        return (
            f"{hours:02}:"
            f"{minutes:02}:"
            f"{secs:02}"
        )

    return (
        f"{minutes:02}:"
        f"{secs:02}"
    )

def build_sentence_map(
    segments
):

    sentence_map = []

    for segment in segments:

        text = (
            segment.get(
                "text",
                ""
            )
            .strip()
        )

        if not text:
            continue

        start_time = (
            segment.get(
                "start",
                0
            )
        )

        timestamp = (
            seconds_to_timestamp(
                start_time
            )
        )

        sentence_map.append({

            "text":
            text,

            "timestamp":
            timestamp,

            "start_seconds":
            start_time
        })

    return sentence_map

def build_sentence_embeddings():
    
    global SENTENCE_MAP
    global SENTENCE_EMBEDDINGS

    if not SENTENCE_MAP:

        print(
            "⚠️ No sentence map found"
        )

        return

    texts = [
        item["text"]
        for item
        in SENTENCE_MAP
    ]

    print(
        "🚀 Creating sentence embeddings..."
    )

    try:

        embeddings = (
            get_embeddings_batch(
                texts
            )
        )

        SENTENCE_EMBEDDINGS = (
            np.array(
                embeddings
            ).astype("float32")
        )

        print(
            f"✅ Sentence embeddings ready: "
            f"{len(texts)} sentences"
        )

    except Exception as e:

        print(
            "❌ Sentence embedding failed:",
            str(e)
        )

        raise e
    
def get_answer_timestamp(
    answer,
    top_k=3
):

    global SENTENCE_MAP
    global SENTENCE_EMBEDDINGS

    if (
        not SENTENCE_MAP
        or SENTENCE_EMBEDDINGS is None
    ):

        return None

    try:

        # Embed answer
        query_embedding = (
            np.array([
                get_embedding(answer)
            ])
            .astype("float32")
        )

        # Cosine similarity
        similarities = np.dot(
            SENTENCE_EMBEDDINGS,
            query_embedding.T
        ).flatten()

        # Top matches
        best_indices = (
            np.argsort(
                similarities
            )[-top_k:][::-1]
        )

        timestamps = []

        for idx in best_indices:

            timestamps.append(
                SENTENCE_MAP[idx]
            )

        if not timestamps:

            return None

        # Use best timestamp
        best_match = (
            timestamps[0]
        )

        print(
            "\n📍 BEST TIMESTAMP MATCH"
        )

        print(
            best_match
        )

        return (
            best_match[
                "timestamp"
            ]
        )

    except Exception as e:

        print(
            "❌ Timestamp retrieval failed:",
            str(e)
        )

        return None

#DOWNLOAD THROUGH LINKS
def download_youtube_audio(url):
    
    temp_dir = tempfile.gettempdir()

    output_path = os.path.join(
        temp_dir,
        "%(id)s.%(ext)s"
    )

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",

        "outtmpl": output_path,

        "quiet": True,

        "noplaylist": True,

        "geo_bypass": True,

        "extract_flat": False,

        "nocheckcertificate": True,

        "ignoreerrors": False,

        "no_warnings": True,

        "http_headers": {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        },

        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "web"
                ],

                "skip": [
                    "dash",
                    "hls"
                ]
            }
        },

        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "192"
        }]
    }

    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            filename = (
                ydl.prepare_filename(info)
            )

            return (
                os.path.splitext(
                    filename
                )[0]
                + ".wav"
            )

    except Exception as e:

        print(
            "❌ YouTube download failed:",
            e
        )

        raise Exception(
            "YouTube blocked the download. "
            "Try another video or retry."
        )

def get_video_id(url):
    
    if "watch?v=" in url:
        return (
            url.split("v=")[1]
            .split("&")[0]
        )

    elif "youtu.be/" in url:
        return (
            url.split("youtu.be/")[1]
            .split("?")[0]
        )

    return None

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

# 🌐 UI Route 
@app.get("/", response_class=HTMLResponse)
def landing(request: Request):

    return templates.TemplateResponse(
        "landing.html",
        {"request": request}
    )


@app.get("/app", response_class=HTMLResponse)
def app_page(
    request: Request,
    exam: str = "upsc"
):

    global GLOBAL_CHUNKS
    global CHAT_HISTORY
    global VIDEO_UPLOADED
    global CURRENT_EXAM

    CHAT_HISTORY = []

    VIDEO_UPLOADED = False

    # save selected exam globally
    CURRENT_EXAM = exam.lower()

    # restore previous chunks
    if (
        not GLOBAL_CHUNKS
        and os.path.exists(
            TRANSCRIPT_PATH
        )
    ):

        print(
            "♻️ Restoring previous video"
        )

        with open(
            TRANSCRIPT_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            transcript = f.read()

        GLOBAL_CHUNKS = (
            create_chunks(
                transcript
            )
        )

    exam_names = {
        "upsc": "UPSC",
        "apsc": "APSC",
        "ssc": "SSC",
        "banking": "Banking",
        "railway": "Railway",
        "adre": "ADRE"
    }

    selected_exam = exam_names.get(
        CURRENT_EXAM,
        "UPSC"
    )

    print(
        "🎯 Current Exam:",
        CURRENT_EXAM
    )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "selected_exam":
                selected_exam
        }
    )


# 🎥 Upload + Full Pipeline
@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):

    global GLOBAL_CHUNKS, LAST_FILE_HASH, UPLOAD_PROGRESS, CHAT_HISTORY
    global LAST_CONTEXT,VIDEO_UPLOADED

    LAST_CONTEXT = ""
    CHAT_HISTORY = []

    # 🔄 Start progress
    UPLOAD_PROGRESS["progress"] = 5
    UPLOAD_PROGRESS["status"] = "Uploading video..."

    # temp video
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
        shutil.copyfileobj(file.file, temp_video)
        temp_video_path = temp_video.name

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 20
    UPLOAD_PROGRESS["status"] = "Checking video..."

    # hash check
    current_hash = get_file_hash(temp_video_path)

    # check if same video already processed
    if (
        os.path.exists(HASH_PATH)
        and os.path.exists(INDEX_PATH)
        and os.path.exists(TRANSCRIPT_PATH)
    ):

        with open(HASH_PATH, "r") as f:
            saved_hash = f.read().strip()

        # SAME VIDEO
        if current_hash == saved_hash:

            print("⚡ Same video detected")

            # restore chunks if server restarted
            if not GLOBAL_CHUNKS:

                with open(
                    TRANSCRIPT_PATH,
                    "r",
                    encoding="utf-8"
                ) as f:
                    transcript = f.read()

                GLOBAL_CHUNKS = create_chunks(transcript)
            VIDEO_UPLOADED = True
            os.remove(temp_video_path)

            UPLOAD_PROGRESS["progress"] = 100
            UPLOAD_PROGRESS["status"] = "Done"

            return {
                "message":
                "✅ This video is already processed.\n"
                "You can start asking questions,\n"
                "generate summaries or quiz."
            }

    print("🆕 New video detected")

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 30
    UPLOAD_PROGRESS["status"] = "Extracting audio..."

    # convert to audio
    temp_audio_path = temp_video_path.replace(".mp4", ".wav")

    print("🎧 Starting audio extraction...")

    subprocess.run(
        [
            "ffmpeg",
            "-i", temp_video_path,
            "-vn",
            "-acodec", "mp3",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            temp_audio_path
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("✅ Audio extraction completed")

    # 🔄 Update progress
    UPLOAD_PROGRESS["progress"] = 50
    UPLOAD_PROGRESS["status"] = "Transcribing audio..."

    print("🚀 Calling transcribe_audio()")

    # transcribe
    transcript, language = (
    transcribe_audio(
        temp_audio_path
    )
)
    
    print("✅ Transcription returned successfully")

    if transcript is None:
        os.remove(temp_video_path)
        os.remove(temp_audio_path)

        return {
            "message":
            "❌ This app supports only English, Hindi, and Assamese videos."
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

    # save current hash
    with open(HASH_PATH, "w") as f:
        f.write(current_hash)

    # 🔄 Done
    UPLOAD_PROGRESS["progress"] = 100
    UPLOAD_PROGRESS["status"] = "Done"
    VIDEO_UPLOADED = True
    # cleanup
    os.remove(temp_video_path)
    os.remove(temp_audio_path)

    return {"message": "✅ Video processed successfully"}


#UPLOAD THROUGH LINKS
@app.post("/upload-youtube/")
async def upload_youtube(url: str):

    import random
    import time
    import requests

    global GLOBAL_CHUNKS
    global LAST_FILE_HASH
    global UPLOAD_PROGRESS
    global CHAT_HISTORY
    global LAST_CONTEXT
    global VIDEO_UPLOADED
    global SENTENCE_MAP
    global SENTENCE_EMBEDDINGS

    LAST_CONTEXT = ""
    CHAT_HISTORY = []

    UPLOAD_PROGRESS["progress"] = 5
    UPLOAD_PROGRESS["status"] = (
        "Fetching YouTube transcript..."
    )

    try:

        video_id = get_video_id(url)

        print(
            "🎥 Video ID:",
            video_id
        )

        if not video_id:

            return {
                "message":
                "❌ Invalid YouTube URL."
            }

        transcript = None
        segments = []

        # -------------------------
        # RETRY LOGIC
        # -------------------------

        for attempt in range(3):

            try:

                wait_time = (
                    random.uniform(2, 5)
                )

                print(
                    f"⏳ Waiting "
                    f"{wait_time:.2f}s "
                    "before transcript fetch..."
                )

                time.sleep(wait_time)

                transcript_service = os.getenv(
                    "TRANSCRIPT_SERVICE_URL"
                )

                print(
                    "🌐 Transcript service:",
                    transcript_service
                )

                response = requests.post(
                    f"{transcript_service}/get-transcript",
                    json={
                        "video_id":
                        video_id
                    },
                    timeout=60
                )

                result = (
                    response.json()
                )

                if not result.get(
                    "success"
                ):

                    raise Exception(
                        result.get(
                            "error",
                            "Transcript service failed"
                        )
                    )

                # -----------------------------------
                # Transcript text
                # -----------------------------------
                transcript = (
                    result[
                        "transcript"
                    ]
                )

                # -----------------------------------
                # Timestamp segments
                # -----------------------------------
                segments = result.get(
                    "segments",
                    []
                )

                # -----------------------------------
                # Build sentence map
                # -----------------------------------
                SENTENCE_MAP = (
                    build_sentence_map(
                        segments
                    )
                )

                print(
                    "\n🔍 SENTENCE MAP SAMPLE"
                )

                print(
                    SENTENCE_MAP[:5]
                )

                # -----------------------------------
                # NEW:
                # Create sentence embeddings
                # -----------------------------------
                build_sentence_embeddings()

                print(
                    "\n🔍 RECEIVED SEGMENTS"
                )

                print(
                    segments[:3]
                )

                print(
                    f"✅ Transcript fetched "
                    f"(attempt {attempt+1})"
                )

                break

            except Exception as e:

                print(
                    f"❌ Attempt "
                    f"{attempt+1} failed:",
                    str(e)
                )

                if attempt < 2:

                    retry_wait = (
                        random.uniform(3, 8)
                    )

                    print(
                        f"🔄 Retrying in "
                        f"{retry_wait:.2f}s..."
                    )

                    time.sleep(
                        retry_wait
                    )

        if not transcript:

            return {
                "message":
                "❌ Could not retrieve transcript.\n"
                "Transcript service failed."
            }

        print(
            "✅ Transcript fetched successfully"
        )

    except Exception as e:

        print(
            "❌ Transcript fetch failed:",
            str(e)
        )

        return {
            "message":
            "❌ Could not retrieve transcript.\n"
            "Transcript service failed."
        }

    # 🔄 progress
    UPLOAD_PROGRESS["progress"] = 20
    UPLOAD_PROGRESS["status"] = (
        "Checking content..."
    )

    # hash from URL
    current_hash = hashlib.md5(
        url.encode()
    ).hexdigest()

    # same video check
    if (
        os.path.exists(HASH_PATH)
        and os.path.exists(INDEX_PATH)
        and os.path.exists(TRANSCRIPT_PATH)
    ):

        with open(
            HASH_PATH,
            "r"
        ) as f:

            saved_hash = (
                f.read().strip()
            )

        if current_hash == saved_hash:

            print(
                "⚡ Same YouTube video detected"
            )

            # restore chunks
            if not GLOBAL_CHUNKS:

                with open(
                    TRANSCRIPT_PATH,
                    "r",
                    encoding="utf-8"
                ) as f:

                    transcript = (
                        f.read()
                    )

                GLOBAL_CHUNKS = (
                    create_chunks(
                        transcript
                    )
                )

            VIDEO_UPLOADED = True

            UPLOAD_PROGRESS[
                "progress"
            ] = 100

            UPLOAD_PROGRESS[
                "status"
            ] = "Done"

            return {
                "message":
                "✅ This video is already processed.\n"
                "You can start asking questions,\n"
                "generate summaries or quiz."
            }

    print(
        "🆕 New YouTube video detected"
    )

    # save transcript
    UPLOAD_PROGRESS["progress"] = 70
    UPLOAD_PROGRESS["status"] = (
        "Saving transcript..."
    )

    with open(
        TRANSCRIPT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(transcript)

    # chunking
    UPLOAD_PROGRESS["progress"] = 80
    UPLOAD_PROGRESS["status"] = (
        "Chunking..."
    )

    GLOBAL_CHUNKS = (
        create_chunks(
            transcript
        )
    )

    # embeddings
    UPLOAD_PROGRESS["progress"] = 90
    UPLOAD_PROGRESS["status"] = (
        "Creating embeddings..."
    )

    create_embeddings_from_chunks(
        GLOBAL_CHUNKS
    )

    # save hash
    with open(
        HASH_PATH,
        "w"
    ) as f:

        f.write(current_hash)

    UPLOAD_PROGRESS[
        "progress"
    ] = 100

    UPLOAD_PROGRESS[
        "status"
    ] = "Done"

    VIDEO_UPLOADED = True

    return {
        "message":
        "✅ YouTube video processed successfully"
    }
    
#SPLIT QUESTIONS
def split_questions(query):
    parts = re.split(r'\?|\.\s+', query)
    return [q.strip() for q in parts if q.strip()]

# 💬 Chat endpoint
@app.post("/chat/")
async def chat(query: str):

    global CHAT_HISTORY
    global LAST_CONTEXT
    global CURRENT_EXAM

    # ✅ Video required check
    if (
        is_video_question(query)
        and
        not VIDEO_UPLOADED
    ):
        return {
            "answer":
            "⚠️ Please upload a video first."
        }

    # ✅ Build history (UNCHANGED)
    history_text = ""

    for q_hist, a_hist in CHAT_HISTORY[-3:]:

        history_text += (
            f"Student: {q_hist}\n"
            f"Teacher: {a_hist}\n"
        )

    # 🔥 Split questions
    questions = split_questions(query)

    answers = []

    current_topic = ""

    for q in questions:

        original_q = q

        # 🔥 Detect follow-up
        is_follow_up = (
            is_follow_up_query(
                original_q
            )
        )

        # 🔥 Update topic
        if not is_follow_up:

            if "fiber" in q.lower():
                current_topic = (
                    "fiber internet"
                )

            elif "cable" in q.lower():
                current_topic = (
                    "cable internet"
                )

            elif len(q.split()) > 3:
                current_topic = q

        elif (
            not current_topic
            and CHAT_HISTORY
        ):

            last_q = (
                CHAT_HISTORY[-1][0]
                .lower()
            )

            if "slr" in last_q:
                current_topic = "SLR"

            elif "dslr" in last_q:
                current_topic = "DSLR"

            elif "fiber" in last_q:
                current_topic = (
                    "fiber internet"
                )

            elif "cable" in last_q:
                current_topic = (
                    "cable internet"
                )

        # 🔥 Resolve pronouns
        if (
            is_follow_up
            and current_topic
        ):

            q = resolve_pronouns(
                q,
                current_topic
            )

            # IMPORTANT FIX
            is_follow_up = False

        # =================================
        # VIDEO QUESTION MODE (RAG)
        # =================================

        if (
            GLOBAL_CHUNKS
            and VIDEO_UPLOADED
        ):

            # Always retrieve
            results = ask_question(
                q,
                GLOBAL_CHUNKS,
                chat_history=CHAT_HISTORY
            )

            print(
                "\n================ DEBUG ================="
            )

            print(
                "QUERY:",
                q
            )

            for i, r in enumerate(
                results[:5]
            ):

                print(
                    f"\nCHUNK {i+1}:"
                )

                print(
                    r[:200]
                )

            print(
                "========================================\n"
            )

            new_context = (
                "\n\n".join(
                    results[:5]
                )
            )

            # Hybrid context
            if (
                is_follow_up
                and LAST_CONTEXT
            ):

                context = (
                    LAST_CONTEXT
                    + "\n\n"
                    + new_context
                )

            else:

                context = (
                    new_context
                )

            # Safety limit
            context = (
                context[-1800:]
            )

            LAST_CONTEXT = context

            # MODE 1 — RAG
            if not is_follow_up:

                results = ask_question(
                    q,
                    GLOBAL_CHUNKS,
                    chat_history=CHAT_HISTORY
                )

                new_context = (
                    "\n\n".join(
                        results[:5]
                    )
                )

                context = (
                    new_context
                )

                LAST_CONTEXT = (
                    context
                )

            # MODE 2 — Follow-up
            else:

                context = (
                    LAST_CONTEXT
                )

            last_topic = (
                CHAT_HISTORY[-1][0]
                if CHAT_HISTORY
                else ""
            )

            full_context = f"""
Previous Topic:
{last_topic}

Conversation:
{history_text}

Context:
{context}
"""

            # =================================
            # ANSWER GENERATION
            # =================================

            ans = generate_answer(
                full_context,
                q,
                exam=CURRENT_EXAM,
                use_context=True
            )

            # =================================
            # NEW:
            # Semantic timestamp grounding
            # =================================

            try:

                timestamp = (
                    get_answer_timestamp(
                        ans
                    )
                )

                if timestamp:

                    ans += (
                        f"\n\n📍 Discussed "
                        f"around {timestamp}"
                    )

            except Exception as e:

                print(
                    "❌ Timestamp grounding failed:",
                    str(e)
                )

        # =================================
        # NON-VIDEO QUESTION
        # =================================

        else:

            full_context = (
                history_text
            )

            ans = generate_answer(
                full_context,
                q,
                exam=CURRENT_EXAM,
                use_context=False,
                no_video_uploaded=True
            )

        answers.append(ans)

    # 🔥 Combine answers
    final_answer = (
        "\n\n".join(answers)
    )

    # ✅ Save conversation
    CHAT_HISTORY.append(
        (
            query,
            final_answer
        )
    )

    if len(CHAT_HISTORY) > 10:
        CHAT_HISTORY.pop(0)

    return {
        "answer":
        final_answer
    }

# ⚡ Summary
@app.get("/summary/")
async def summary():

    global GLOBAL_CHUNKS
    global VIDEO_UPLOADED
    global CURRENT_EXAM

    if not VIDEO_UPLOADED:
        return {
            "summary":
            "⚠️ Please upload a video first."
        }

    if not os.path.exists(
        TRANSCRIPT_PATH
    ):
        return {
            "summary":
            "⚠️ Transcript missing. Please re-upload the video."
        }

    with open(
        TRANSCRIPT_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        text = f.read()

    if not text.strip():
        return {
            "summary":
            "⚠️ Transcript is empty. Please upload video again."
        }

    # ✅ Exam config
    exam_config = EXAM_CONFIGS.get(
        CURRENT_EXAM,
        EXAM_CONFIGS["upsc"]
    )

    summary_style = (
        exam_config[
            "summary_style"
        ]
    )

    prompt = f"""
You are an expert teacher helping students revise quickly.

Exam Mode:
{CURRENT_EXAM.upper()}

Instructions:
{summary_style}

Keep the summary:
- Student friendly
- Structured
- Easy to revise
- Exam focused

Transcript:
{text}
"""

    # ✅ OPENAI summary
    summary = (
        generate_summary_openai(
            prompt
        )
    )

    return {
        "summary":
        summary
    }


# 📝 Quiz generator
@app.get("/quiz/")
async def quiz(
    difficulty: str = "medium"
):

    global VIDEO_UPLOADED
    global CURRENT_EXAM
    global GLOBAL_CHUNKS

    if not VIDEO_UPLOADED:

        return {
            "quiz":
            "⚠️ Please upload a video first."
        }

    if not GLOBAL_CHUNKS:

        return {
            "quiz":
            "⚠️ Video content missing."
        }

    # ✅ Exam config
    exam_config = EXAM_CONFIGS.get(
        CURRENT_EXAM,
        EXAM_CONFIGS["upsc"]
    )

    quiz_style = (
        exam_config[
            "quiz_style"
        ]
    )

    # ✅ RAG retrieval
    context = (
        get_quiz_context(
            GLOBAL_CHUNKS
        )
    )

    if not context.strip():

        return {
            "quiz":
            "⚠️ Failed to retrieve video content."
        }

    prompt = f"""
You are an expert government exam teacher.

STRICT RULES:
1. Create quiz ONLY from the provided context.
2. Do NOT use outside knowledge.
3. If information is missing,
   do not invent facts.
4. Questions must test
   important concepts from
   the video.

Exam Mode:
{CURRENT_EXAM.upper()}

Instructions:
{quiz_style}

Difficulty:
{difficulty.upper()}

Generate:
5 questions

Format:

Q1.
Options:
A)
B)
C)
D)

Answer:
Explanation:

Context:
{context}
"""

    questions = (
        generate_quiz_openai(
            prompt
        )
    )

    return {
        "quiz":
        questions
    }