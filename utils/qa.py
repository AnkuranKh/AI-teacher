import faiss
import numpy as np
import requests
import os
import torch

from sentence_transformers import CrossEncoder
from openai import OpenAI
from dotenv import load_dotenv

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
EXIT_WORDS = ["exit", "bye", "goodbye", "quit", "see you", "stop"]

# ✅ Lazy-loaded reranker model
reranker_model = None


# ✅ OpenAI embedding helper
def get_embedding(text):

    try:
        response = embedding_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        return response.data[0].embedding

    except Exception as e:
        print("❌ OpenAI query embedding error:", e)
        raise e


# ✅ Reranker loader
def get_reranker():
    global reranker_model

    if reranker_model is None:
        print("🚀 Loading reranker model...")

        reranker_model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

    return reranker_model


# Expand query for better retrieval
def expand_query(query):
    return query + " explanation definition concept details"


# Paths
INDEX_PATH = "data/index/index.faiss"
CHUNKS_PATH = "data/index/chunks.pkl"


# Re-ranking function
def rerank_chunks(query, chunks, top_n=5):

    if not chunks:
        return []

    try:

        # Pair query with each chunk
        pairs = [(query, chunk) for chunk in chunks]

        # ✅ Lazy load reranker
        reranker = get_reranker()

        # Get relevance scores
        scores = reranker.predict(pairs)

        # Combine chunks with scores
        scored_chunks = list(zip(chunks, scores))

        # Sort by score (highest first)
        ranked = sorted(
            scored_chunks,
            key=lambda x: x[1],
            reverse=True
        )

        # Return top N best chunks
        return [
            chunk for chunk, score in ranked[:top_n]
        ]

    except Exception as e:

        print("Re-ranking failed:", e)

        return chunks[:top_n]  # fallback


def extract_last_topic(chat_history):

    if not chat_history:
        return ""

    return chat_history[-1][0].replace("?", "").strip()


def ask_question(query, chunks, k=20, chat_history=None):

    if not os.path.exists(INDEX_PATH):
        return ["⚠️ No index found. Please upload a video first."]

    index = faiss.read_index(INDEX_PATH)

    # 🔥 stronger expansion
    expanded_query = (
        query +
        " explanation working speed reason advantage difference bandwidth latency"
    )

    # ✅ OpenAI embeddings
    query_vector = get_embedding(expanded_query)

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

    if not results:
        results = [
            chunks[0],
            chunks[len(chunks)//2],
            chunks[-1]
        ]

    # 🔥 Apply re-ranking
    reranked_results = rerank_chunks(
        query,
        results,
        top_n=5
    )

    return reranked_results


# detect if question is about video
def is_video_question(query):

    keywords = [
        "video", "lecture", "explain", "topic",
        "concept", "discussed", "according to", "in the video"
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
        "it", "this", "that",
        "they", "them", "he", "she"
    ]

    # 🔥 Weak signals
    weak_signals = [
        "why", "how",
        "what about", "and", "then"
    ]

    # ✅ Rule 1
    if any(word in query for word in pronoun_signals):
        return True

    # ✅ Rule 2
    if len(query.split()) <= 6 and any(
        word in query for word in weak_signals
    ):
        return True

    return False


# 🔁 dual-mode answer
def generate_answer(
    context,
    question,
    use_context=True,
    no_video_uploaded=False
):

    if use_context:

        prompt = f"""
You are a strict AI teacher helping a student understand a video.

Follow these rules strictly:

1. Check if the answer exists in the provided context.

2. If the answer IS present in the context:
   - Answer ONLY using the context
   - Do NOT use outside knowledge

3. If the answer is NOT present in the context:
   - Say EXACTLY: "Not found in the video."
   - Then answer using your own knowledge

4. Be conversational and helpful.

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

IMPORTANT:
- No video is uploaded.
- First mention briefly that you are answering using your own knowledge and expertise because no video is uploaded.
- Then answer naturally and helpfully.
- Keep it conversational.

Question:
{question}

Answer:
"""

      else:

        prompt = f"""
You are a helpful AI assistant.

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

    return response.choices[0].message.content


if __name__ == "__main__":

    print("🤖 Ask questions (type 'exit' to quit)")

    while True:

        query = input("\n❓ Your question: ")

        query_lower = query.lower()

        if any(word in query_lower for word in EXIT_WORDS):

            print(
                "\n👋 Got it! See you later. Feel free to come back anytime!\n"
            )

            break

        if is_video_question(query):

            print(
                "⚠️ This mode requires chunks (not available in CLI version)."
            )

        else:

            answer = generate_answer(
                "",
                query,
                use_context=False
            )

        print("\n🧠 AI Answer:\n")

        print(answer)