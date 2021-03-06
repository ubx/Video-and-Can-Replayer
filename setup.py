import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Video-and-Can-Replayer",  # Replace with your own username
    version="0.1.0",
    author="Andreas Lüthi",
    author_email="andreas.luethi@gmx.net",
    description="Replay a video in sync with a can-bus logfile.",
    #long_description=long_description,
    #long_description_content_type="text/markdown",
    url="https://github.com/ubx/Video-and-Can-Replayer",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3.0",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
