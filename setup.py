from setuptools import setup, find_packages
from flan.settings import __VERSION__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="flan",
    version=__VERSION__,
    author="Bret Lowery",
    author_email="bret.lowery@gmail.com",
    description="Create (very good) fake NCSA Combined Log Format access.log files for testing log-consuming systems like Splunk, ActiveMQ, Amazon MQ, RabbitMQ, Kafka, FluentD, Flume, Pulsar, Nifi...",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bretlowery/flan",
    packages=find_packages(),
    install_requires=[
        'python-dateutil>=2.8.0',
        'ua-parser>=0.8.0',
        'user-agents>=2.0',
        'numpy>=1.16.4.0',
        'service>=0.6.0',
        'PyYAML>=5.1.2',
        'boto>=2.49.0',
        'confluent_kafka>=1.1.0',
        'fluent-logger>=0.9.3',
        'pyspark>=2.4.3',
        'splunk-sdk>=1.6.6',
        'stomp.py>=4.1.22',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
          'console_scripts': [
              'flan = flan.__main__:main'
          ]
      },
)
