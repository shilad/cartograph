# Procedural Map Generation
Note: This architecture is based off of the stack designed on https://switch2osm.org/serving-tiles/. For reference, the original install instructions (which are quite out of date in a number of ways) are located [here] (https://switch2osm.org/serving-tiles/manually-building-a-tile-server-14-04/). 

# Machine Setup
## Install Virtualbox and Ubuntu. 
The instructions [here](http://www.engadget.com/2009/09/07/how-to-set-up-ubuntu-linux-on-a-mac-its-easy-and-free/) should be helpful. But you want to have at least 4GB of ram and 15-25GB of storage. For the actual server machine, we may want to actually be running Ubuntu, rather than having a virtual instance. I'm going to assume the username is "research" in this documentation, but that's an easy fix if we want to change it.

## Dependency laundry list
Here's a dependency laundry list that consists of things we want and things that are good to have:
```
sudo apt-get install libboost-all-dev subversion git-core tar unzip wget bzip2 build-essential autoconf libtool libxml2-dev libgeos-dev libgeos++-dev libpq-dev libbz2-dev libproj-dev munin-node munin libprotobuf-c0-dev protobuf-c-compiler libfreetype6-dev libpng12-dev libicu-dev libgdal-dev libcairo-dev libcairomm-1.0-dev apache2 apache2-dev libagg-dev liblua5.2-dev ttf-unifont lua5.1 liblua5.1-dev libgeotiff-epsg node-carto libtiff5-dev:i386 libtiff5-dev
```
## Set up your source directory
This is where the majority of this code will live.
```
mkdir ~/src
cd ~/src
```

# Repo Setup
## Download our repo!
```
git clone https://github.com/Bboatman/proceduralMapGeneration.git
cd proceduralMapGeneration/
```
## Mapnik
We need our good friend Mapnik in order draw our tiles and maps, and in order to get mapnik we need pip.
```
wget https://bootstrap.pypa.io/get-pip.py
sudo python2.7 get-pip.py
sudo pip2.7 install mapnik
```
## Dependencies! 
We need a few things to work with this library, so install them now.
```
sudo pip install geojson
sudo pip install scipy
sudo pip install numpy
sudo pip install matplotlib # we should probably remove this dependancy but Jaco.....
```
## Set up tiles directory
We need a directory to save the tiles in, so in order to do that you should
```
sudo mkdir /var/www/html/tiles
```
Take ownership of the tiles directory to access them...
```
sudo chown -R research.research /var/www/html/tiles/
```
# Web Server Setup
## Apache webserver

### 000-default.conf
Replace the entire content of /etc/apache2/sites-available/000-default.conf with the text of the "000-default.conf" file I have included in the installDocuments/ folder of this project.
### configure apache
Restart the server so it knows you've made changes.  **NOTE:**  Will result in an error but we should still be ok.
```
sudo service apache2 reload
```

## Installing TileStache
Adapted from [this axis maps blog post.](http://www.axismaps.com/blog/2012/01/dont-panic-an-absolute-beginners-guide-to-building-a-map-server/)

### Install mod_python 
This interface is how TileStache communicates with the web server. 
```
sudo apt-get install libapache2-mod-python
```
Then restart the web server. 
```
sudo /etc/init.d/apache2 restart
```
### Install some dependencies. 
Packages that help with the install/required python tools and libraries.
```
cd /etc
sudo apt-get install curl
sudo apt-get install git-core
sudo apt-get install python-setuptools
sudo apt-get install aptitude
sudo aptitude install python-dev
sudo apt-get install libjpeg8 libjpeg62-dev libfreetype6 libfreetype6-dev
```
You probably have pip at this point, but if you don't:
```
curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
sudo python get-pip.py
```
Install required python modules. 
```
sudo pip install -U werkzeug
sudo pip install -U simplejson
sudo pip install -U modestmaps
```
Python Image Library doesn't play nice with Ubuntu, add some symlinks to fix that: 
```
sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib
sudo ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib
sudo ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib
```
Install pillow.  
```
sudo pip install -U pillow
```
Clone the TileStache repository from GitHub. 
```
sudo git clone https://github.com/migurski/TileStache.git
```
Install TileStache globally. 
```
cd TileStache/
sudo python setup.py install
```
### Link mod_python and TileStache to the web server. 
Open the apache configuration file to edit it. 
```
sudo nano /etc/apache2/httpd.conf
```
Add the following to the conf file. 
```
<Directory /var/www/html/tiles>
  AddHandler mod_python .py
  PythonHandler TileStache::modpythonHandler
  PythonOption config /etc/TileStache/tilestache.cfg
</Directory>
```
Reboot your server. 
```
reboot
```
### Edit config files
Update tilestache.cfg
```
cd /etc/TileStache/
sudo gedit tilestache.cfg
```
Edit the file to work with our project. (NOTE: update this with a file in setup files so that the code doesn't have to go in the readme - it will be getting updated regularly) 
```
{
  "cache":
  {
    "name": "Disk",
    "path": "/tmp/stache"
  },
  "layers": 
  {
    "map":
    {
        "provider": {"name": "mapnik", "mapfile": "/home/research/src/proceduralMapGeneration/map.xml"},
        "projection": "spherical mercator"
        "metatile": {"rows": 6, "columns": 6, "buffer":64}
    }
  }
}
```
Edit an outdated function call. Note that there are many Mapnik.py versions. Open the one listed below.
```
cd /usr/local/lib/python2.7/dist-packages/TileStache-1.50.1-py2.7.egg/TileStache/
sudo gedit Mapnik.py
```
On line 154 in the renderArea() function, change fromstring() to frombytes().


# Making the Map

## Python
TOOD: To be updated with the details of how to use the new workflow/pipeline

##TileStache
To actually generate the map tiles from the xml, you need to run TileStache.
```
cd /etc/TileStache/
./scripts/tilestache-server.py
```

To check if your server is running, open a browser to localhost:8080. If it says "TileStache bellows hello.", you're all good - you should be able to go view the map. If not, something has gone wrong.  

Note that if you change things that affect the way the tiles look (basically, anything that affects the xml), to overwrite the tiles in the cache you have to remove it and rerun the TileStache server:
```
rm -rf /tmp/stache
cd /etc/TileStache/
./scripts/tilestache-server.py
```

### Take a look!
Then open up your friendly neighborhood web browser and point it at [http://localhost/Leaflet/leafletmap2.html](http://localhost/Leaflet/leafletmap2.html) ...and you should have a map!

# Known Fixes

Take ownership of the tiles directory to access them...
```
sudo chown -R research.research /var/www/html/tiles/
```
Restart the apache server
```
sudo service apache2 reload
```
If you get an error saying the server is offline, try
```
sudo service apache2 start
```


