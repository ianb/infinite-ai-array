#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md") as readme_file:
    readme = readme_file.read()

requirements = ["openai"]

test_requirements = [
    "pytest>=3",
]

setup(
    author="Ian Bicking",
    author_email="ian@ianbicking.org",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Do you worry that you'll get to the end of a good list and have nothing more, leaving you sad and starved of data! Worry no more!",
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    include_package_data=True,
    keywords="gpt3",
    name="infinite_ai_array",
    packages=find_packages(include=["iaia", "iaia.*"]),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/ianb/infinite_ai_array",
    version="0.1.0",
    zip_safe=False,
)
