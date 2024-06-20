import os

import versioneer
from setuptools import find_packages, setup

DESCRIPTION = (
    'Flexible recursive directory iterator: scandir meets glob("**", recursive=True)'
)

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(PROJECT_ROOT, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except OSError:
    long_description = DESCRIPTION

setup(
    name="scantree",
    version=versioneer.get_version(),
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/andhus/scantree",
    author="Anders Huss",
    author_email="andhus@kth.se",
    license="MIT",
    python_requires=">=3.8",
    install_requires=["attrs>=18.0.0", "pathspec>=0.10.1"],
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    entry_points={},
    tests_require=["pytest", "pytest-cov", "pre-commit"],
)
