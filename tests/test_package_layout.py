from pathlib import Path


def test_package_layout_is_present():
    repository_root = Path(__file__).resolve().parents[1]
    package_root = repository_root / "src" / "likepilot"

    assert (package_root / "__init__.py").is_file()
    assert (package_root / "core" / "runtime.py").is_file()
    assert (package_root / "integrations" / "providers" / "base.py").is_file()
    assert (package_root / "dashboard" / "app.py").is_file()
    assert (package_root / "dashboard" / "templates" / "login.html").is_file()
    assert (package_root / "dashboard" / "static" / "dashboard.css").is_file()
    assert (package_root / "entrypoints" / "server.py").is_file()
