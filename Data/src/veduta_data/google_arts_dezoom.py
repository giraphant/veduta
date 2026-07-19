import subprocess
from pathlib import Path
from urllib.parse import urlparse

from veduta_data.downloader import image_dimensions, sha256_file


def is_google_arts_asset_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and parsed.netloc == "artsandculture.google.com" and parsed.path.startswith("/asset/")


def dezoomify_google_arts(
    canonical_page: str,
    destination: Path,
    command: str = "dezoomify-rs",
    parallelism: int = 4,
    min_interval: str = "100ms",
    retries: int = 2,
    min_width: int | None = None,
    timeout: float = 600,
) -> dict[str, object]:
    if not is_google_arts_asset_url(canonical_page):
        raise ValueError(f"Unsupported Google Arts asset URL: {canonical_page}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.parent / f".{destination.stem}.dezoomify{destination.suffix}"
    temp_path.unlink(missing_ok=True)

    try:
        subprocess.run(
            [
                command,
                "--largest",
                "--parallelism",
                str(parallelism),
                "--min-interval",
                min_interval,
                "--retries",
                str(retries),
                canonical_page,
                str(temp_path),
            ],
            check=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        if not temp_path.exists():
            raise RuntimeError(f"dezoomify-rs did not create {temp_path}")
        width, height = image_dimensions(temp_path)
        if min_width is not None and width < min_width:
            raise RuntimeError(f"Downloaded image is only {width}px wide; expected at least {min_width}px")
        metadata = {
            "width": width,
            "height": height,
            "bytes": temp_path.stat().st_size,
            "sha256": sha256_file(temp_path),
            "url": canonical_page,
        }
        temp_path.replace(destination)
        return metadata
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
