from setuptools import find_packages, setup

setup(
    name="ota-marketing-diagnosis",
    version="0.1.0",
    description="Independent third-party OTA marketing diagnosis tool",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=["openpyxl>=3.1.0"],
)
