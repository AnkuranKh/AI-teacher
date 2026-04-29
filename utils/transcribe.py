from faster_whisper import WhisperModel
import os

print("🚀 Loading Whisper model once...")

model = WhisperModel(
    "small",                      # 🔥 faster + better than base
    device="cpu",
    compute_type="int8",
    cpu_threads=os.cpu_count()   # 🔥 use all CPU cores
)

def transcribe_audio(audio_path):
    print("🎧 Transcribing...")

    # ✅ Faster decoding settings
    segments, info = model.transcribe(
        audio_path,
        beam_size=1,       # 🔥 major speed boost
        best_of=1,         # 🔥 avoid extra computation
        temperature=0.0    # 🔥 stable + faster
    )

    detected_language = info.language
    print(f"🌐 Detected language: {detected_language}")

    # ✅ Allow only these languages and Normalize Assamese detection
    if detected_language == "bn":
        print("⚠️ Detected Bengali — treating as Assamese")

    ALLOWED_LANGUAGES = ["en", "hi", "as", "bn"]

    if detected_language not in ALLOWED_LANGUAGES:
        return None, detected_language

    full_text = ""

    for segment in segments:
        print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
        full_text += segment.text + " "

    return full_text, detected_language


if __name__ == "__main__":
    input_path = "data/videos/output.wav"
    output_path = "data/transcripts/transcript.txt"

    # ensure folder exists
    os.makedirs("data/transcripts", exist_ok=True)

    transcript, _ = transcribe_audio(input_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print(f"\n✅ Transcription saved to {output_path}")