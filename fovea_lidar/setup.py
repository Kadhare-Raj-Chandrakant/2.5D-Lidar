from setuptools import find_packages, setup

package_name = 'fovea_lidar'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/fovea.launch.py']),
        ('share/' + package_name + '/config', ['config/params.yaml']),
        ('share/' + package_name + '/rviz', ['rviz/fovea.rviz']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='User',
    maintainer_email='user@example.com',
    description='Foveated LiDAR Perception with Risk-Aware Adaptive ROI',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'fovea_node = fovea_lidar.node:main',
            'synthetic_publisher = fovea_lidar.synthetic_publisher:main',
        ],
    },
)