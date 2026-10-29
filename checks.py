"""
checks.py -- plain Python functions with no AI in them.

These are the rules the agent's tools use. Because they are ordinary functions,
we can unit-test them (see tests/test_checks.py). This is the same idea as
Chapter 8: keep the logic you can test separate from the part that talks to a model.
"""
import re
from pathlib import PurePath

ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".md"}
MAX_FILE_CHARS = 20_000


def safe_filename(name):
    """Return a safe file name, or raise ValueError saying why not.
    Only a bare name like 'index.html' is allowed: no folders, no '..', no odd types."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("The file name is empty.")
    name = name.strip()
    if name != PurePath(name).name or "\\" in name or "/" in name or ".." in name:
        raise ValueError(f"'{name}' is not allowed. Use a plain file name such as index.html.")
    if PurePath(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"'{name}' has a file type that is not allowed. "
                         f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.")
    return name


def check_html(text):
    """Look at a web page's text and return a list of problems (empty list = looks OK).
    This is a quick static check. It does not run the page."""
    problems = []
    low = text.lower()
    if "<html" not in low or "<body" not in low:
        problems.append("The page needs <html> and <body> tags.")
    body = re.search(r"<body[^>]*>(.*?)</body>", text, re.DOTALL | re.IGNORECASE)
    visible = re.sub(r"<script.*?</script>", "", body.group(1), flags=re.DOTALL | re.IGNORECASE) if body else ""
    if body and not re.search(r"<(button|input|p|h1|h2|div|span|ul|li|table|form)\b", visible, re.IGNORECASE):
        problems.append("The <body> shows nothing: it has no buttons, text, or other elements.")
    if "<script" not in low:
        problems.append("There is no <script> block, so nothing will work when you click.")
    if re.search(r"<script[^>]+src\s*=", text, re.IGNORECASE) or re.search(r"<link[^>]+href\s*=\s*[\"']https?:", text, re.IGNORECASE):
        problems.append("The page loads an outside file. It must be self-contained (inline CSS and JavaScript).")
    if re.search(r"type\s*=\s*[\"']module[\"']", text, re.IGNORECASE) or re.search(r"^\s*(import|export)\s", text, re.MULTILINE):
        problems.append("The page uses JavaScript modules (import/export). Browsers block those when you "
                        "double-click a file. Put everything in one plain <script>.")
    if "localstorage" not in low:
        problems.append("The page never uses localStorage, so data will not survive a reload.")
    ids_in_html = set(re.findall(r"\bid\s*=\s*[\"']([\w-]+)[\"']", text))
    ids_used = set(re.findall(r"getElementById\(\s*[\"']([\w-]+)[\"']\s*\)", text))
    missing = sorted(ids_used - ids_in_html)
    if missing:
        problems.append("The script looks for element ids that do not exist in the page: " + ", ".join(missing) + ".")
    if len(text) > MAX_FILE_CHARS:
        problems.append(f"The file is very long ({len(text):,} characters). Keep it small.")
    return problems


def describe_problems(problems):
    """The text the tool hands back to the agent."""
    if not problems:
        return "OK: no problems found by the static check."
    return "PROBLEMS FOUND:\n" + "\n".join(f"{i}. {p}" for i, p in enumerate(problems, 1))
