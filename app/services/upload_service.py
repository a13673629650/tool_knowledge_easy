from datetime import datetime
from pathlib import Path


def write_log(path:str=None, content:str=None):
    Path("logs").mkdir(exist_ok=True)
    if path is None:
        path = f"{datetime.now().date()}"
    with open(f"logs/upload{path}.log", "a", encoding="utf-8") as f:
        f.write(content)