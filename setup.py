from setuptools import setup, find_packages

setup(
    name="alphax_ai_platform",
    version="0.5.1",
    description="AlphaX AI - enterprise AI layer for ERPNext/Frappe",
    author="AlphaX",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["frappe>=15.0.0"],
    zip_safe=False,
)
