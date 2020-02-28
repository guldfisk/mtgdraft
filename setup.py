from setuptools import setup
import os


def package_files(directory):
    paths = []
    for path, directories, file_names in os.walk(directory):
        for filename in file_names:
            paths.append(os.path.join('..', path, filename))
    return paths


extra_files = package_files('draft')


setup(
    name='draft',
    version='1.0',
    packages=['draft'],
    package_data={'': extra_files},
    install_requires = [
        'yeetlong @ https://github.com/guldfisk/yeetlong/tarball/master#egg=yeetlong-1.0',
        'ring @ https://github.com/guldfisk/ring/tarball/master#egg=ring-1.0',
        'mtgorp @ https://github.com/guldfisk/mtgorp/tarball/master#egg=mtgorp-1.0',
        'magiccube @ https://github.com/guldfisk/magiccube/tarball/master#egg=magiccube-1.0',
        'websocket',
    ],

)