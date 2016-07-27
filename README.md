# Procedural Map Generation
This is the code behind [our map of Wikipedia](http://nokomis.macalester.edu/cartograph/static/index.html), which maps Wikipedia articles into an imaginary geographical space based on their relatedness to each other. If you want to be able to generate your own maps, read on!

##Requirements
- These instructions are written for a Mac system. They should be pretty easily portable to Linux/Windows with appropriate adjustment of the command line stuff, but we haven't tested it on those systems yet, so some things might be different.
- You'll need your own vectorized dataset and some kind of popularity/weighting measure for it (for Wikipedia, ours was a combination of page views and page rank). Unfortunately, you can't run the code on our Wikipedia dataset - there are ~10GB of it so it doesn't fit on Github :( 
- Python 2.7, which you can install [here](https://www.python.org/downloads/) if you don't already have it, and your text editor of choice

##Getting started

Fork and clone the repo:
```
git clone https://github.com/Bboatman/proceduralMapGeneration.git
cd proceduralMapGeneration/
```

Then get postgres, which is where your data is going to live, from [here](http://postgresapp.com/). You'll need to change your bash profile in order to get it to work:
```
nano .bash_profile
```
Add this line to it (assuming you're using bash):
```
export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/latest/bin
```
Ctrl-O to save and Ctrl-X to exit

Make sure postgres is in your applications folder and then open it to start the server. 

##Getting your data set up
[TODO - EXPLAIN FORMAT DATA NEEDS TO BE IN, HOW TO EDIT CONFIG FILE, HOW TO CREATE POSTGRES DATABASE - SHILAD AND BROOKE QUESTIONS]

##Dependencies galore!
You'll have to install a bunch of dependencies in order to get started. Most of them are pretty quick with the exception of pygsgp, which takes about half an hour - it's a good thing to start installing before you go get lunch or go chasing Pokemon or something. These instructions all say pip2.7, because sometimes pip doesn't like to install things in the right place if you have Python 3, but if you only have Python 2.7, you can just say pip. 

```
pip2.7 install luigi
pip2.7 install geojson
pip2.7 install shapely
pip2.7 install mapnik
pip2.7 install lxml
pip2.7 install sklearn
pip2.7 install Cython
pip2.7 install tsne
pip2.7 install psycopg2
pip2.7 install annoy
pip2.7 install werkzeug
pip2.7 install marisa-trie
pip2.7 install TileStache 
```

You have to revert your Pillow version because it doesn't play nice with the tile generation
```
pip2.7 install -I Pillow == 2.9.0
```

##Conf files

One more conf file to create - create a file called conf.txt and put it in the base directory (proceduralMapGeneration). It doesn't need to do anything, but it won't work if it's blank, so just add an arbitary heading like so: [Heading] (you call call it whatever you want)


##Test the server
Open a browser window and go to localhost:8080. If it says "TileStache bellows hello", congrats! Your server is working properly.

##Run the pipeline!
This runs a luigi script that works through workflow.py, checking to see if any tasks have already been completed and skipping those (so you don't have to rerun the clustering algorithm every time). It will automatically update if code marked as required has been changed. The end product of this script is an xml file that represents the map. 

```
./build.sh
```

##Run the server!
The last step is to run the TileStache server, which takes your map xml and turns it into tiles that can then be served. This part also handles setting up things like the search function.

```
python run-server.py
```

Now you should have a functional map! 





