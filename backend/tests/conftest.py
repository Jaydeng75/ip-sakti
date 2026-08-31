import os
import tempfile
from pathlib import Path

TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="ip-sakti-tests-"))

os.environ["IPSAKTI_DATABASE_URL"] = f"sqlite:///{TEST_DATA_DIR / 'test.db'}"
os.environ["IPSAKTI_UPLOAD_DIR"] = str(TEST_DATA_DIR / "uploads")
os.environ["IPSAKTI_EXTERNAL_RESEARCH_ENABLED"] = "false"
