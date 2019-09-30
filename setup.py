# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="django-catalog",
    version=__import__('catalog').__version__,
    license="GPL",
    keywords="django catalog",

    author="Egor Slesarev",
    author_email="egor.slesarev@redsolution.ru",

    maintainer="Egor Slesarev",
    maintainer_email="egor.slesarev@redsolution.ru",

    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Framework :: Django',
        'Environment :: Web Environment',
        'Natural Language :: Russian',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
    ],
    packages=find_packages(),
    install_requires=[
        'django-classy-tags >=0.3,<=0.9.0',
        'django-mptt==0.9.*',
        'django==1.11.*'
    ],
    include_package_data=True,
    zip_safe=False,
)
