import os
import pickle

def chunk_text(text, chunk_size=500, overlap=100):
    sentences = text.split(". ")

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # add sentence if within limit
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())

            # overlap handling (optional but useful)
            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())

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