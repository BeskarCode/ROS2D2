from glob import glob

from setuptools import find_packages, setup

package_name = "r2_dome_tracker"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Fernando Beltran",
    maintainer_email="Fernando-Beltran@users.noreply.github.com",
    description="ROS2D2 dome tracker",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "dome_tracker = r2_dome_tracker.dome_tracker_node:main",
        ],
    },
)
