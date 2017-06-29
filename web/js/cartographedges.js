var CG = CG || {};
var storeddotslayer = [];
var storedcurveslayer = [];

 CG.showEdgesCityTooltip = function (mapX, mapY, properties) {
        var id = properties.id;
        var relatedPoints = '../point.json?id=' + id;

        var randHue = 'rgb(' + (Math.floor(Math.random() * 256))
                            + ',' + (Math.floor(Math.random() * 256))
                            + ',' + (Math.floor(Math.random() * 256)) + ')';

        var edgeHoverStyle =   {weight: 3,
                                opacity: 0.95,
                                smoothFactor: 1,
                                attribution: 'edge'};
        var edgeNeutralStyle = {color: randHue,
                                weight: 1,
                                opacity: 0.65,
                                smoothFactor: 1,
                                attribution: 'edge'};

        $.getJSON(relatedPoints, function (data) {
            CG.map.removeLayer(storeddotslayer);
            CG.map.removeLayer(storedcurveslayer);

            storeddots = [];
            storedcurves = [];

            var smallMarker = L.icon({
            iconUrl: 'images/blackDot.png',
            iconSize: [10,10]
            });

            coords = [];
            names = [];

            data[id].forEach(function (linkInfo) {
                  var x = linkInfo.data.loc[0];
                  var y = linkInfo.data.loc[1];
                  marker = L.marker([x, y], {icon: smallMarker});
                  storeddots.push(marker);
                  coords.push([linkInfo.data.id, linkInfo.data.name, [x, y]]);
            });
            storeddotslayer = L.layerGroup(storeddots);
            CG.map.addLayer(storeddotslayer);


            var linkPairArray = [];
            for(i=1; i < coords.length; i++) {
                linkPairArray.push(coords[0]);
                linkPairArray.push(coords[i]);
            }


            function drawCurves(){
                json = [];
                for (var i=0; i<linkPairArray.length-2; i+=2){

                    var pointA = linkPairArray[i][2]; //source x,y
                    var pointB = linkPairArray[i+1][2]; //dest x,y

                    json.push({
                    "id": linkPairArray[i][0] + " " + linkPairArray[i+1][0], //source + dest id
                    "name": linkPairArray[i][1] + " -> " + linkPairArray[i+1][1], //source + dest name
                    "data": {
                        "coords": [
                            pointA[0], pointA[1], pointB[0], pointB[1]
                                  ]
                            }
                    });

                }

                var bundle = new Bundler();
                bundle.setNodes(json);
                bundle.buildNearestNeighborGraph();
                bundle.MINGLE();

                /*
                The function below renders the graph. It first sets the variable edges to an array of arrays that contain Graph.Node objects. These arrays either represent an edge between two specific nodes (ex: "Movie -> Sound effect")
                or represent a merged edge (ex: "3 4988-3 19150-3 343-3 442" merges 4 edges into a single edge). It then loops over each e in edges and draws the appropriate curves/lines. To do this, it sets the starting position to the x,y of the destination node
                and moves to the starting position. Then, if e contains more than 3 Graph.Node objects, it creates a benzier curve. Otherwise, it draws a straight line. After the graph is rendered, hovering effects are added, so that a user can view the source and
                destination of a edge they are hovering over.
                */

                bundle.graph.each(function(node) {
                    var edges = node.unbundleEdges(1);
                    for (i = 0, l = edges.length; i < l; ++i) {
                        e = edges[i];
                        start = e[0].unbundledPos;
                        var line = ['M', start];
                        if (e.length > 3) {
                            c1 = e[1].unbundledPos;
                            c2 = e[(e.length - 1) / 2 - 1].unbundledPos;
                            end = [c2[0], c2[1]]

                            line.push('C', c1, c2, end);
                            c1 = e[(e.length - 1) / 2 + 1].unbundledPos;
                            c2 = e[e.length - 2].unbundledPos;
                            end = e[e.length - 1].unbundledPos;

                            start = [c1[0], c1[1]]
                            line.push('L', start);

                            line.push('C', c1, c2, end);
                            } else {
                                end = e[e.length -1].unbundledPos;
                                line.push('L', end);
                            }
                        var newCurve = L.curve(line, edgeNeutralStyle);
                        storedcurves.push(newCurve);
                        newCurve.bindPopup(e[0].node.name);

                        newCurve.on('mouseover', function(e){
                        e.target.setStyle(edgeHoverStyle);
                        newCurve.openPopup();
                        });
                        newCurve.on('mouseout', function(e){
                        e.target.setStyle(edgeNeutralStyle);
                        newCurve.closePopup();
                        });
                    }
                });
                storedcurveslayer = L.layerGroup(storedcurves);
                CG.map.addLayer(storedcurveslayer);
            }
            drawCurves();

        });

 }