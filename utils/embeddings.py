import os
import faiss
import numpy as np

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# ✅ OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
print("OPENAI ENV:", os.getenv("OPENAI_API_KEY"))

# Paths
INDEX_PATH = "data/index/index.faiss"


# ✅ OpenAI embedding helper
def get_embedding(text):

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        return response.data[0].embedding

    except Exception as e:
        print("❌ OpenAI embedding error:", e)
        raise e


# ✅ Create embeddings from chunks (BATCH VERSION)
def create_embeddings_from_chunks(chunks):

    # delete old index
    if os.path.exists(INDEX_PATH):
        os.remove(INDEX_PATH)

    print("🚀 Creating embeddings...")

    try:

        # 🔥 Batch embeddings (much faster + cheaper)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunks
        )

        embeddings = [
            item.embedding
            for item in response.data
        ]

        embeddings = np.array(
            embeddings
        ).astype("float32")

        dimension = embeddings.shape[1]

        index = faiss.IndexFlatL2(dimension)

        index.add(embeddings)

        faiss.write_index(index, INDEX_PATH)

        print("✅ Embeddings created")

        return {
            "message": "Embeddings created",
            "num_chunks": len(chunks)
        }

    except Exception as e:

        print("❌ Embedding creation failed:", e)

        raise e