from glob import glob

from setuptools import find_packages, setup

package_name = "r2_vision"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/models", glob("models/*.onnx")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Fernando Beltran",
    maintainer_email="BeskarCode@users.noreply.github.com",
    description="ROS2D2 vision nodes (face detector)",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "face_detector = r2_vision.face_detector_node:main",
        ],
    },
)
