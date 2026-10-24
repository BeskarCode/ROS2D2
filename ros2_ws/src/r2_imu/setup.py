from glob import glob

from setuptools import find_packages, setup

package_name = "r2_imu"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Fernando Beltran",
    maintainer_email="fernando.beltran@gmail.com",
    description="ROS2D2 IMU node (MPU6050 over I2C)",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "imu_node = r2_imu.imu_node:main",
        ],
    },
)
