import os
import urllib.request
import tarfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_model():
    url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2"
    output_dir = "models"
    os.makedirs(output_dir, exist_ok=True)

    model_name = "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
    model_path = os.path.join(output_dir, model_name)

    required_files = [
        "encoder.int8.onnx",
        "decoder.int8.onnx",
        "joiner.int8.onnx",
        "tokens.txt",
    ]

    missing = False
    if not os.path.exists(model_path):
        missing = True
    else:
        for f in required_files:
            if not os.path.exists(os.path.join(model_path, f)):
                missing = True
                break

    if not missing:
        logger.info(f"Model {model_name} already exists and is complete.")
        return

    filename = url.split("/")[-1]
    output_path = os.path.join(output_dir, filename)

    logger.info(f"Downloading {url}...")
    try:
        urllib.request.urlretrieve(url, output_path)
    except Exception as e:
        logger.error(f"Failed to download model: {e}")
        return

    logger.info("Extracting...")
    try:
        with tarfile.open(output_path, "r:bz2") as tar:
            tar.extractall(output_dir)
    except Exception as e:
        logger.error(f"Failed to extract model: {e}")
        return

    if os.path.exists(output_path):
        os.remove(output_path)
    logger.info("Model download and extraction complete.")


if __name__ == "__main__":
    download_model()
