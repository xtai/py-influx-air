from setuptools import find_packages, setup

setup(
    name="py-influx-air",
    version="0.0.1",
    author="Xiaoyu Tai (xtai)",
    author_email="xtai.dev@gmail.com",
    url="https://github.com/xtai/py-influx-air",
    description="A Python library that parses SDS011 and BME680 sensor data to an InfluxDB instance.",
    keywords=[
        "influxdb",
        "sds011",
        "bme680"
    ],
    license="MIT",
    install_requires=[
        "influxdb>=5.2",
        "pyserial>=3.4",
    ],
    setup_requires=[
    ],
    tests_require=[
    ],
    entry_points={
        "console_scripts": [
            "air = air.__main__:main",
        ],
    },
)
