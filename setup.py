from setuptools import setup
from flan.flan import __VERSION__

setup(name='flan',
      version=__VERSION__,
      packages=['flan'],
      entry_points={
          'console_scripts': [
              'flan = flan.__main__:main'
          ]
      },
      )
