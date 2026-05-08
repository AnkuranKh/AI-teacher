from faster_whisper import WhisperModel
import os
import torch

# ✅ reduce thread pressure
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_num_threads(1)

# ✅ lazy-loaded global model
model = None


def get_whisper_model():
    global model

    if model is None:
        print("🚀 Loading Whisper model once...")

        model = WhisperModel(
            "tiny",                    # 🔥 lightweight for Render
            device="cpu",
            compute_type="int8",
            cpu_threads=1
        )

    return model


def transcribe_audio(audio_path):
    print("🎧 Transcribing...")

    # ✅ lazy load model only when needed
    whisper_model = get_whisper_model()

    print("🚀 Starting Whisper transcription...")

    # ✅ Faster decoding settings
    segments, info = whisper_model.transcribe(
        audio_path,
        beam_size=5,        # 🔥 better accuracy
        best_of=3,          # 🔥 better candidate selection
        temperature=0.2     # 🔥 avoids rigid decoding
    )

    print("✅ Whisper transcription initialized")

    detected_language = info.language
    print(f"🌐 Detected language: {detected_language}")

    # ✅ Allow only these languages and Normalize Assamese detection
    if detected_language == "bn":
        print("⚠️ Detected Bengali — treating as Assamese")

    ALLOWED_LANGUAGES = ["en", "hi", "as", "bn"]

    if detected_language not in ALLOWED_LANGUAGES:
        return None, detected_language

    full_text = ""

    # ✅ Removed heavy per-segment console printing
    for segment in segments:
        full_text += segment.text + " "

    print("✅ Transcript generation completed")

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