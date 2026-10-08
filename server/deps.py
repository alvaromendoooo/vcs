import os
from functools import lru_cache
from pathlib import Path

from .service import VCSService
from .storage import FileSystemStorage, RepoStorage


@lru_cache
def get_storage() -> RepoStorage:
    return FileSystemStorage(Path(os.environ.get("VCS_STORAGE_ROOT", "data")))


def get_service() -> VCSService:
    return VCSService(get_storage())
