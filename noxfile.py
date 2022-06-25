import os
import sys
import subprocess
from pathlib import Path

import nox


PYODIDE_VERSION = os.getenv("PYODIDE_VERSION", "0.21.0-alpha.2")
GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS")
GITHUB_ENV = os.getenv("GITHUB_ENV")


def append_to_github_env(name: str, value: str):
    if not GITHUB_ACTIONS or not GITHUB_ENV:
        return

    with open(GITHUB_ENV, "w+") as f:
        f.write(f"{name}={value}\n")


@nox.session(name="setup-pyodide")
def setup_pyodide(session: nox.Session):
    tests_dir = Path("./tests").resolve()
    with session.chdir(tests_dir):
        session.run(
            "npm",
            "i",
            "--no-save",
            f"pyodide@{PYODIDE_VERSION}",
            "prettier",
            external=True,
        )
        with session.chdir(tests_dir / "node_modules" / "pyodide"):
            session.run(
                "node",
                "../prettier/bin-prettier.js",
                "-w",
                "pyodide.asm.js",
                external=True,
            )
            emscripten_version = (
                subprocess.check_output(
                    '''node -p "require('./repodata.json').info.platform.split('_').slice(1).join('.')"''',
                    shell=True,
                )
                .decode()
                .strip()
            )
            append_to_github_env("EMSCRIPTEN_VERSION", emscripten_version)


@nox.session(name="test-emscripten")
def test_emscripten(session: nox.Session):
    tests_dir = Path("./tests").resolve()

    test_crates = [
        "test-crates/pyo3-pure",
        "test-crates/pyo3-mixed",
    ]
    for crate in test_crates:
        crate = Path(crate).resolve()
        ver = sys.version_info
        session.run(
            "cargo",
            "+nightly",
            "run",
            "build",
            "-m",
            str(crate / "Cargo.toml"),
            "--target",
            "wasm32-unknown-emscripten",
            "-i",
            f"python{ver.major}.{ver.minor}",
            external=True,
        )

        with session.chdir(tests_dir):
            session.run("node", "emscripten_runner.js", str(crate), external=True)