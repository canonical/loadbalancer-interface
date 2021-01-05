from setuptools import setup


SETUP = {
    "name": "loadbalancer-interface",
    "version": "1.0.0",
    "author": "Cory Johns",
    "author_email": "cory.johns@canonical.com",
    "url": "https://github.com/juju-solutions/loadbalancer-interface",
    "py_modules": ["loadbalancer_interface"],
    "install_requires": [
        "ops>=1.0.0",
    ],
    # TODO: move this to normal PyPI dependency when ready
    "dependency_links": [
        "https://github.com/juju-solutions/ops-reactive-interface/archive/master.zip#egg=ops-reactive-interface",  # noqa
    ],
    "entry_points": {
        "ops_reactive_interface.provides": "loadbalancer = loadbalancer_interface:LBProducer",  # noqa
        "ops_reactive_interface.requires": "loadbalancer = loadbalancer_interface:LBConsumer",  # noqa
    },
    "license": "Apache License 2.0",
    "description": "'loadbalancer' interface protocol API library",
    "long_description_content_type": "text/markdown",
    "long_description": open("README.md").read(),
}


if __name__ == "__main__":
    setup(**SETUP)
