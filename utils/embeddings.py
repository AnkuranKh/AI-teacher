import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Paths
CHUNKS_PATH = "data/index/chunks.pkl"
INDEX_PATH = "data/index/index.faiss"

app = FastAPI()


def create_embeddings():
    # 🧹 DELETE OLD INDEX FIRST
    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)

    # Load chunks
    with open(CHUNKS_PATH, "rb") as f:
        chunks = pickle.load(f)

    print(f"📄 Loaded {len(chunks)} chunks")

    # Convert text → embeddings
    embeddings = model.encode(chunks)

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

    embeddings = model.encode(chunks)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))

    faiss.write_index(index, INDEX_PATH)

    return {"message": "Embeddings created", "num_chunks": len(chunks)}


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