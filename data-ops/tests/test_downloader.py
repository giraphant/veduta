import hashlib

from openartpaper_data.downloader import choose_download_state, sha256_file


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
