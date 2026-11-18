import hashlib
from pathlib import Path


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        while block := file.read(1024 * 1024):
            digest.update(block)

    return digest.hexdigest()