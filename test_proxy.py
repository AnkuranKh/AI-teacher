import requests

from http.cookiejar import (
    MozillaCookieJar
)

from youtube_transcript_api import (
    YouTubeTranscriptApi
)

video_id = "7o0NkKez1AY"

# YOUR RESIDENTIAL PROXY
proxy_url = (
    "http://USERNAME:PASSWORD@HOST:PORT"
)

try:

    print(
        "🔄 Testing residential proxy..."
    )

    session = (
        requests.Session()
    )

    # Make request look like Chrome
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; "
            "Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/125.0.0.0 "
            "Safari/537.36"
        ),
        "Accept-Language":
            "en-US,en;q=0.9",
        "Referer":
            "https://www.youtube.com/"
    })

    # Add residential proxy
    session.proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    # Load cookies.txt
    cookie_jar = (
        MozillaCookieJar()
    )

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

    # Check proxy IP
    response = session.get(
        "https://httpbin.org/ip",
        timeout=15
    )

    print(
        "🌍 Proxy IP:"
    )

    print(
        response.text
    )

    # Fetch transcript
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