import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from ..errors import InvalidName, ObjectNotFound, RepoExists, RepoNotFound

_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _check_name(name: str) -> str:
    if not _NAME_RE.fullmatch(name) or name in {".", ".."}:
        raise InvalidName(f"Invalid name: {name!r}")
    return name


class FileSystemStorage:
    """Layout:
    <root>/<repo>/meta.json
    <root>/<repo>/objects/<ab>/<rest of sha256>
    <root>/<repo>/refs/<name>
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _repo_dir(self, repo: str) -> Path:
        return self.root / _check_name(repo)

    def _require(self, repo: str) -> Path:
        path = self._repo_dir(repo)
        if not path.is_dir():
            raise RepoNotFound(repo)
        return path

    def create_repo(self, repo: str, metadata: dict) -> None:
        path = self._repo_dir(repo)
        try:
            path.mkdir()
        except FileExistsError:
            raise RepoExists(repo) from None
        (path / "objects").mkdir()
        (path / "refs").mkdir()
        (path / "meta.json").write_text(json.dumps(metadata))

    def repo_exists(self, repo: str) -> bool:
        return self._repo_dir(repo).is_dir()

    def get_metadata(self, repo: str) -> dict:
        return json.loads((self._require(repo) / "meta.json").read_text())

    def put_object(self, repo: str, data: bytes) -> str:
        path = self._require(repo)
        object_id = hashlib.sha256(data).hexdigest()
        target = path / "objects" / object_id[:2] / object_id[2:]
        if not target.exists():
            target.parent.mkdir(exist_ok=True)
            self._atomic_write(target, data)
        return object_id

    def get_object(self, repo: str, object_id: str) -> bytes:
        path = self._require(repo)
        if not _HASH_RE.fullmatch(object_id):
            raise ObjectNotFound(object_id)
        target = path / "objects" / object_id[:2] / object_id[2:]
        try:
            return target.read_bytes()
        except FileNotFoundError:
            raise ObjectNotFound(object_id) from None

    def get_ref(self, repo: str, ref: str) -> str | None:
        target = self._require(repo) / "refs" / _check_name(ref)
        try:
            return target.read_text().strip()
        except FileNotFoundError:
            return None

    def set_ref(self, repo: str, ref: str, object_id: str, expected: str | None) -> None:
        # TODO: compare-and-swap. Needs a per-ref lock to be truly safe under
        # concurrent commits; for now only the write itself is atomic.
        target = self._require(repo) / "refs" / _check_name(ref)
        self._atomic_write(target, object_id.encode())

    @staticmethod
    def _atomic_write(target: Path, data: bytes) -> None:
        fd, tmp = tempfile.mkstemp(dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, target)
        except BaseException:
            os.unlink(tmp)
            raise
