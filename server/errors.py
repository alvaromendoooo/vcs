class VCSError(Exception):
    """Base class for domain errors."""


class InvalidName(VCSError):
    pass


class RepoExists(VCSError):
    pass


class RepoNotFound(VCSError):
    pass


class ObjectNotFound(VCSError):
    pass
