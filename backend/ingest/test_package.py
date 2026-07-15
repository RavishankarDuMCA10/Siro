from pathlib import Path

from package import resolve_site_packages


def test_resolve_site_packages_uses_current_interpreter_path():
    site_packages = resolve_site_packages()

    assert site_packages is not None
    assert Path(site_packages).exists()
    assert Path(site_packages).name == "site-packages"
