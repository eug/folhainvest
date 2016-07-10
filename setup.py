# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='folhainvest',
      version='0.1',
      description='Um wrapper de acesso ao FolhaInvest',
      url='https://github.com/eug/folhainvest',
      author='Eugênio Cabral',
      author_email='eugfcl@gmail.com',
      license='MIT',
      packages=['folhainvest'],
      install_requires=[
        'requests',
        'beautifulsoup4'
      ],
      zip_safe=False)