from setuptools import find_packages, setup

setup(
    name='duckcord.py',
    description='discord.py dataclasses but with more duck-typing.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/tonywu7/duckcord.py',
    author='@tonyzbf',
    author_email='tony@tonywu.org',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries',
    ],
    packages=find_packages(),
    keywords='discord discord.py',
    python_requires='>=3.9',
    install_requires=[
        'discord.py',
        'attrs',
    ],
    tests_require=[
        'pytest',
    ],
)
