"""Setup script for gbm-simulator package."""

from setuptools import setup, find_packages

setup(
    name="gbm-simulator",
    version="1.0.0",
    description="Stock Price Simulation using Geometric Brownian Motion",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="GBM Contributors",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.20.0",
        "yfinance>=0.2.0",
        "matplotlib>=3.3.0",
        "pandas>=1.3.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "gbm=gbm.cli:main",
        ],
    },
)

