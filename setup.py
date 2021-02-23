from setuptools import setup


SETUP = {
    "name": "loadbalancer_interface",
    "version": "1.0.5",
    "author": "Cory Johns",
    "author_email": "cory.johns@canonical.com",
    "url": "https://github.com/juju-solutions/loadbalancer-interface",
    "packages": [
        "loadbalancer_interface",
        "loadbalancer_interface.schemas",
    ],
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
    },
    "license": "Apache License 2.0",
    "description": "'loadbalancer' interface protocol API library",
    "long_description_content_type": "text/markdown",
    "long_description": open("README.md").read(),
}


if __name__ == "__main__":
    setup(**SETUP)
