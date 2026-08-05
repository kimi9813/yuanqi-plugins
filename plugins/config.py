import os
from pathlib import Path


def get_data_dir() -> Path:
    """返回可用的数据目录。优先环境变量 DATA_DIR，否则尝试 ./data，不可写则回退 /tmp/data。"""
    if os.environ.get("DATA_DIR"):
        return Path(os.environ["DATA_DIR"])

    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        test = candidate / ".write_test"
        test.write_text("ok")
        test.unlink()
        return candidate
    except OSError:
        fallback = Path("/tmp/data")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
