#!/usr/bin/env python3
"""
Cross-platform Lambda deployment package creator using uv.
Works on Windows, Mac, and Linux.
"""

import os
import sys
import shutil
import site
import zipfile
from pathlib import Path


def resolve_site_packages():
    """Return the active interpreter's site-packages directory."""
    candidates = []

    # Include standard site-packages locations from the current interpreter.
    candidates.extend(site.getsitepackages())
    candidates.extend(site.getusersitepackages().split(os.sep)[:-1])

    # Add the sysconfig path for the current interpreter.
    try:
        import sysconfig

        candidates.append(sysconfig.get_paths().get("purelib"))
        candidates.append(sysconfig.get_paths().get("platlib"))
    except Exception:
        pass

    # Also check common uv-managed virtualenv locations.
    current_dir = Path(__file__).parent
    candidates.extend(
        [
            current_dir / ".venv" / "lib",
            current_dir / ".venv" / "Lib",
        ]
    )

    for candidate in candidates:
        if not candidate:
            continue

        candidate_path = Path(candidate)
        if candidate_path.name == "site-packages":
            if candidate_path.exists():
                return str(candidate_path)
        elif candidate_path.exists():
            for child in candidate_path.rglob("site-packages"):
                if child.exists():
                    return str(child)

    return None


def create_deployment_package():
    """Create a Lambda deployment package with dependencies from uv."""

    # Paths
    current_dir = Path(__file__).parent
    build_dir = current_dir / "build"
    package_dir = build_dir / "package"
    zip_path = current_dir / "lambda_function.zip"

    # Clean up previous builds
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if zip_path.exists():
        os.remove(zip_path)

    # Create build directory
    package_dir.mkdir(parents=True, exist_ok=True)

    # Find the site-packages directory for the active interpreter.
    site_packages = resolve_site_packages()

    if not site_packages or not Path(site_packages).exists():
        print(
            "Error: Could not find site-packages for the active Python interpreter. Make sure dependencies are installed with 'uv sync' or 'uv add'."
        )
        sys.exit(1)

    print(f"Copying dependencies from {site_packages}...")
    # Copy all dependencies to package directory
    site_packages_path = Path(site_packages)
    for item in site_packages_path.iterdir():
        if item.name.endswith(".dist-info") or item.name == "__pycache__":
            continue
        if item.is_dir():
            shutil.copytree(item, package_dir / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, package_dir)

    # Copy Lambda function code
    print("Copying Lambda function code...")

    # Copy S3 Vectors Lambda handlers
    if (current_dir / "ingest_s3vectors.py").exists():
        shutil.copy(current_dir / "ingest_s3vectors.py", package_dir)
    if (current_dir / "search_s3vectors.py").exists():
        shutil.copy(current_dir / "search_s3vectors.py", package_dir)

    # Create ZIP file
    print("Creating deployment package...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith(".pyc"):
                    continue
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)

    # Clean up build directory
    shutil.rmtree(build_dir)

    # Get file size
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Deployment package created: {zip_path}")
    print(f"   Size: {size_mb:.2f} MB")

    if size_mb > 50:
        print("⚠️  Warning: Package exceeds 50MB. Consider using Lambda Layers.")

    return str(zip_path)


if __name__ == "__main__":
    create_deployment_package()
