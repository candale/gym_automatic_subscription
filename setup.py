from setuptools import setup


setup(
    name='GymSub',
    version='1.0',
    py_modules=['cli'],
    install_requires=[
        "backports.ssl-match-hostname==3.5.0.1",
        "click==6.6",
        "requests==2.9.1",
        "selenium==2.53.1",
        "six==1.10.0",
        "slackclient==1.0.0",
        "websocket-client==0.35.0",
        "wheel==0.24.0",

    ],
    entry_points='''
        [console_scripts]
        gym_sub=cli:cli
    ''',
)
