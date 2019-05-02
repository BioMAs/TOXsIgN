import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'pyramid_beaker',
    'waitress',
    'pymongo==2.7.2',
    'py-bcrypt',
    'gunicorn',
    'gevent',
    'future',
    'PyJWT',
    'bcrypt',
    'velruse',
    'elasticsearch',
    'simplejson'
    'xlrd'
    ]

setup(name='chemsign',
      version='1.0.0',
      description='Chemsign',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Olivier Sallou',
      author_email='olivier.sallou@irisa.fr',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="chemsign",
      entry_points="""\
      [paste.app_factory]
      main = chemsign:main
      """,
      )
