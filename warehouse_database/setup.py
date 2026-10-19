from setuptools import setup
from glob import glob
package_name = 'warehouse_database'
setup(name=package_name, version='0.1.0', packages=[package_name],
      data_files=[('share/ament_index/resource_index/packages', ['resource/' + package_name]),
                  ('share/' + package_name, ['package.xml']),
                  ('share/' + package_name + '/config', glob('config/*.yaml'))],
      install_requires=['setuptools', 'PyYAML'], zip_safe=True)
