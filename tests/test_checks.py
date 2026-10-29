"""The rules behind the tools are plain functions, so we test them directly. No AI, no key."""
import pytest
import checks

GOOD = """<!DOCTYPE html><html><body><h1>Water</h1><button id="b">+250</button>
<span id="total">0</span>
<script>const k=localStorage.getItem('x');
document.getElementById('b').onclick=()=>{document.getElementById('total').textContent=1};
</script></body></html>"""


# ---- safe_filename ----------------------------------------------------------------
@pytest.mark.parametrize("name", ["index.html", "style.css", "app.js", "notes.md", " index.html "])
def test_plain_names_are_allowed(name):
    assert checks.safe_filename(name) == name.strip()

@pytest.mark.parametrize("name", ["../x.html", "a/b.html", "a\\b.html", "/etc/passwd", "x..html", "C:\\x.html"])
def test_names_that_escape_the_folder_are_refused(name):
    with pytest.raises(ValueError):
        checks.safe_filename(name)

@pytest.mark.parametrize("name", ["run.exe", "script.py", "noextension", "x.html.exe"])
def test_other_file_types_are_refused(name):
    with pytest.raises(ValueError):
        checks.safe_filename(name)

@pytest.mark.parametrize("name", ["", "   ", None, 5])
def test_empty_or_wrong_type_is_refused(name):
    with pytest.raises(ValueError):
        checks.safe_filename(name)


# ---- check_html -------------------------------------------------------------------
def test_a_good_page_has_no_problems():
    assert checks.check_html(GOOD) == []

def test_empty_body_is_caught():
    page = "<html><body><script>localStorage.x=1</script></body></html>"
    assert any("shows nothing" in p for p in checks.check_html(page))

def test_missing_script_is_caught():
    page = "<html><body><h1>Hi</h1></body></html>"
    assert any("no <script>" in p for p in checks.check_html(page))

def test_outside_files_are_caught():
    page = GOOD.replace("<script>", '<script src="https://cdn.example/x.js"></script><script>', 1)
    assert any("outside file" in p for p in checks.check_html(page))

def test_modules_are_caught():
    page = GOOD.replace("<script>", '<script type="module">', 1)
    assert any("modules" in p for p in checks.check_html(page))

def test_import_lines_are_caught():
    page = GOOD.replace("<script>", "<script>\nimport {a} from './a.js';\n", 1)
    assert any("modules" in p for p in checks.check_html(page))

def test_missing_local_storage_is_caught():
    page = GOOD.replace("localStorage", "memory")
    assert any("localStorage" in p for p in checks.check_html(page))

def test_unknown_element_id_is_named():
    page = GOOD.replace("getElementById('total')", "getElementById('totl')")
    problems = checks.check_html(page)
    assert any("totl" in p for p in problems)

def test_a_huge_file_is_flagged():
    page = GOOD.replace("</script>", "//" + "x" * 25000 + "</script>")
    assert any("very long" in p for p in checks.check_html(page))

def test_missing_html_and_body_tags():
    assert any("<html>" in p for p in checks.check_html("just text"))

def test_describe_problems():
    assert checks.describe_problems([]).startswith("OK")
    text = checks.describe_problems(["a", "b"])
    assert "1. a" in text and "2. b" in text
