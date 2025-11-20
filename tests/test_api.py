import os
import pytest
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

# Mocking the heavy AI functions to avoid actual processing during simple API tests
# In a real scenario, we might want integration tests, but for now we test the flow.
from unittest.mock import patch


@pytest.fixture
def mock_ai_pipeline():
    with (
        patch("server.routers.audio.convert_to_wav") as mock_wav,
        patch("server.routers.audio.transcribe_audio") as mock_asr,
        patch("server.routers.audio.split_sentences") as mock_nlp,
        patch("server.routers.audio.generate_srt") as mock_srt,
        patch("server.routers.audio.sf.info") as mock_sf_info,
    ):
        mock_wav.return_value = "test.wav"
        mock_asr.return_value = {
            "text": "Hello world",
            "tokens": ["Hello", " world"],
            "timestamps": [0.0, 1.0],
        }
        mock_nlp.return_value = [{"text": "Hello world", "start": 0.0, "end": 1.0}]
        mock_srt.return_value = "1\n00:00:00,000 --> 00:00:01,000\nHello world\n"

        # Mock sf.info object
        class MockInfo:
            duration = 10.0

        mock_sf_info.return_value = MockInfo()

        yield


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hearing API is running"}


def test_upload_flow(mock_ai_pipeline):
    # 1. Upload
    # Create a dummy file
    with open("test_audio.mp3", "wb") as f:
        f.write(b"dummy audio content")

    try:
        with open("test_audio.mp3", "rb") as f:
            response = client.post(
                "/api/audio/upload", files={"file": ("test_audio.mp3", f, "audio/mpeg")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        task_id = data["task_id"]
        assert data["status"] == "pending"

        # 2. Process
        response = client.post(f"/api/audio/process/{task_id}")
        assert response.status_code == 200

        # 3. Check Status (it might be fast since we mocked it, but background tasks run after response)
        # We can't easily test background tasks with TestClient synchronously unless we force it.
        # But for unit test, we just check if the endpoint returns 200.

    finally:
        if os.path.exists("test_audio.mp3"):
            os.remove("test_audio.mp3")
