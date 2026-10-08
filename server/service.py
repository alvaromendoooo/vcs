import json
import time
from pathlib import PurePosixPath

from .errors import InvalidName
from .schemas import CommitContent, CreateRepo
from .storage import RepoStorage

DEFAULT_BRANCH = "main"


def _clean_path(path: str) -> str:
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise InvalidName(f"Invalid path: {path!r}")
    return p.as_posix()


class VCSService:
    def __init__(self, storage: RepoStorage):
        self.storage = storage

    def create_repo(self, repo: CreateRepo) -> dict:
        metadata = repo.model_dump()
        metadata["created_at"] = time.time()
        self.storage.create_repo(repo.name, metadata)
        return metadata

    def get_repo_info(self, name: str) -> dict:
        info = self.storage.get_metadata(name)
        info["head"] = self.storage.get_ref(name, DEFAULT_BRANCH)
        return info

    def commit(self, repo: str, content: CommitContent) -> str:
        parent = self.storage.get_ref(repo, DEFAULT_BRANCH)
        tree = self._load_tree(repo, parent)

        for change in content.changes:
            path = _clean_path(change.path)
            if change.op == "mkdir":
                if path not in tree["dirs"]:
                    tree["dirs"].append(path)
            elif change.op in ("add", "modify"):
                blob = self.storage.put_object(repo, (change.content or "").encode())
                tree["files"][path] = blob
            elif change.op == "delete":
                tree["files"].pop(path, None)

        tree_id = self.storage.put_object(repo, self._dump(tree))
        commit = {
            "tree": tree_id,
            "parent": parent,
            "author": content.author,
            "message": content.message,
            "timestamp": time.time(),
        }
        commit_id = self.storage.put_object(repo, self._dump(commit))
        self.storage.set_ref(repo, DEFAULT_BRANCH, commit_id, expected=parent)
        return commit_id

    def _load_tree(self, repo: str, commit_id: str | None) -> dict:
        if commit_id is None:
            return {"files": {}, "dirs": []}
        commit = json.loads(self.storage.get_object(repo, commit_id))
        return json.loads(self.storage.get_object(repo, commit["tree"]))

    @staticmethod
    def _dump(obj: dict) -> bytes:
        return json.dumps(obj, sort_keys=True).encode()
