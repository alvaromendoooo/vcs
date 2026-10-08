from pydantic import BaseModel
from typing import Literal

class CreateRepo(BaseModel):
    name: str
    description: str
    homepage: str
    private: bool
    is_template: bool
    template_format: str

class CommitChanges(BaseModel):
    op: Literal["mkdir", "add", "modify", "delete"]
    path: str
    content: str = None

class CommitContent(BaseModel):
    author: str
    message: str
    changes: list[CommitChanges]