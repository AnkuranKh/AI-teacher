import requests
from youtube_transcript_api import (
    YouTubeTranscriptApi
)

video_id = "7o0NkKez1AY"

proxies_to_test = [

    "http://174.138.165.108:9276",

    "http://174.138.162.197:8254",

    "http://38.127.179.147:37234",
    
    "http://138.68.235.51:80",

    "http://174.138.165.78:9814",
]

for proxy_url in proxies_to_test:

    print("\n" + "=" * 50)
    print(
        f"🔍 Testing: {proxy_url}"
    )

    session = requests.Session()

    session.proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    session.timeout = 10

    try:

        response = session.get(
            "https://httpbin.org/ip",
            timeout=10
        )

        print(
            "🌍 Proxy works:"
        )

        print(response.text)

        ytt_api = (
            YouTubeTranscriptApi(
                http_client=session
            )
        )

        transcript = (
            ytt_api.fetch(video_id)
        )

        print(
            "✅ SUCCESS!"
        )

        print(
            transcript[0].text
        )

        break

    except Exception as e:

        print(
            "❌ FAILED"
        )

        print(str(e))