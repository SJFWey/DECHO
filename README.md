# DECHO

<p align="center">
  <strong>A language learning tool for listening comprehension and pronunciation practice</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#demo">Demo</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a>
</p>

---

## Features

- **Speech Recognition (ASR)** - Powered by Sherpa-ONNX with NeMo Parakeet model for accurate transcription
- **Text-to-Speech (TTS)** - High-quality audio generation with customizable voices
- **Intelligent Text Processing** - LLM-powered sentence splitting and analysis
- **Multi-language Support** - English, German, Chinese and more via spaCy NLP
- **Practice Tracking** - Track your progress with detailed statistics
- **Interactive Practice Mode** - Listen, repeat, and compare your pronunciation
- **Beautiful Dark UI** - Modern "Silent Titanium" design system

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI, Python 3.13+, SQLAlchemy |
| **Frontend** | Next.js 16, React 19, TailwindCSS |
| **ASR** | Sherpa-ONNX (NeMo Parakeet TDT) |
| **NLP** | spaCy |
| **Database** | SQLite (via Prisma) |

## Prerequisites

- **Python 3.13+**
- **Node.js 18+** & npm
- **uv** (recommended for Python dependency management) - [Install uv](https://github.com/astral-sh/uv)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/SJFWey/decho.git
cd decho
```

### 2. Backend Setup

```bash
# Install Python dependencies using uv (recommended)
uv sync

# OR using pip
pip install -e .

# Download spaCy language models (as needed)
python -m spacy download en_core_web_md
python -m spacy download de_core_news_md
```

### 3. Frontend Setup

```bash
cd web
npm install

# Setup database
npx prisma generate
npx prisma db push
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys and settings
```

### 5. Download ASR Model

The ASR model needs to be downloaded manually. Download the **Sherpa-ONNX NeMo Parakeet TDT model** from the official repository:

**Download Link:** [sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models)

After downloading, extract and place the model files in the `models/` directory:

```
models/
└── sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/
    ├── decoder.int8.onnx
    ├── encoder.int8.onnx
    ├── joiner.int8.onnx
    └── tokens.txt
```

Alternatively, you can run the download script:

```bash
python scripts/download_models.py
```

## Usage

### Development Mode

**Start both services:**

```bash
# Terminal 1 - Backend
uv run uvicorn server.main:app --reload --port 8000

# Terminal 2 - Frontend
cd web && npm run dev
```

Or use VS Code tasks (recommended):
- Press `Ctrl+Shift+B` to run "Start All" task

**Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production Build

```bash
# Build frontend
cd web && npm run build

# Run production server
uv run uvicorn server.main:app --port 8000
```

## Configuration

All configuration is done via environment variables. See [`.env.example`](.env.example) for all available options.

### Key Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for LLM service | Required |
| `LLM_BASE_URL` | LLM API endpoint | Required |
| `TTS_API_KEY` | API key for TTS service | Required |
| `ASR_METHOD` | ASR engine (`parakeet`) | `parakeet` |
| `APP_SOURCE_LANGUAGE` | Source language code | `en` |
| `APP_TARGET_LANGUAGE` | Target language code | `de` |

## Project Structure

```
decho/
├── backend/           # Core Python modules
│   ├── asr.py        # Speech recognition
│   ├── audio_*.py    # Audio processing
│   ├── llm.py        # LLM integration
│   └── nlp.py        # NLP processing
├── server/           # FastAPI server
│   ├── main.py       # Application entry
│   ├── routers/      # API routes
│   └── models.py     # Database models
├── web/              # Next.js frontend
│   ├── app/          # App routes
│   ├── components/   # React components
│   └── lib/          # Utilities
├── models/           # ASR model files
├── scripts/          # Build & utility scripts
└── docs/             # Documentation
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) for the ASR engine
- [NeMo](https://github.com/NVIDIA/NeMo) for the Parakeet model
- [spaCy](https://spacy.io/) for NLP capabilities
- [shadcn/ui](https://ui.shadcn.com/) for UI components

---

<p align="center">Made with love for language learners</p>
