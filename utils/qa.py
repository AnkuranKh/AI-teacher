import faiss
import numpy as np
from sentence_transformers import SentenceTransformer,CrossEncoder 
import requests
import os   # ✅ ADDED

# EXIT WORDS
EXIT_WORDS = ["exit", "bye", "goodbye", "quit", "see you", "stop"]

# Load embedding model
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Re-ranking model
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

#  Expand query for better retrieval
def expand_query(query):
    return query + " explanation definition concept details"

# Paths
INDEX_PATH = "data/index/index.faiss"
CHUNKS_PATH = "data/index/chunks.pkl"

# ❌ REMOVED THIS LINE (was causing crash)
# index = faiss.read_index(INDEX_PATH)

#  Re-ranking function
def rerank_chunks(query, chunks, top_n=5):
    if not chunks:
        return []

    try:
        # Pair query with each chunk
        pairs = [(query, chunk) for chunk in chunks]

        # Get relevance scores
        scores = reranker.predict(pairs)

        # Combine chunks with scores
        scored_chunks = list(zip(chunks, scores))

        # Sort by score (highest first)
        ranked = sorted(scored_chunks, key=lambda x: x[1], reverse=True)

        # Return top N best chunks
        return [chunk for chunk, score in ranked[:top_n]]

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

    # 🔥 STRONG QUERY BUILD (REAL FIX)
    if chat_history:
        last_topic = extract_last_topic(chat_history)

        # ALWAYS combine (not just for "it/this")
        query = f"{last_topic}. {query}"

    # 🔥 stronger expansion
    expanded_query = query + " explanation working speed reason advantage difference bandwidth latency"

    query_vector = model.encode([expanded_query], normalize_embeddings=True)

    distances, indices = index.search(np.array(query_vector), k)

    results = [chunks[i] for i in indices[0] if i < len(chunks)]

    if not results:
       results = [chunks[0], chunks[len(chunks)//2], chunks[-1]]

    # 🔥 NEW: Apply re-ranking
    reranked_results = rerank_chunks(query, results, top_n=5)

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


#follow-up detector
def is_follow_up_query(query):
    query = query.lower().strip()

    # 🔥 Strong signals (pronouns → high confidence follow-up)
    pronoun_signals = ["it", "this", "that", "they", "them", "he", "she"]

    # 🔥 Weak signals (only if query is short)
    weak_signals = ["why", "how", "what about", "and", "then"]

    # ✅ Rule 1 — Pronoun present → follow-up
    if any(word in query for word in pronoun_signals):
        return True

    # ✅ Rule 2 — Short question + weak signal → follow-up
    if len(query.split()) <= 6 and any(word in query for word in weak_signals):
        return True

    return False



# 🔁 dual-mode answer
def generate_answer(context, question, use_context=True):

    if use_context:
        prompt = f"""
You are a strict AI teacher helping a student understand a video.

Follow these rules strictly:

1. Check if the answer exists in the provided context.

2. If the answer IS present in the context:
   - Answer ONLY using the context
   - Do NOT use any outside knowledge

3. If the answer is NOT present in the context:
   - Say EXACTLY: "Not found in the video."
   - Then give a general explanation using your own knowledge

4. Do NOT mix both modes.
5. Be clear and helpful.

Context:
{context}

Question:
{question}

Answer:
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
        "stream": False,
        "options": {
            "temperature": 0.7,   # 🔥 controls randomness
            "top_p": 0.9
        }
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