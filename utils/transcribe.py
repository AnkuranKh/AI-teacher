from faster_whisper import WhisperModel
import os

def transcribe_audio(audio_path):
    print("⏳ Loading model...")
    model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

    print("🎧 Transcribing...")
    segments, _ = model.transcribe(audio_path, language="en")

    full_text = ""

    for segment in segments:
        print(f"[{segment.start:.2f}s - {segment.end:.2f}s] {segment.text}")
        full_text += segment.text + " "

    return full_text


if __name__ == "__main__":
    input_path = "data/videos/output.wav"
    output_path = "data/transcripts/transcript.txt"

    # ensure folder exists
    os.makedirs("data/transcripts", exist_ok=True)

    transcript = transcribe_audio(input_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print(f"\n✅ Transcription saved to {output_path}")