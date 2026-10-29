from setuptools import find_packages, setup

package_name = 'turtlebot3_factory_nav'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='P Pranav',
    maintainer_email='pranavrobotics.eng@gmail.com',
    description='Station simulator and FIFO pickup dispatcher for '
                'TurtleBot3 factory navigation using Nav2.',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'cart_patrol = turtlebot3_factory_nav.cart_patrol:main'
        ],
    },
)
