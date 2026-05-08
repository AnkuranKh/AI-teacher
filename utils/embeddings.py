import os
import pickle
import faiss
import numpy as np
import torch

from sentence_transformers import SentenceTransformer
from fastapi import FastAPI

# ✅ Reduce memory/thread pressure
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_num_threads(1)

# ✅ Lazy-loaded embedding model
embedding_model = None

# Paths
CHUNKS_PATH = "data/index/chunks.pkl"
INDEX_PATH = "data/index/index.faiss"

app = FastAPI()


# ✅ Lazy loading function
def get_embedding_model():
    global embedding_model

    if embedding_model is None:
        print("🚀 Loading embedding model...")

        embedding_model = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2'
        )

    return embedding_model


def create_embeddings():
    # 🧹 DELETE OLD INDEX FIRST
    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)

    # Load chunks
    with open(CHUNKS_PATH, "rb") as f:
        chunks = pickle.load(f)

    print(f"📄 Loaded {len(chunks)} chunks")

    # ✅ Lazy load model only when needed
    model = get_embedding_model()

    # Convert text → embeddings
    embeddings = model.encode(
        chunks,
        normalize_embeddings=True
    )

    print("🧠 Embeddings created")

    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)

    index.add(np.array(embeddings))

    # Save index
    faiss.write_index(index, INDEX_PATH)

    print(f"💾 Index saved to {INDEX_PATH}")


# ✅ NEW FUNCTION (in-memory)
def create_embeddings_from_chunks(chunks):
    # 🧹 DELETE OLD INDEX FIRST
    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)

    # ✅ Lazy load model only when needed
    model = get_embedding_model()

    embeddings = model.encode(
        chunks,
        normalize_embeddings=True
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(np.array(embeddings))

    faiss.write_index(index, INDEX_PATH)

    return {
        "message": "Embeddings created",
        "num_chunks": len(chunks)
    }


# ✅ FASTAPI ENDPOINT
@app.post("/create-embeddings")
def create_embeddings_api(data: dict):
    chunks = data.get("chunks", [])

    if not chunks:
        return {"error": "No chunks provided"}

    return create_embeddings_from_chunks(chunks)


if __name__ == "__main__":
    os.makedirs("data/index", exist_ok=True)

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)