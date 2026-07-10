from __future__ import annotations

import hashlib
import threading
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from gi.repository import GLib


class ImageCacheService:
    """Small async image cache for marketplace listing thumbnails."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._active_urls: set[str] = set()

    def fetch_async(self, url: str | None, callback) -> None:
        if not url:
            GLib.idle_add(callback, None)
            return

        cached_path = self._path_for_url(url)

        if cached_path.exists():
            GLib.idle_add(callback, cached_path)
            return

        if url in self._active_urls:
            return

        self._active_urls.add(url)

        thread = threading.Thread(
            target=self._download_worker,
            args=(url, cached_path, callback),
            daemon=True,
        )
        thread.start()

    def _download_worker(self, url: str, cached_path: Path, callback) -> None:
        result: Path | None = None

        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "DealWise/0.4 image-cache",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                },
            )

            with urlopen(request, timeout=15) as response:
                data = response.read(2_500_000)

            if data:
                cached_path.write_bytes(data)
                result = cached_path
        except (URLError, TimeoutError, OSError):
            result = None
        finally:
            self._active_urls.discard(url)
            GLib.idle_add(callback, result)

    def _path_for_url(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.img"
