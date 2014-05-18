from setuptools import setup, find_packages
from hvad import __version__ as version

with open('README.rst') as f:
    long_description = f.read()

setup(
    name = 'django-hvad',
    version = version,
    description = 'A content translation framework for django integrated automatically in the normal ORM. Removes the pain of having to think about translations in a django project.',
    long_description = long_description,
    author = 'Kristian Ollegaard',
    author_email = 'kristian.ollegaard@divio.ch',
    url = 'https://github.com/KristianOellegaard/django-hvad',
    packages = find_packages(
        exclude = [
            'testproject',
            'testproject.app',
            'nani.tests',
            'hvad.tests',
        ],
    ),
    zip_safe=False,
    include_package_data = True,
    install_requires=[
        'Django>=1.3',
    ],
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Database",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ]
)
