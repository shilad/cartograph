# Procedural Map Generation
This is the code behind [our map of Wikipedia](http://nokomis.macalester.edu/cartograph/static/index.html), which maps Wikipedia articles into an imaginary geographical space based on their relatedness to each other. If you want to be able to generate your own maps, read on!

#Requirements
- These instructions are written for a Mac system. They should be pretty easily portable to Linux/Windows with appropriate adjustment of the command line stuff, but we haven't tested it on those systems yet, so some things might be different.
- You'll need your own vectorized dataset and some kind of popularity/weighting measure for it (for Wikipedia, ours was a combination of page views and page rank). Unfortunately, you can't run the code on our Wikipedia dataset - there are ~10GB of it so it doesn't fit on Github :( If you'd like to play around with the full Wikipedia dataset, open an issue and we'll do our best to get you set up.
- Python 2.7, which you can install [here](https://www.python.org/downloads/) if you don't already have it, and your text editor of choice

#Getting started

###Github
Fork and clone the repo:
```
git clone https://github.com/shilad/cartograph
cd cartograph/
```
###Postgres
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

#Getting your data set up
As long as your data is in the proper format, the pipeline should be able to handle it just fine. Unfortunately, it's a pretty specific format, so be careful. 

##Data format

The basics: Your data need to be vectorized (think word2vec) and have some kind of popularity/weighting score attached to each individual data point. They'll be stored in tsvs (tab-separated files), which are pretty easy to create if you don't have them already. 

###Files you need
I'll number the files you need so that you can reference them later. 

1. A file of all your vectors, one per line, with individual numbers separated by tabs. The first line of this should just be a list of numbers from 1 to the length of your vectors (ours goes from 1 to 100). The line numbers in this file will eventually become the unique id numbers for each vector/item (id numbers are arbitrary and meaningless, but help with data tracking and lookup). Here are the first two lines of our vecs file so you can see:
```
1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	32	33	34	35	36	37	38	39	40	41	42	43	44	45	46	47	48	49	50	51	52	53	54	55	56	57	58	59	60	61	62	63	64	65	66	67	68	69	70	71	72	73	74	75	76	77	78	79	80	81	82	83	84	85	86	87	88	89	90	91	92	93	94	95	96	97	98	99	100
-0.07138634	-0.08672774	-0.013411164	0.07870448	0.04251623	0.11026025	0.008073568	0.044899702	0.05322492	-0.13140923	0.077965975	-0.12912643	0.073434114	-0.053325653	-0.09941709	0.08749974	0.060241103	-0.124527335	-0.014015436	0.033687353	0.1030426	-0.012437582	0.004548788	-0.061617494	0.1483283	0.0057908297	-0.13584042	0.15024185	-0.037984252	-0.12157321	0.09136045	0.020964265	0.016398907	-0.081725836	-0.036406517	-0.15739226	-0.05564201	0.056917787	0.06571305	0.2697841	0.19257343	0.11049521	0.06296027	0.01737237	0.083135724	-0.06151676	-0.22469974	-0.14886552	0.05225146	-0.060946107	0.049633026	-0.15782869	-0.12573588	-0.015895367	0.012135506	0.043959737	0.03600359	0.034795165	-0.04003203	-0.007905722	0.08175945	0.06722367	-0.017473102	0.009483457	0.04708171	0.16971242	0.08944678	-0.0101213455	0.055675507	0.05460131	0.17296863	0.19190204	-0.13852596	-0.114959955	-0.03523159	-0.014250398	0.114590645	0.0142169	-0.04355693	-0.19052565	0.07115126	-0.28525978	-0.027846217	-0.07007706	-0.14977187	-0.022709966	0.056917787	-0.025865555	0.06698871	0.09790647	-0.0046830177	0.11667204	0.03761494	-0.0047165155	0.17921269	0.07742882	-0.14728767	-0.14275575	-0.073064804	0.14440072
```

2. A file of all your names/titles, one per line. There should be two columns, one callled "index" and one called "name". "Index" should correspond to the line number of the vectors file (i.e. they should be in the same order), and "name" is the title of your item/point. Again, everything should be tab-separated. Here are the first few lines of our names file:
```
index	name
1	Kat Graham
2	Cedi Osman
3	List of Chicago Bulls seasons
4	Alabama
5	An American in Paris
```

3. A file of all your popularities/weights, one per line. This should have two tab-separated columns, one of which contains the name/title of the point, and the second of which contains the score. This file does not need a heading. It also does not need to be in the same order as the other two. Here's our popularity file, which measures the popularity of Wikipedia articles using a weighted combination of page views and page rank.
```
2014–15 West Ham United F.C. season	6.038550978007928E-6
The Return of Superman (TV series)	8.09840661109975E-5
Bethany Mota	9.359317492029514E-5
Elfrid Payton (basketball)	1.3807395228814057E-5
Dothraki language	5.198423874878717E-5
List of edible molluscs	4.500109212570877E-6
```

4. (OPTIONAL) Region names. This is probably something you'll add after you see your data for the first time. It's the file that creates the region labels ("Physics & Maths", "Politics & Geography", etc. on our map). It has a header - one column is "cluster_id" and the other is "label", and is tab-separated, like all of our data files. If you leave this one off, the code will just number your regions on the map.
```
cluster_id	label
0	India
1	History & Geography
2	Politics & Economics
3	Physics & Maths
```

5. (OPTIONAL) t-sne cache. This is a cache of your embedding, a three-column tsv file with an header "index x y", which represents the index/id number of the point and then its x/y coordinates after embedding. Caching this file maintains a consistent embedding and also speeds up the run-time of the process. 
```
index	x	y
91139	1.29488570272	6.27138495391
40135	20.3768748707	-9.27980846186
89370	-6.43982634997	-4.71632724942
89371	-2.57335603135	25.4092678524
```

##Config
This is the top of data/conf/defaultconfig.txt, which you'll need to edit to correspond to your data files. You'll also have to create a couple of directories for your files to live in. 
```
[DEFAULT]
dataset: dev_en
baseDir: ./data/%(dataset)s
generatedDir: %(baseDir)s/tsv
mapDir: %(baseDir)s/maps
geojsonDir: %(baseDir)s/geojson
externalDir: ./data/labdata/%(dataset)s

[ExternalFiles]
vecs_with_id: %(externalDir)s/vecs.tsv
names_with_id: %(externalDir)s/names.tsv
popularity: %(externalDir)s/popularity.tsv
region_names: %(externalDir)s/region_names.tsv
article_embedding = %(externalDir)s/tsne_cache.tsv
```
###Directory setup and config
This is the only part of this file you should need to change - the rest will either be generated based on your data or is constant.

First up, the directories.
1. In data/labdata, create a new file and call it something relevant to your dataset. Ours is called dev_en (development english)
2. Put all your data files from Data Format into this folder
3. Change the "dataset" line in the config file to point to your folder rather than dev_en
4. One more conf file to create - create a file called conf.txt and put it in the base directory (cartograph). It doesn't need to do anything, but it won't work if it's blank, so just add an arbitary heading like so: 
```
[Heading]
```

Next, external files: they're pretty easy - they go in the order described above in Data Format. Just pop in the title of your file after the last / in the filepath - so, for example, if you called your vectors file myvectors.tsv, you would change the file to read
```
vecs_with_id: %(externalDir)s/myvectors.tsv
```
Do the same for the other four files. If you don't have the last two, it's okay to leave them - the pipeline is set up to catch that and work around it. 


###Postgres database
One more step for configuration - you have to create a postgres database to hold your data. Open up a terminal window and create a database with the title mapnik_yourdataset. Ours is called mapnik_dev_en.
```
$ createdb mapnik_yourdataset
```


#Dependencies galore!
You'll have to install a bunch of dependencies in order to get started. Most of them are pretty quick, with the exception of pygsgp, which takes about half an hour - start it installing and go get a snack or catch some Pokemon or something. 

These instructions all say pip2.7, because sometimes pip doesn't like to install things in the right place if you have Python 3, but if you only have Python 2.7, you can just say pip. 

```
pip2.7 install luigi
pip2.7 install geojson
pip2.7 install shapely
pip2.7 install mapnik
pip2.7 install lxml
pip2.7 install sklearn
pip2.7 install Cython
pip2.7 install numpy
pip2.7 install tsne
pip2.7 install psycopg2
pip2.7 install annoy
pip2.7 install werkzeug
pip2.7 install marisa-trie
pip2.7 install TileStache 
```

You have to revert your Pillow version (Pillow is automatically installed by TileStache) because it doesn't play nice with the tile generation
```
pip2.7 install -I Pillow==2.9.0
```


#Test the server
Open a browser window and go to localhost:8080. If it says "TileStache bellows hello", congrats! Your server is working properly.

#Run the pipeline!
This runs a luigi script that works through workflow.py, checking to see if any tasks have already been completed and skipping those (so you don't have to rerun the clustering algorithm/denoising/etc every time). It will automatically update if code marked as required has been changed. The end product of this script is an xml file that represents the map. 

```
./build.sh
```

##Run the server!
The last step is to run the TileStache server, which takes your map xml and turns it into tiles that can then be served. This part also handles setting up things like the search function.

```
python run-server.py
```

If you go to localhost:8080/static/index.html, you'll hit the landing page, and you can click through to go to your map, or you can just go directly to localhost:8080/static/mapPage.html. The html/javascript is set up for wikipedia, but you should have a functional map! 





