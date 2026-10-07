import os
from pathlib import Path

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./certs.db")
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./generated")).resolve()
MAX_RECIPIENTS_PER_JOB: int = int(os.getenv("MAX_RECIPIENTS_PER_JOB", "1000"))
