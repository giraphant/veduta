import hashlib
import urllib.request

import veduta_data.downloader as downloader
from veduta_data.downloader import download_first_working, sha256_file


def test_download_first_working_skips_existing_high_resolution_file(tmp_path, monkeypatch):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"good")

    def fail_download(url, destination):
        raise AssertionError("should not download when a good file exists")

    monkeypatch.setattr(downloader, "download_url", fail_download)
    monkeypatch.setattr(downloader, "image_dimensions", lambda path: (4096, 2650))
    monkeypatch.setattr(downloader, "verify_decodable_image", lambda path: None)

    result = download_first_working(["https://example.test/image.jpg"], image_path, delay_seconds=0)

    assert result["status"] == "skipped"
    assert result["url"] is None
    assert image_path.read_bytes() == b"good"


def test_sha256_file_hashes_file_contents(tmp_path):
    path = tmp_path / "payload.bin"
    path.write_bytes(b"veduta")
    assert sha256_file(path) == hashlib.sha256(b"veduta").hexdigest()


def test_download_url_sends_artic_referer_for_artic_iiif_images(tmp_path, monkeypatch, fake_urlopen):
    seen_requests = []
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen(b"image", content_type="image/jpeg", seen=seen_requests))

    destination = tmp_path / "image.jpg"
    downloader.download_url(
        "https://www.artic.edu/iiif/2/image-id/full/843,/0/default.jpg",
        destination,
    )

    assert destination.read_bytes() == b"image"
    assert seen_requests[0].headers["Referer"] == "https://www.artic.edu/"


def test_download_url_converts_tiff_response_to_high_quality_jpeg_destination(tmp_path, monkeypatch, fake_urlopen):
    calls = []

    def fake_run(command, text, capture_output, check):
        calls.append(command)
        output_path = command[-1]
        with open(output_path, "wb") as handle:
            handle.write(b"jpeg")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen(b"tiff", content_type="image/tiff"))
    monkeypatch.setattr(downloader.subprocess, "run", fake_run)

    destination = tmp_path / "image.jpg"
    downloader.download_url("https://example.test/full.tif", destination)

    assert destination.read_bytes() == b"jpeg"
    assert calls[0][:7] == ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "95"]


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
    monkeypatch.setattr(downloader, "verify_decodable_image", lambda path: None)

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


def test_download_first_working_redownloads_existing_low_resolution_file(tmp_path, monkeypatch):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"low")
    calls = []

    def fake_image_dimensions(path):
        if path.read_bytes() == b"low":
            return (3400, 2200)
        return (4096, 2650)

    def fake_download_url(url, destination):
        calls.append(url)
        destination.write_bytes(b"high")

    monkeypatch.setattr(downloader, "image_dimensions", fake_image_dimensions)
    monkeypatch.setattr(downloader, "download_url", fake_download_url)
    monkeypatch.setattr(downloader, "verify_decodable_image", lambda path: None)

    result = download_first_working(["https://example.test/image.jpg"], image_path, delay_seconds=0)

    assert calls == ["https://example.test/image.jpg"]
    assert image_path.read_bytes() == b"high"
    assert result == {
        "status": "downloaded",
        "url": "https://example.test/image.jpg",
        "width": 4096,
        "height": 2650,
        "bytes": 4,
        "sha256": hashlib.sha256(b"high").hexdigest(),
    }


def test_download_first_working_redownloads_existing_undecodable_file(tmp_path, monkeypatch):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"bad-decode")
    calls = []

    def fake_download_url(url, destination):
        calls.append(url)
        destination.write_bytes(b"good")

    def fake_verify_decodable_image(path):
        if path.read_bytes() == b"bad-decode":
            raise ValueError("invalid jpeg")

    monkeypatch.setattr(downloader, "image_dimensions", lambda path: (4096, 2650))
    monkeypatch.setattr(downloader, "download_url", fake_download_url)
    monkeypatch.setattr(downloader, "verify_decodable_image", fake_verify_decodable_image)

    result = download_first_working(["https://example.test/image.jpg"], image_path, delay_seconds=0)

    assert calls == ["https://example.test/image.jpg"]
    assert result["status"] == "downloaded"
    assert image_path.read_bytes() == b"good"


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
    monkeypatch.setattr(downloader, "verify_decodable_image", lambda path: None)

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


def test_download_first_working_falls_back_when_candidate_is_undecodable(tmp_path, monkeypatch):
    image_path = tmp_path / "image.jpg"
    calls = []

    def fake_download_url(url, destination):
        calls.append(url)
        destination.write_bytes(b"bad" if url.endswith("first.jpg") else b"good")

    def fake_verify_decodable_image(path):
        if path.read_bytes() == b"bad":
            raise ValueError("invalid jpeg")

    monkeypatch.setattr(downloader, "download_url", fake_download_url)
    monkeypatch.setattr(downloader, "image_dimensions", lambda path: (4096, 2650))
    monkeypatch.setattr(downloader, "verify_decodable_image", fake_verify_decodable_image)

    result = download_first_working(
        ["https://example.test/first.jpg", "https://example.test/second.jpg"], image_path, delay_seconds=0
    )

    assert calls == ["https://example.test/first.jpg", "https://example.test/second.jpg"]
    assert result["url"] == "https://example.test/second.jpg"
    assert image_path.read_bytes() == b"good"
