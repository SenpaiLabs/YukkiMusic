# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import asyncio
import random
import re
from pathlib import Path

import aiohttp
import yt_dlp
from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils

_YT_REGEX = re.compile(
    r"(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
)
_YT_IREGEX = re.compile(
    r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
    r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
    r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
)


class _NullLogger:
    debug = warning = error = staticmethod(lambda *_: None)


class YouTube:
    def __init__(self):
        self.cookies: list[str] = []
        self.checked: bool = False
        self.cookie_dir: Path = Path("anony/cookies")
        self.warned: bool = False

    def get_cookies(self) -> str | None:
        if not self.checked:
            self.cookies = [str(p) for p in self.cookie_dir.glob("*.txt")]
            self.checked = True
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        self.cookie_dir.mkdir(parents=True, exist_ok=True)
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.rstrip("/").split("/")[-1]
                link = f"https://batbin.me/raw/{name}"
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    (self.cookie_dir / f"{name}.txt").write_bytes(await resp.read())
        self.checked = False
        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        return bool(_YT_REGEX.match(url))

    def invalid(self, url: str) -> bool:
        return bool(_YT_IREGEX.match(url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            results = await VideosSearch(query, limit=1, with_live=False).next()
        except Exception:
            return None
        if results and results.get("result"):
            data = results["result"][0]
            thumbnails = data.get("thumbnails") or [{}]
            return Track(
                id=data.get("id"),
                channel_name=(data.get("channel") or {}).get("name", ""),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=(data.get("title") or "")[:25],
                thumbnail=thumbnails[-1].get("url", "").split("?")[0],
                url=data.get("link"),
                view_count=(data.get("viewCount") or {}).get("short", ""),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        try:
            plist = await Playlist.get(url)
            return [
                Track(
                    id=d.get("id"),
                    channel_name=(d.get("channel") or {}).get("name", ""),
                    duration=d.get("duration"),
                    duration_sec=utils.to_seconds(d.get("duration")),
                    title=(d.get("title") or "")[:25],
                    thumbnail=(d.get("thumbnails") or [{}])[-1].get("url", "").split("?")[0],
                    url=(d.get("link") or "").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                for d in plist.get("videos", [])[:limit]
            ]
        except Exception:
            return []

    async def download(self, video_id: str, video: bool = False) -> str | None:
        filename = f"downloads/{video_id}.{'mp4' if video else 'webm'}"
        if Path(filename).exists():
            return filename

        ydl_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "logger": _NullLogger(),
            "nocheckcertificate": True,
            "cookiefile": self.get_cookies(),
            "remote_components": ["ejs:github"],
            "format": (
                "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio)"
                if video
                else "bestaudio[ext=webm][acodec=opus]"
            ),
            **({"merge_output_format": "mp4"} if video else {}),
        }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
                except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError):
                    return None
                except Exception as ex:
                    logger.warning("Download failed: %s", ex)
                    return None
            return filename

        return await asyncio.to_thread(_download)
