import faiss
import numpy as np
import os
import torch

from openai import OpenAI
from dotenv import load_dotenv
from utils.exam_profiles import EXAM_CONFIGS

# ✅ Reduce memory/thread pressure
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_num_threads(1)

load_dotenv(override=True)

# ✅ Groq client for chat
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# ✅ OpenAI client for embeddings
embedding_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# EXIT WORDS
EXIT_WORDS = [
    "exit",
    "bye",
    "goodbye",
    "quit",
    "see you",
    "stop"
]


# ✅ OpenAI embedding helper
def get_embedding(text):

    try:
        response = embedding_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        return response.data[0].embedding

    except Exception as e:
        print(
            "❌ OpenAI query embedding error:",
            e
        )
        raise e


# Expand query for better retrieval
def expand_query(query):
    return (
        query +
        " explanation definition concept details"
    )


# Paths
INDEX_PATH = "data/index/index.faiss"
CHUNKS_PATH = "data/index/chunks.pkl"


def extract_last_topic(chat_history):

    if not chat_history:
        return ""

    return (
        chat_history[-1][0]
        .replace("?", "")
        .strip()
    )


def ask_question(
    query,
    chunks,
    k=12,   # slightly increased since reranker removed
    chat_history=None
):

    if not os.path.exists(INDEX_PATH):
        return [
            "⚠️ No index found. Please upload a video first."
        ]

    index = faiss.read_index(INDEX_PATH)

    # 🔥 stronger query expansion
    expanded_query = (
        query +
        " explanation working speed "
        "reason advantage difference "
        "bandwidth latency"
    )

    # ✅ OpenAI embeddings
    query_vector = get_embedding(
        expanded_query
    )

    query_vector = np.array(
        [query_vector]
    ).astype("float32")

    distances, indices = index.search(
        query_vector,
        k
    )

    results = [
        chunks[i]
        for i in indices[0]
        if i < len(chunks)
    ]

    # fallback
    if not results and chunks:

        results = [
            chunks[0],
            chunks[len(chunks)//2],
            chunks[-1]
        ]

    # ✅ TEMP: Disable reranker for Render stability
    return results[:3]

def get_quiz_context(
    chunks,
    k=8
):

    if not os.path.exists(
        INDEX_PATH
    ):

        return ""

    try:

        # ✅ Load FAISS index
        index = faiss.read_index(
            INDEX_PATH
        )

        # quiz retrieval query
        quiz_query = (
            "important concepts "
            "key facts "
            "definitions "
            "government exam topics "
            "important current affairs "
            "important explanations"
        )

        query_vector = (
            get_embedding(
                quiz_query
            )
        )

        query_vector = np.array(
            [query_vector]
        ).astype(
            "float32"
        )

        distances, indices = (
            index.search(
                query_vector,
                k
            )
        )

        results = [
            chunks[i]
            for i in indices[0]
            if i < len(chunks)
        ]

        return "\n\n".join(
            results[:6]
        )

    except Exception as e:

        print(
            "❌ Quiz retrieval error:",
            e
        )

        return ""
    
# detect if question is about video
def is_video_question(query):

    keywords = [
        "video",
        "lecture",
        "explain",
        "topic",
        "concept",
        "discussed",
        "according to",
        "in the video"
    ]

    query_lower = query.lower()

    for word in keywords:
        if word in query_lower:
            return True

    return False


# follow-up detector
def is_follow_up_query(query):

    query = query.lower().strip()

    # 🔥 Strong signals
    pronoun_signals = [
        "it",
        "this",
        "that",
        "they",
        "them",
        "he",
        "she"
    ]

    # 🔥 Weak signals
    weak_signals = [
        "why",
        "how",
        "what about",
        "and",
        "then"
    ]

    # ✅ Rule 1
    if any(
        word in query
        for word in pronoun_signals
    ):
        return True

    # ✅ Rule 2
    if (
        len(query.split()) <= 6
        and any(
            word in query
            for word in weak_signals
        )
    ):
        return True

    return False


# 🔁 dual-mode answer
def generate_answer(
    context,
    question,
    exam="upsc",
    use_context=True,
    no_video_uploaded=False
):

    # ✅ Get exam config safely
    exam_config = EXAM_CONFIGS.get(
        exam.lower(),
        EXAM_CONFIGS["upsc"]
    )

    chat_style = (
        exam_config["chat_style"]
    )

    if use_context:

        prompt = f"""
You are a strict AI teacher helping a student understand a video.

Exam Mode:
{exam.upper()}

Answer Style:
{chat_style}

Follow these rules strictly:

1. Check if the answer exists in the provided context.

2. If the answer IS present in the context:
   - Answer ONLY using the context
   - Do NOT use outside knowledge

3. If the answer is NOT present in the context:
   - Say EXACTLY:
     "Not found in the video."
   - Then answer using your own knowledge

4. Follow the exam style strictly.

5. Be conversational and helpful.

Context:
{context}

Question:
{question}

Answer:
"""

    else:

        if no_video_uploaded:

            prompt = f"""
You are a helpful AI assistant.

Exam Mode:
{exam.upper()}

Answer Style:
{chat_style}

IMPORTANT:
- No video is uploaded.
- First briefly mention that
  you are answering using your
  own knowledge because no
  video is uploaded.
- Then answer naturally.
- Follow the exam style strictly.

Question:
{question}

Answer:
"""

        else:

            prompt = f"""
You are a helpful AI assistant.

Exam Mode:
{exam.upper()}

Answer Style:
{chat_style}

IMPORTANT:
- Follow the exam style strictly.

Question:
{question}

Answer:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=500
    )

    return (
        response
        .choices[0]
        .message.content
    )
            

# ✅ OpenAI summary generator
def generate_summary_openai(prompt):

    try:

        response = embedding_client.chat.completions.create(
            model="gpt-4o-mini",

            messages=[
                {
                    "role": "system",
                    "content":
                    (
                        "You are an expert teacher helping "
                        "students revise educational videos "
                        "for government exams."
                    )
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.5,

            max_tokens=1200
        )

        return (
            response
            .choices[0]
            .message.content
        )

    except Exception as e:

        print(
            "❌ OpenAI summary error:",
            e
        )

        return (
            "❌ Failed to generate summary."
        )            
        

def generate_quiz_openai(prompt):
    
    try:

        response = (
            embedding_client
            .chat
            .completions
            .create(

                model="gpt-4o-mini",

                messages=[

                    {
                        "role": "system",
                        "content":
                        (
                            "You are an expert "
                            "government exam "
                            "teacher who creates "
                            "high-quality quizzes."
                        )
                    },

                    {
                        "role": "user",
                        "content":
                            prompt
                    }
                ],

                temperature=0.5,

                max_tokens=1000
            )
        )

        return (
            response
            .choices[0]
            .message.content
        )

    except Exception as e:

        print(
            "❌ OpenAI quiz error:",
            e
        )

        return (
            "❌ Failed to generate quiz."
        )        
        