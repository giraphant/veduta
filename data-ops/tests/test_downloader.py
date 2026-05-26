import hashlib

import openartpaper_data.downloader as downloader
from openartpaper_data.downloader import choose_download_state, download_first_working, sha256_file


def test_choose_download_state_skips_complete_file(tmp_path):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"abc")
    assert choose_download_state(image_path) == "skip"


def test_choose_download_state_retries_partial_file(tmp_path):
    image_path = tmp_path / "image.jpg"
    partial_path = tmp_path / "image.jpg.partial"
    partial_path.write_bytes(b"abc")
    assert choose_download_state(image_path) == "download"


def test_sha256_file_hashes_file_contents(tmp_path):
    path = tmp_path / "payload.bin"
    path.write_bytes(b"openartpaper")
    assert sha256_file(path) == hashlib.sha256(b"openartpaper").hexdigest()


def test_download_first_working_redownloads_corrupt_existing_file(tmp_path, monkeypatch):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"bad")
    calls = []

    def fake_image_dimensions(path):
        if path.read_bytes() == b"bad":
            raise ValueError("corrupt image")
        return (100, 200)

    def fake_download_url(url, destination):
        calls.append(url)
        destination.write_bytes(b"good")

    monkeypatch.setattr(downloader, "image_dimensions", fake_image_dimensions)
    monkeypatch.setattr(downloader, "download_url", fake_download_url)

    result = download_first_working(["https://example.test/image.jpg"], image_path, delay_seconds=0)

    assert calls == ["https://example.test/image.jpg"]
    assert image_path.read_bytes() == b"good"
    assert result == {
        "status": "downloaded",
        "url": "https://example.test/image.jpg",
        "width": 100,
        "height": 200,
        "bytes": 4,
        "sha256": hashlib.sha256(b"good").hexdigest(),
    }


def test_download_first_working_falls_back_to_second_candidate(tmp_path, monkeypatch):
    image_path = tmp_path / "image.jpg"
    calls = []

    def fake_download_url(url, destination):
        calls.append(url)
        if url == "https://example.test/first.jpg":
            raise ValueError("not an image")
        destination.write_bytes(b"second")

    monkeypatch.setattr(downloader, "download_url", fake_download_url)
    monkeypatch.setattr(downloader, "image_dimensions", lambda path: (300, 400))

    result = download_first_working(
        ["https://example.test/first.jpg", "https://example.test/second.jpg"], image_path, delay_seconds=0
    )

    assert calls == ["https://example.test/first.jpg", "https://example.test/second.jpg"]
    assert result == {
        "status": "downloaded",
        "url": "https://example.test/second.jpg",
        "width": 300,
        "height": 400,
        "bytes": 6,
        "sha256": hashlib.sha256(b"second").hexdigest(),
    }
