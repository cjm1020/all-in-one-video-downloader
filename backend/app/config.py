import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    data_dir: Path = Path(os.getenv("DATA_DIR", "data")).resolve()
    access_token: str = os.getenv("ACCESS_TOKEN", "")
    cookie_file: str = os.getenv("COOKIE_FILE", "")
    deepseek_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    max_storage_gb: float = float(os.getenv("MAX_STORAGE_GB", "10"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "library.sqlite3"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"


config = Config()
