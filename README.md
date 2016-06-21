# Procedural Map Generation
Note: This architecture is based off of the stack designed on https://switch2osm.org/serving-tiles/. For reference, the original install instructions (which are quite out of date in a number of ways) are located [here] (https://switch2osm.org/serving-tiles/manually-building-a-tile-server-14-04/). 

## Setup
### Install Virtualbox and Ubuntu. 
The instructions [here](http://www.engadget.com/2009/09/07/how-to-set-up-ubuntu-linux-on-a-mac-its-easy-and-free/) should be helpful. But you want to have at least 4GB of ram and 15-25GB of storage. For the actual server machine, we may want to actually be running Ubuntu, rather than having a virtual instance. I'm going to assume the username is "research" in this documentation, but that's an easy fix if we want to change it.
### Dependancy laundry list
Here's a dependancy laundry list that consists of things we want and things that are good to have:
```
sudo apt-get install libboost-all-dev subversion git-core tar unzip wget bzip2 build-essential autoconf libtool libxml2-dev libgeos-dev libgeos++-dev libpq-dev libbz2-dev libproj-dev munin-node munin libprotobuf-c0-dev protobuf-c-compiler libfreetype6-dev libpng12-dev libicu-dev libgdal-dev libcairo-dev libcairomm-1.0-dev apache2 apache2-dev libagg-dev liblua5.2-dev ttf-unifont lua5.1 liblua5.1-dev libgeotiff-epsg node-carto libtiff5-dev:i386 libtiff5-dev
```
### Set up your source directory
This is where the majority of this code will live.
```
mkdir ~/src
cd ~/src
```

## Setting Up Our Pipeline
### Download our repo!
```
git clone https://github.com/Bboatman/proceduralMapGeneration.git
cd proceduralMapGeneration/
```
### Mapnik
We need our good friend Mapnik in order draw our tiles and maps, and in order to get mapnik we need pip.
```
wget https://bootstrap.pypa.io/get-pip.py
sudo python2.7 get-pip.py
sudo pip2.7 install mapnik
```
### Dependancies! 
We need a few things to work with this library, so install them now.
```
sudo pip install geojson
sudo pip install scipy
sudo pip install numpy
sudo pip install matplotlib # we should probably remove this dependancy but Jaco.....
```
### Set up tiles directory
We need a directory to save the tiles in, so in order to do that you should
```
sudo mkdir /var/www/html/tiles
```

## Running our pipeline, generating tiles!
### Generate tiles
```
cd ~/src/proceduralMapGeneration/
sudo python mapGenerator.py
cd ..
```

## mod_tile and renderd
### get mod_tile
Tile serving for our project happens with mod_tile and renderd, which were built by the kind folks at openstreetmaps to run an apache server on top of mapnik images. I'll be including versions of the config files I manually modded but the architecture is solid.
```
git clone git://github.com/openstreetmap/mod_tile.git
cd mod_tile
sudo apt-get install libmapnik-dev
./autogen.sh
./configure
make
sudo make install-mod_tile
sudo ldconfig
```

## Apache webserver
### renderd.conf
Now we have to edit some configurations to be able to run the server. In this folder I have copies of the conf files that you're going to end up wanting to change. Replace the entire renderd.conf with the content of the version I have included in the installDocuments/ folder of this project.
### set up renderd
This assumes that the username of your ubuntu enviornment is "research".
```
sudo mkdir /var/run/renderd
sudo chown research /var/run/renderd
sudo mkdir /var/lib/mod_tile
sudo chown research /var/lib/mod_tile
```
### mod_tile.conf
Now we need to tell our webserver about mod_tile, so we need to create and edit /etc/apache2/conf-available/mod_tile.conf and add the following line to it:
```
LoadModule tile_module /usr/lib/apache2/modules/mod_tile.so
```
### 000-default.conf
Replace the entire content of /etc/apache2/sites-available/000-default.conf with the text of the "000-default.conf" file I have included in the installDocuments/ folder of this project.
### configure apache
We need to tell Apache that we've added the new module. **NOTE:** The second command will get an error but we should still be ok.
```
sudo a2enconf mod_tile
sudo service apache2 reload
```
## Drawing the map client-side
### map.html
Create a file called /var/www/html/map.html with the content of the "map.html" I have included in the installDocuments/ folder of this project.

## Run the server!
### run renderd
To run the server, you need to run renderd.
```
cd ~/src/mod_tile/
./renderd -f -c ~/src/mod_tile/renderd.conf
```
### Take a look!
Then open up your friendly neighborhood web browser and point it at [http://localhost/map.html](http://localhost/map.html) ...and you should have a map!

## Know Oddities

### If you get an error when trying to run again with renderd.sock...
Try remaking the renderd directory
```
sudo mkdir /var/run/renderd
sudo chown research /var/run/renderd
```
### Also make sure to...
Link the renderd.conf file to another place that some things might end up looking for it...
```
cd ~/src/mod_tile/
sudo ln renderd.conf /usr/local/etc/renderd.conf
```
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

# UPDATE: Server change to TileStache 
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
Install PIP if you don't already have it! 
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
Fix some ubuntu specific Python Image Library module issues. 
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
### Link the mod_python and TileStache to the web server. 
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
If you don't have a tiles folder, create one now. 
```
mkdir /var/www/html/tiles
```
Reboot your server. 
```
reboot
```
## Make a few file changes. 
Update tilestache.cfg
```
cd /etc/TileStache/
sudo gedit tilestache.cfg
```
Edit the file to work with our project. 
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

## Test the server.
Run on the command line:
```
./scripts/tilestache-server.py
```
To check if TileStache is running, go to http://localhost:8080. If the message "TileStache bellows hello." appears then the server is functioning properly. 

To view your map go to http://localhost:8080/map/preview.html. 
