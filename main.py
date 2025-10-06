# Entry point to run the FastAPI web application only.
import sys

try:
    import uvicorn  # type: ignore
except ImportError as e:
    print("uvicorn is required. Install dependencies first.")
    sys.exit(1)

try:
    from app import app  # FastAPI instance
except Exception as e:
    print("Failed to import FastAPI app:", e)
    sys.exit(1)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8011)
