from __future__ import annotations

from pathlib import Path

from setuptools import find_packages, setup


ROOT = Path(__file__).parent


def _read_requirements() -> list[str]:
    req_path = ROOT / "requirements.txt"
    if not req_path.exists():
        return []
    lines = []
    for raw in req_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def _src_top_level(packages: list[str]) -> set[str]:
    roots = set()
    for name in packages:
        root = name.split(".", maxsplit=1)[0]
        roots.add(root)
    return roots


root_packages = find_packages(".")
src_packages = find_packages("src")
all_packages = sorted(set(root_packages + src_packages))
package_dir = {"": "."}
for root in _src_top_level(src_packages):
    package_dir[root] = f"src/{root}"


setup(
    name="tickertape",
    version="0.1.0",
    description="TickerTape terminal analytics",
    packages=all_packages,
    package_dir=package_dir,
    include_package_data=True,
    install_requires=_read_requirements(),
    entry_points={
        "console_scripts": [
            "tickertape=tui.app:run",
            "tt=tui.app:run",
            "tickertape-serve=tui.serve:run",
            # Back-compat aliases
            "TickerTape=tui.app:run",
            "TTape=tui.app:run",
        ]
    },
)
