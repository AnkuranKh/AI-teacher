from fastapi import FastAPI
from pydantic import BaseModel

import requests

from http.cookiejar import (
    MozillaCookieJar
)

from youtube_transcript_api import (
    YouTubeTranscriptApi
)

app = FastAPI()


class VideoRequest(
    BaseModel
):
    video_id: str


@app.post(
    "/get-transcript"
)
async def get_transcript(
    data: VideoRequest
):

    try:

        session = (
            requests.Session()
        )

        # Browser headers
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

        # Load cookies
        cookie_jar = (
            MozillaCookieJar()
        )

        cookie_jar.load(
            "cookies.txt",
            ignore_discard=True,
            ignore_expires=True
        )

        for cookie in cookie_jar:

            session.cookies.set(
                cookie.name,
                cookie.value,
                domain=cookie.domain
            )

        # Transcript API
        ytt_api = (
            YouTubeTranscriptApi(
                http_client=session
            )
        )

        transcript_data = (
    ytt_api.fetch(
        data.video_id,

        languages=[
            "en",
            "hi",
            "en-IN",
            "hi-IN",
            "as",
            "bn"
        ]
    )
)

        transcript = (
            " ".join([
                item.text
                for item
                in transcript_data
            ])
        )

        return {
            "success":
            True,

            "transcript":
            transcript
        }

    except Exception as e:

        return {
            "success":
            False,

            "error":
            str(e)
        }