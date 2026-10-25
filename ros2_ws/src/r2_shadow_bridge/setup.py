from setuptools import find_packages, setup

package_name = "r2_shadow_bridge"

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
    maintainer="Fernando Beltran",
    maintainer_email="BeskarCode@users.noreply.github.com",
    description="ROS2D2 bridge to the ShadowMD Mega",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mega_bridge = r2_shadow_bridge.mega_bridge_node:main",
            "foot_calibrate = r2_shadow_bridge.foot_calibrate:main",
        ],
    },
)
