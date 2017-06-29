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

                bundle.graph.each(function(node) { //render the graph
                    var edges = node.unbundleEdges(1); //edges's an array of arrays that contain Graph.Node objects (which either represent an edge between two specific nodes or represent a merged edge)
                    for (i = 0, l = edges.length; i < l; ++i) { //loop over edges
                        e = edges[i]; //an array that contains Graph.Node objects (which either represent an edge between two specific nodes (ex: "Movie -> Sound effect") or represent a merged edge (ex: "3 4988-3 19150-3 343-3 442" merges 4 edges))
                        //the first and last item in e will always be an edge between the SAME two specific nodes (ex: both will represent "Movie -> Sound effect")
                        console.log(e);
                        start = e[0].unbundledPos; //set the starting position to the x,y of the destination node
                        var line = ['M', start]; //move to the starting position
                        if (e.length > 3) { //if e has more than 3 Graph.Node objects, you can create a benzier curve. if it's equal to three it's just the two specific nodes 3 times over and you just create a straight line
                            c1 = e[1].unbundledPos; //set the first control point to the mid unbundled position?
                            c2 = e[(e.length - 1) / 2 - 1].unbundledPos; //set the second control point to the second to last unbundled position?
                            end = [c2[0], c2[1]] //set the ending position equal to c2

                            line.push('C', c1, c2, end); //draw the benzier curve
                            c1 = e[(e.length - 1) / 2 + 1].unbundledPos; //set the first control point to the mid unbundled position?
                            c2 = e[e.length - 2].unbundledPos; //set the second control point to the second to last unbundled position?
                            end = e[e.length - 1].unbundledPos; //set the ending position to the x,y of the destination node

                            start = [c1[0], c1[1]] //set the starting position equal to c1
                            line.push('L', start); //draw a line to the starting position

                            line.push('C', c1, c2, end); //draw the benzier curve
                            } else { //otherwise, create a straight line
                                end = e[e.length -1].unbundledPos; //set the ending position to the x,y of the destination node
                                line.push('L', end); //draw a line to the ending position
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