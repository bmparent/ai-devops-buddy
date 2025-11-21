from setuptools import setup, find_packages

setup(
    name="ai_buddy",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "matplotlib>=3.7.0",
        "plotly>=5.15.0",
    ],
)
