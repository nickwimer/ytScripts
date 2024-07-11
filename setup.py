from setuptools import find_packages, setup

install_requires = [
    "yt",
    "numpy",
    "pandas",
    "matplotlib",
    "h5py",
    "scikit-image",
    "pydantic",
    "black",
    "isort",
    "flake8",
    "lxml",
    "mpi4py",
    "pyvalem",
    "sphinx",
    "sphinx_rtd_theme",
    "sphinx_argparse",
]


setup(
    name="ytscripts",
    version="0.1.0",
    description="Scripts for visualization using the yt project",
    url="https://github.com/nickwimer/ytScripts",
    author="Nicholas T. Wimer",
    author_email="nicholas.wimer@gmail.com",
    license="MIT License",
    packages=find_packages(),
    install_requires=install_requires,
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9, <3.12",
    entry_points={
        "console_scripts": [
            "quick_vis = quick_vis:main",
            "data_extraction = data_extraction:main",
            "plot_data = plot_data:main",
        ],
    },
)
