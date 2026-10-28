# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
from setuptools import find_packages, setup

package_name = "r2_pico_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="NandoMadrid",
    maintainer_email="BeskarCode@users.noreply.github.com",
    description="ROS2D2 bridge to the Pico that reads the distance sensors",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "pico_bridge = r2_pico_bridge.pico_bridge_node:main",
            "fake_pico = r2_pico_bridge.fake_pico:main",
        ],
    },
)
