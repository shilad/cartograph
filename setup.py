#
# Packages needed on CentOS7:
# libxml2
# libxml2-devel
# gcc libxml2 libxml2-devel libxslt libxslt-devel python-devel
# geos
# geos-devel
# atlas-devel
# sudo yum install freetype-devel
# sudo yum install libpng-devel
# sudo yum install postgresql-devel
# sudo yum install blas-devel lapack-devel gcc-c++ 
# sudo yum -y install gcc gcc-c++ numpy python-devel scipy
# sudo ln -s /usr/lib64/atlas/libsatlas.so /usr/lib/libcblas.so
# sudo yum install python-devel libjpeg-devel zlib-devel
# sudo yum install cmake qt-devel
#
# easy_install numpy scipy
# pip install python-daemon Cython
# export PATH=$PATH:/usr/pgsql-9.4/bin/
#


from setuptools import setup

setup(name='cartograph',
      version='0.1',
      description='The Cartograph Non-Spatial Map Framework',
      url='https://github.com/Bboatman/proceduralMapGeneration',
      author='Shilad Sen and many amazing others',
      author_email='ssen@macalester.edu',
      license='MIT',
      packages=[],
      install_requires=[
          'geojson',
          'luigi',
	  'lxml',
	  'mapnik',
	  'matplotlib',
	  'pygsp',
	  'psycopg2',
	  'python-daemon',
	  'pyyaml',
	  'scikit-learn',
	  'shapely',
	  'tsne',
	  'cython',
	  'Tilestache',
      ],
      zip_safe=False)
