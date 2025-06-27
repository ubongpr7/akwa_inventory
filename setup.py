from setuptools import setup, find_packages

setup(
    name='akwa_inventory',
    version='0.1.1',  
    packages=find_packages(where='.'),
    include_package_data=True,
    install_requires=[
        'Django>=4.0',
        'djangorestframework>=3.13',
        'web3>=6.0',
        'celery>=5.2',
        'psycopg2-binary',
    ],
    author='Ubong Prosper',
    email='ubongpr7@gmail.com.com',  
    description='Reusable inventory management for microservices',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/ubongpr7/akwa_inventory',  
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: MIT License',  
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.8',
)