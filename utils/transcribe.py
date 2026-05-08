from openai import OpenAI
from dotenv import load_dotenv
import os

# ✅ load env variables
load_dotenv()

# ✅ Groq client
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


def transcribe_audio(audio_path):

    print("🎧 Transcribing with Groq Whisper API...")

    try:

        with open(audio_path, "rb") as audio_file:

            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo"
            )

        full_text = transcript.text

        print("✅ Transcript generation completed")

        # ✅ preserve old return structure
        detected_language = "en"

        return full_text, detected_language

    except Exception as e:

        print("❌ Transcription failed:", e)

        return None, "unknown"


if __name__ == "__main__":

    input_path = "data/videos/output.mp3"

    transcript, _ = transcribe_audio(input_path)

    if transcript:

        os.makedirs("data/transcripts", exist_ok=True)

        output_path = "data/transcripts/transcript.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcript)

        print(f"\n✅ Transcription saved to {output_path}")

    else:

        print("❌ Failed to generate transcript")