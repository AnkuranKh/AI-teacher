import os
import pickle

def chunk_text(text, chunk_size=500, overlap=100):
    words = text.split()  # 🔥 CHANGE: word-based instead of sentence split

    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk.strip())

    return chunks

def create_chunks(text):
    return chunk_text(text)


if __name__ == "__main__":
    input_path = "data/transcripts/transcript.txt"
    output_path = "data/index/chunks.pkl"

    # create folder if not exists
    os.makedirs("data/index", exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)

    print(f"✅ Created {len(chunks)} chunks")

    # save chunks
    with open(output_path, "wb") as f:
        pickle.dump(chunks, f)

    print(f"💾 Saved chunks to {output_path}")