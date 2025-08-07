"""
Setup script for DDV Save Editor
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="ddv-save-editor",
    version="1.0.0",
    author="DDV Save Editor Contributors",
    description="A Python-based save editor for Disney Dreamlight Valley",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ddv-save-editor-python",
    
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    install_requires=requirements,
    
    entry_points={
        'console_scripts': [
            'ddv-editor=main:main',
        ],
    },
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Games/Entertainment",
        "Topic :: Utilities",
    ],
    
    python_requires=">=3.8",
    
    keywords="disney dreamlight valley save editor game utility",
    
    include_package_data=True,
    zip_safe=False,
)
