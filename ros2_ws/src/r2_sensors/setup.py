# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from glob import glob

from setuptools import find_packages, setup

package_name = "r2_sensors"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="NandoMadrid",
    maintainer_email="BeskarCode@users.noreply.github.com",
    description="ROS2D2 distance sensors and lidar: sensors.yaml, their TF and the lidar",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "sensor_tf = r2_sensors.sensor_tf_node:main",
            "fake_lidar = r2_sensors.fake_lidar_node:main",
            "scan_crop = r2_sensors.scan_crop_node:main",
        ],
    },
)
