#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for GPC Converter.

Build commands:
    python setup.py sdist bdist_wheel    # Create source and wheel distribution
    python setup.py pyinstaller           # Build standalone .exe (Windows)
"""

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get long description from README
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="gpc-converter",
    version="1.0.0",
    author="Majid Ka",
    author_email="jabawookez99@gmail.com",
    description="Convert Viva Wallet exports to POHODA GPC format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/majidka99/gpc-converter",
    project_urls={
        "Bug Tracker": "https://github.com/majidka99/gpc-converter/issues",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Natural Language :: English",
        "Natural Language :: Czech",
    ],
    package_dir={"": "."},
    packages=find_packages(where="."),
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies — uses only Python standard library
    ],
    entry_points={
        "console_scripts": [
            "gpc-converter=gpc_converter_gui:main",
        ],
        "gui_scripts": [
            "gpc-converter-gui=gpc_converter_gui:main",
        ],
    },
    include_package_data=True,
)
