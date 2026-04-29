from setuptools import find_packages, setup

install_requires = ["numpy", "pytest-benchmark"]

setup(
    name="reliabilityassessment",
    version="0.1",
    description="Grid Reliability Assessment",
    url="https://github.com/Breakthrough-Energy/reliability-assessment",
    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
)
