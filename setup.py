from setuptools import setup

setup(name='flan',
      version='0.0.11',
      packages=['flan'],
      entry_points={
          'console_scripts': [
              'flan = flan.__main__:main'
          ]
      },
      )