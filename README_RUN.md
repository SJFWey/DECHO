# How to Run the Hearing App

## Prerequisites
- Python 3.13+
- Node.js & npm
- `uv` (optional, but recommended for Python dependency management)

## 1. Backend Setup (FastAPI)

1.  **Install Dependencies**:
    ```powershell
    # Using uv (recommended)
    uv sync
    
    # OR using pip
    pip install -e .
    ```

2.  **Start the Server**:
    ```powershell
    # Using uv
    uv run uvicorn server.main:app --reload --port 8000

    # OR using python directly
    python -m uvicorn server.main:app --reload --port 8000
    ```
    The backend will be available at `http://localhost:8000`.

## 2. Frontend Setup (Next.js)

1.  **Install Dependencies**:
    ```powershell
    cd web
    npm install
    ```

2.  **Database Setup**:
    Ensure the database schema is pushed (if not already):
    ```powershell
    npx prisma generate
    npx prisma db push
    ```

3.  **Start the Frontend**:
    ```powershell
    npm run dev
    ```
    The frontend will be available at `http://localhost:3000`.

## 3. Usage
Open `http://localhost:3000` in your browser. The frontend will communicate with the backend running on port 8000.
