from setuptools import setup
from shutil import rmtree


SETUP = {
    "name": "loadbalancer_interface",
    "version": "1.2.0",
    "author": "Cory Johns",
    "author_email": "cory.johns@canonical.com",
    "url": "https://github.com/juju-solutions/loadbalancer-interface",
    "packages": [
        "loadbalancer_interface",
        "loadbalancer_interface.schemas",
        "loadbalancer_interface.examples",  # Synthetic package populated at build time
    ],
    "package_dir": {
        "loadbalancer_interface.examples": "examples",
    },
    "package_data": {
        "loadbalancer_interface.examples": [
            "../examples/lb-provider/*",
            "../examples/lb-provider/*/*",
            "../examples/lb-consumer/*",
            "../examples/lb-consumer/*/*",
            "../examples/lb-provider-reactive/*",
            "../examples/lb-provider-reactive/*/*",
            "../examples/lb-provider-reactive/*/*/*/*",
            "../examples/lb-consumer-reactive/*",
            "../examples/lb-consumer-reactive/*/*",
            "../examples/lb-consumer-reactive/*/*/*/*",
        ],
    },
    "install_requires": [
        "ops>=1.0.0",
        "cached_property",
        "marshmallow",
        "marshmallow-enum",
        "ops_reactive_interface",
    ],
    "entry_points": {
        "ops_reactive_interface.provides": "loadbalancer = loadbalancer_interface:LBConsumers",  # noqa
        "ops_reactive_interface.requires": "loadbalancer = loadbalancer_interface:LBProvider",  # noqa
        "pytest11": [
            "loadbalancer-test-charm = loadbalancer_interface.pytest_plugin",
        ]
    },
    "license": "Apache License 2.0",
    "description": "'loadbalancer' interface protocol API library",
    "long_description_content_type": "text/markdown",
    "long_description": open("README.md").read(),
}


if __name__ == "__main__":
    rmtree("dist", ignore_errors=True)
    setup(**SETUP)
    rmtree("loadbalancer_interface.egg-info", ignore_errors=True)
