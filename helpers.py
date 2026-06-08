"""通用工具函数"""

import re


def format_time(seconds: float) -> str:
    if seconds <= 0 or seconds == float("inf"):
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def sanitize_filename(name: str) -> str:
    name = re.sub(r"""[<>:"/\\|?*']""", "_", name)
    name = name.strip().strip(".")
    return name or "untitled"
