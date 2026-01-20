#!/usr/bin/env python
"""
Setup script for PowerMCP
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="powermcp",
    version="0.1.0",
    description="Open-source collection of MCP servers for power system software",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="PowerMCP Team",
    author_email="",
    url="https://github.com/Power-Agent/PowerMCP",
    project_urls={
        "Documentation": "https://power-agent.github.io/",
        "Source": "https://github.com/Power-Agent/PowerMCP",
        "Bug Tracker": "https://github.com/Power-Agent/PowerMCP/issues",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.10",
    install_requires=[
        "fastmcp>=2.0.1",
        "mcp>=1.0.0",
    ],
    extras_require={
        # Individual power system tools
        "andes": ["andes>=1.9.0"],
        "egret": ["egret>=0.0.2"],
        "opendss": ["opendssdirect.py>=0.8.0"],
        "pandapower": ["pandapower>=2.13.0"],
        "powerworld": ["pywin32>=306; sys_platform == 'win32'"],
        "pypsa": [
            "pypsa>=0.25.0",
            "highspy>=1.5.0",
            "networkx>=3.0",
            "cartopy>=0.21.0",
        ],
        "pyltspice": [
            "PyLTSpice>=1.0.0",
            "matplotlib>=3.5.0",
        ],
        # Development dependencies
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "pytest-timeout>=2.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pylint>=2.17.0",
            "isort>=5.12.0",
        ],
        # Testing dependencies
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "mock>=5.0.0",
        ],
        # Install all open-source tools
        "all-opensource": [
            "andes>=1.9.0",
            "egret>=0.0.2",
            "opendssdirect.py>=0.8.0",
            "pandapower>=2.13.0",
            "pypsa>=0.25.0",
            "highspy>=1.5.0",
            "networkx>=3.0",
            "PyLTSpice>=1.0.0",
            "matplotlib>=3.5.0",
        ],
    },
    package_data={
        "": ["*.json", "*.dss", "*.csv", "*.pwb", "*.pwd", "*.sav", "*.dyr", 
             "*.dyd", "*.m", "*.nc", "*.otg", "*.cntl", "*.dycr", "*.con", 
             "*.mon", "*.sub"],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="mcp power-systems simulation ai llm",
    license="MIT",
)
