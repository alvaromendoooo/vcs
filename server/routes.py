from fastapi import APIRouter, Depends, HTTPException

from .deps import get_service
from .errors import InvalidName, ObjectNotFound, RepoExists, RepoNotFound
from .schemas import CommitContent, CreateRepo
from .service import VCSService

router = APIRouter()

@router.post("/repo", status_code=201)
def create_repo(repo: CreateRepo, service: VCSService = Depends(get_service)):
    try:
        return service.create_repo(repo)
    except InvalidName as e:
        raise HTTPException(422, str(e))
    except RepoExists:
        raise HTTPException(409, "Repository already exists")


@router.post("/repos/{repo}/commit", status_code=201)
def commit_changes(repo: str, changes: CommitContent, service: VCSService = Depends(get_service)):
    try:
        return {"commit": service.commit(repo, changes)}
    except InvalidName as e:
        raise HTTPException(422, str(e))
    except RepoNotFound:
        raise HTTPException(404, "Repository not found")
    except ObjectNotFound as e:
        raise HTTPException(500, f"Corrupt repository: missing object {e}")


@router.get("/repos/{repo}")
def get_repo_info(repo: str, service: VCSService = Depends(get_service)):
    try:
        return service.get_repo_info(repo)
    except InvalidName as e:
        raise HTTPException(422, str(e))
    except RepoNotFound:
        raise HTTPException(404, "Repository not found")


@router.get("/")
async def read_root():
    return {"message": "API is running"}


@router.get("/health")
async def health_check():
    return {"status": "ok"}
