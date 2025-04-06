from setuptools import setup, find_packages

setup(
    name='Sentinel_Eye',
    version='0.1.0',
    author='Jikson Jimmy',
    author_email='jiksonjimmy@gmail.com',
    description='This project centers on developing an intelligent drone-based surveillance system '
                'designed to enhance public safety through the real-time detection of wanted criminals '
                'and potential weapons, accidents.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/JIKS31/Sentinel-Eye.git',
    packages=find_packages(),
    install_requires=open('requirements.txt').read().splitlines(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)
