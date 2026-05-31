import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "Veduta/0.1 (+https://github.com/veduta/veduta)"


def choose_download_state(final_path: Path) -> str:
    if final_path.exists() and final_path.stat().st_size > 0:
        return "skip"
    return "download"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        text=True,
        capture_output=True,
        check=True,
    )
    width = 0
    height = 0
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("pixelWidth:"):
            width = int(stripped.split(":", 1)[1].strip())
        if stripped.startswith("pixelHeight:"):
            height = int(stripped.split(":", 1)[1].strip())
    if width <= 0 or height <= 0:
        raise ValueError(f"Could not read image dimensions from {path}")
    return width, height


def download_url(url: str, destination: Path, timeout: float = 60.0) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ValueError(f"Expected image content from {url}, got {content_type}")
        with partial.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    partial.replace(destination)


def download_first_working(candidates: list[str], destination: Path, delay_seconds: float) -> dict[str, object]:
    if choose_download_state(destination) == "skip":
        try:
            width, height = image_dimensions(destination)
            return {
                "status": "skipped",
                "url": None,
                "width": width,
                "height": height,
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        except (OSError, ValueError, subprocess.CalledProcessError):
            if destination.exists():
                destination.unlink()

    errors: list[str] = []
    for url in candidates:
        try:
            download_url(url, destination)
            width, height = image_dimensions(destination)
            return {
                "status": "downloaded",
                "url": url,
                "width": width,
                "height": height,
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        except (urllib.error.URLError, TimeoutError, ValueError, subprocess.CalledProcessError) as error:
            errors.append(f"{url}: {error}")
            if destination.exists():
                destination.unlink()
            partial = destination.with_suffix(destination.suffix + ".partial")
            if partial.exists():
                partial.unlink()
            time.sleep(delay_seconds)

    raise RuntimeError(json.dumps({"destination": str(destination), "errors": errors}, ensure_ascii=False))
