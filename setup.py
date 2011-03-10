from setuptools import setup, find_packages

version = 'EXPERIMENTAL'

setup(
    name = 'project-nani',
    version = version,
    description = 'EXPERIMENTAL new multilingual database content app',
    author = 'Jonas Obrist',
    author_email = 'jonas.obrist@divio.ch',
    packages = find_packages(),
    zip_safe=False,
    install_requires=[
        'Django>=1.2',
    ],
)
