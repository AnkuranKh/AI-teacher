import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import requests
import os   # ✅ ADDED

# EXIT WORDS
EXIT_WORDS = ["exit", "bye", "goodbye", "quit", "see you", "stop"]

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# 🔥 NEW: Expand query for better retrieval
def expand_query(query):
    return query + " explanation definition concept details"

# Paths
INDEX_PATH = "data/index/index.faiss"
CHUNKS_PATH = "data/index/chunks.pkl"

# ❌ REMOVE THIS LINE (was causing crash)
# index = faiss.read_index(INDEX_PATH)


def ask_question(query, chunks, k=10):
    # 🛑 Check if index exists
    if not os.path.exists(INDEX_PATH):
        return ["⚠️ No index found. Please upload a video first."]

    # ✅ Load index ONLY when needed
    index = faiss.read_index(INDEX_PATH)

    # Convert query to embedding
    expanded_query = expand_query(query)
    query_vector = model.encode([expanded_query], normalize_embeddings=True)

    # Search similar chunks
    distances, indices = index.search(np.array(query_vector), k)

    # ✅ Safe indexing (prevents crash)
    results = [chunks[i] for i in indices[0] if i < len(chunks)]

    # 🔥 NEW: fallback if no good results
    if not results:
       results = [chunks[0], chunks[len(chunks)//2], chunks[-1]]

    return results


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


# 🔁 dual-mode answer
def generate_answer(context, question, use_context=True):

    if use_context:
        prompt = f"""
You are an expert teacher helping a student understand a lesson.

Follow these rules:
1. Use the provided context if it contains relevant information.
2. If the context is not sufficient, you can use your own knowledge.
3. Prefer context over general knowledge when both are available.
4. Explain clearly and simply.
5. If the topic is related to the video, try to connect your answer with the video.

Context:
{context}

Question:
{question}

Answer (in clear teaching style):
"""
    else:
        prompt = f"""
You are a friendly AI assistant.

Answer the question naturally and conversationally.

Question:
{question}

Answer:
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "gemma:2b",
            "prompt": prompt,
            "stream": False
        },
        timeout=60
    )

    return response.json().get("response", "No response from model.")


if __name__ == "__main__":
    print("🤖 Ask questions (type 'exit' to quit)")

    while True:
        query = input("\n❓ Your question: ")

        query_lower = query.lower()

        if any(word in query_lower for word in EXIT_WORDS):
            print("\n👋 Got it! See you later. Feel free to come back anytime!\n")
            break

        if is_video_question(query):
            print("⚠️ This mode requires chunks (not available in CLI version).")

        else:
            answer = generate_answer("", query, use_context=False)

        print("\n🧠 AI Answer:\n")
        print(answer)