import os
import tempfile
from pathlib import Path

_root = Path(tempfile.mkdtemp(prefix="tripwise-test-"))
os.environ["SQLITE_PATH"] = str(_root / "test.db")
os.environ["CHROMA_PATH"] = str(_root / "chroma")
os.environ["UPLOAD_PATH"] = str(_root / "uploads")
os.environ["JWT_SECRET"] = "test-secret"
os.environ["GROQ_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
