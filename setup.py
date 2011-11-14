from setuptools import setup, find_packages
from nani import __version__ as version

setup(
    name = 'django-hvad',
    version = version,
    description = 'A translations framework for django integrated automatically in the normal ORM. Removes the pain of having to think about translations in a django project.',
    author = 'Kristian Ollegaard',
    author_email = 'kristian.ollegaard@divio.ch',
    url = 'https://github.com/KristianOellegaard/django-hvad',
    packages = find_packages(exclude=['testproject', 'testproject.app',
                                      'nani.tests']),
    zip_safe=False,
    include_package_data = True,
    install_requires=[
        'Django>=1.2',
    ],
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Database",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ]
)
