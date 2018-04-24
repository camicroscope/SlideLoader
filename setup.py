try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='SlideLoader',
      version='0.0.1',
      description='Role Based Access Control (RBAC) for mysql',
      author='Ryan Birmingham',
      author_email='birm@rbirm.us',
      url='http://rbirm.us',
      classifiers=['Development Status :: 2 - Pre-Alpha',
                   'Programming Language :: Python :: 3.6',
                   'Intended Audience :: Healthcare Industry',
                   'Programming Language :: Python :: 2.7',
                   'Topic :: Scientific/Engineering :: Medical Science Apps.',
                   'License :: OSI Approved :: Apache Software License'],
      long_description=open('README.md', 'r').read(),
      packages=['SlideLoader'],
      entry_points = {
        'console_scripts': ['SlideLoad=SlideLoader.__main__'],
        }
)
