import requests
from http.cookiejar import MozillaCookieJar
from youtube_transcript_api import (
    YouTubeTranscriptApi
)

video_id = "3XwteXbM34Q"

try:

    print("⏳ Testing cookies...")

    session = requests.Session()

    cookie_jar = MozillaCookieJar()

    cookie_jar.load(
        "cookies.txt",
        ignore_discard=True,
        ignore_expires=True
    )

    print(
        "🍪 Cookies loaded:",
        len(cookie_jar)
    )

    # Inject cookies
    for cookie in cookie_jar:

        session.cookies.set(
            cookie.name,
            cookie.value,
            domain=cookie.domain
        )

    # DEBUG: check if logged in
    response = session.get(
        "https://www.youtube.com"
    )

    print(
        "🌐 Status:",
        response.status_code
    )

    if "Sign in" in response.text:
        print(
            "❌ NOT AUTHENTICATED"
        )
    else:
        print(
            "✅ AUTHENTICATED"
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

    print("✅ SUCCESS!")
    print(transcript[0].text)

except Exception as e:

    print("❌ FAILED")
    print(str(e))