#!/usr/bin/env python3
"""Publish the local Veduta library to an S3-compatible bucket (Garage).

Mirrors the canonical library tree verbatim:

    catalog.json
    collections/*.json
    images/<collection-id>/*.jpg

Uploads are incremental: an object is skipped when the bucket already holds a
copy with a matching size and sha256 (stored as object metadata on first
upload). Images are sent with a long immutable cache lifetime; the JSON
manifests are sent with a short lifetime so refreshed catalogs propagate.

Configuration comes from the environment (load a local .env first; it is
gitignored). Required:

    GARAGE_ENDPOINT      e.g. https://minio.example.com
    GARAGE_ACCESS_KEY
    GARAGE_SECRET_KEY
    GARAGE_BUCKET        e.g. veduta

Optional:

    GARAGE_REGION        default "us-east-1" (Garage ignores it but boto3 wants one)
    MIRROR_PREFIX       key prefix inside the bucket, e.g. "v1/" (default "")
    LIBRARY_ROOT        default ~/Pictures/VedutaLibrary

Requires boto3:  pip install boto3   (or: uv pip install boto3)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

IMAGE_CACHE_CONTROL = "public, max-age=31536000, immutable"
MANIFEST_CACHE_CONTROL = "public, max-age=300"

CONTENT_TYPES = {
    ".json": "application/json",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def default_library_root() -> Path:
    return Path.home() / "Pictures" / "VedutaLibrary"


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (no external dep). Existing env vars win."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(library_root: Path) -> list[Path]:
    """The canonical published set: catalog + collection manifests + images.

    Everything else in the library (audit reports, backups, scan caches) is
    working data and is deliberately left out of the mirror.
    """
    files: list[Path] = []
    catalog = library_root / "catalog.json"
    if catalog.exists():
        files.append(catalog)
    collections = library_root / "collections"
    if collections.is_dir():
        files.extend(sorted(collections.glob("*.json")))
    images = library_root / "images"
    if images.is_dir():
        files.extend(sorted(p for p in images.rglob("*") if p.is_file() and p.suffix.lower() in CONTENT_TYPES))
    return files


def make_client(args: argparse.Namespace):
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        sys.exit("boto3 is required: pip install boto3 (or: uv pip install boto3)")

    endpoint = os.environ.get("GARAGE_ENDPOINT")
    access_key = os.environ.get("GARAGE_ACCESS_KEY")
    secret_key = os.environ.get("GARAGE_SECRET_KEY")
    missing = [
        name
        for name, value in (
            ("GARAGE_ENDPOINT", endpoint),
            ("GARAGE_ACCESS_KEY", access_key),
            ("GARAGE_SECRET_KEY", secret_key),
            ("GARAGE_BUCKET", os.environ.get("GARAGE_BUCKET")),
        )
        if not value
    ]
    if missing:
        sys.exit(f"missing required env vars: {', '.join(missing)}")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=os.environ.get("GARAGE_REGION", "us-east-1"),
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            # boto3 >=1.36 adds CRC32 checksums via aws-chunked trailers by
            # default; Garage (and other S3-compatible stores) reject that with
            # "Chunk format error". Only checksum when the operation requires it.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def remote_matches(client, bucket: str, key: str, size: int, sha: str) -> bool:
    """True when the bucket already holds this exact object (size + sha256)."""
    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except Exception:
        return False
    if head.get("ContentLength") != size:
        return False
    return head.get("Metadata", {}).get("sha256") == sha


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the Veduta library to a Garage/S3 bucket.")
    parser.add_argument("--library-root", default=str(default_library_root()))
    parser.add_argument("--prefix", default=os.environ.get("MIRROR_PREFIX", ""))
    parser.add_argument("--dry-run", action="store_true", help="list what would change, upload nothing")
    parser.add_argument("--env-file", default=".env", help="path to a .env file to load (default: .env)")
    parser.add_argument("--limit", type=int, help="only process the first N files (manifests first) — handy as a smoke test")
    args = parser.parse_args()

    load_dotenv(Path(args.env_file))

    library_root = Path(args.library_root).expanduser()
    if not library_root.is_dir():
        sys.exit(f"library root not found: {library_root}")

    files = collect_files(library_root)
    if not files:
        sys.exit(f"no publishable files found under {library_root}")
    if args.limit is not None:
        files = files[: args.limit]

    prefix = args.prefix.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    client = None if args.dry_run else make_client(args)
    bucket = os.environ.get("GARAGE_BUCKET", "")
    if args.dry_run and not bucket:
        bucket = "<bucket>"  # dry-run does not require credentials

    uploaded = skipped = 0
    uploaded_bytes = 0
    failed: list[str] = []
    for path in files:
        rel = path.relative_to(library_root).as_posix()
        key = prefix + rel
        size = path.stat().st_size
        sha = sha256_file(path)

        is_manifest = path.suffix.lower() == ".json"
        cache_control = MANIFEST_CACHE_CONTROL if is_manifest else IMAGE_CACHE_CONTROL
        content_type = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")

        if not args.dry_run and remote_matches(client, bucket, key, size, sha):
            skipped += 1
            continue

        print(f"{'WOULD UPLOAD' if args.dry_run else 'upload'}  {key}  ({size / 1_048_576:.1f} MB)", flush=True)
        if args.dry_run:
            uploaded += 1
            uploaded_bytes += size
            continue

        try:
            client.upload_file(
                str(path),
                bucket,
                key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": cache_control,
                    "Metadata": {"sha256": sha},
                },
            )
        except Exception as exc:
            # Don't abort the whole run for one bad object — record it and move
            # on. Already-uploaded files are skipped on the next run, so a
            # re-run resumes and retries only what's left.
            print(f"  FAILED  {key}: {exc}", flush=True)
            failed.append(key)
            continue
        uploaded += 1
        uploaded_bytes += size

    verb = "would upload" if args.dry_run else "uploaded"
    print(
        f"\nDone: {verb} {uploaded} file(s) ({uploaded_bytes / 1_073_741_824:.2f} GB), "
        f"skipped {skipped} unchanged, {len(failed)} failed, {len(files)} total."
    )
    if failed:
        print(f"Failed objects ({len(failed)}): re-run to retry just these.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
