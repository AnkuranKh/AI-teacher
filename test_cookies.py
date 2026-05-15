import requests

from youtube_transcript_api import (
    YouTubeTranscriptApi
)

video_id = "7o0NkKez1AY"

try:

    print(
        "⏳ Testing cookies..."
    )

    session = (
        requests.Session()
    )

    session.cookies = (
        requests.cookies.RequestsCookieJar()
    )

    # Load cookies file
    with open(
        "cookies.txt",
        "r",
        encoding="utf-8"
    ) as f:

        cookies_text = (
            f.read()
        )

    ytt_api = (
        YouTubeTranscriptApi(
            http_client=session
        )
    )

    transcript = (
        ytt_api.fetch(
            video_id
        )
    )

    print(
        "✅ SUCCESS!"
    )

    print(
        transcript[0].text
    )

except Exception as e:

    print(
        "❌ FAILED"
    )

    print(str(e))