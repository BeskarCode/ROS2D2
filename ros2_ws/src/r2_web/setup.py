import os
from glob import glob

from setuptools import find_packages, setup

package_name = "r2_web"


def web_files():
    """Every file under www/, keeping its folder (vendor/loaders, models...)."""
    out = []
    for folder, _, files in os.walk("www"):
        if files:
            out.append((os.path.join("share", package_name, folder), [os.path.join(folder, f) for f in files]))
    return out

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ] + web_files(),
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Fernando Beltran",
    maintainer_email="BeskarCode@users.noreply.github.com",
    description="ROS2D2 web console",
    license="MIT",
    entry_points={
        "console_scripts": [
            "web_console = r2_web.web_server_node:main",
        ],
    },
)
