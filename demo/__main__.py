"""python -m demo  ->  serves the demo on http://127.0.0.1:8000 (localhost only)."""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("demo.app:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")), log_level="info")
