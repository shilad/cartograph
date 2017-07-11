var CG = CG || {};
var storeddotslayer = [];
var storedcurveslayer = [];

/* showEdgesCityTooltip is responsible for rendering the edges and dots, as well as calling point.json.
*/
CG.showEdgesCityTooltip = function (mapX, mapY, properties) {
        var id = properties.id;
        var relatedPoints = '../point.json?id=' + id;

        $.getJSON(relatedPoints, function (data) {
            //Removes any dots or curves from the map
            CG.map.removeLayer(storeddotslayer);
            CG.map.removeLayer(storedcurveslayer);
            var storeddots = [];


            //Sets the marker to be a small black dot
            var smallMarker = L.icon({
                iconUrl: 'images/blackDot.png',
                iconSize: [10,10]
            });

            //Initializes coords to an empty array. coords stores the id, name and location of the src and its dests
            coords = [];

            //Loops over the data to create the markers of the src and its dest, as well as push them to coords
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

            drawCurves(linkPairArray);

        });

}

function drawCurves(linkPairArray){
                //Creates a json file from the link pair array. It stores the edges between the src and its dests
                json = [];

                var storedcurves = [];

                for (var i=0; i<linkPairArray.length-1; i+=2){
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

                //Calls the mingling algorithm
                var bundle = new Bundler();
                bundle.setNodes(json);
                bundle.buildNearestNeighborGraph();
                bundle.MINGLE();


                var edgeHoverStyle =   {weight: 4,
                                opacity: 0.95,
                                smoothFactor: 1,
                                attribution: 'edge'};

                var edgeNeutralStyle = {
                                weight: 1,
                                opacity: 0.3,
                                smoothFactor: 1,
                                attribution: 'edge',
                                color:'#666'};

                /*
                The code below renders the graph. It first sets the variable edges to an array of arrays that
                contain Graph.Node objects. These arrays either represent an edge between two specific nodes (ex:
                "Movie -> Sound effect") or represent a merged edge (ex: "3 4988-3 19150-3 343-3 442" merges 4 edges
                into a single edge). It then loops over each e in edges and draws the appropriate curves/lines. To do
                this, it sets the starting position to the x,y of a destination node and moves there. Then, if e
                contains more than 3 Graph.Node objects, it creates a bezier curve. Otherwise, it draws a straight
                line to the source node. After the graph is rendered, hovering effects are added, so that a user can
                view the source and destination of a edge they are hovering over.
                */

                bundle.graph.each(function(node) {
                    var edges = node.unbundleEdges(1);
                    var pct = 1 || 0,
                         i, l, j, n, e, pos, midpoint, c1, c2, start, end;


                    for (i = 0, l = edges.length; i < l; ++i) {

                        e = edges[i];
                        //console.log(e)
                        start = e[0].unbundledPos;
                        var line = ['M', start];
                        midpoint = e[(e.length - 1) / 2].unbundledPos;
                        if (e.length > 3) {
                            c1 = e[1].unbundledPos;
                            c2 = e[(e.length - 1) / 2 - 1].unbundledPos;
                            end = $lerp(midpoint, c2, 1 - pct);
                            line.push('C', c1, c2, end);
                            c1 = e[(e.length - 1) / 2 + 1].unbundledPos;
                            c2 = e[e.length - 2].unbundledPos;
                            end = e[e.length - 1].unbundledPos;

                            if (1 - pct) {
                                //line to midpoint + pct of something
                                start = $lerp(midpoint, c1, 1 - pct);
                                line.push('L', start);
                             }

                            line.push('C', c1, c2, end);
                           // line.push('Z');# Y U NOT WORK??????
                            } else {
                                end = e[e.length -1].unbundledPos;
                                line.push('L', end);

                            }
                        var newCurve = L.curve(line, edgeNeutralStyle);
                        newCurve.bindPopup(e[0]['node']['name']);
                        storedcurves.push(newCurve);

                    }
                });
                storedcurveslayer = L.layerGroup(storedcurves);
                storedcurveslayer.eachLayer(function (layer) {

                    layer.on('mouseover', function(e){
                            e.target.setStyle(edgeHoverStyle);
                            layer.openPopup(e.latlng);
                    });
                    layer.on('mouseout', function(e){
                            e.target.setStyle(edgeNeutralStyle);
                            layer.closePopup();
                    });
                })
                CG.map.addLayer(storedcurveslayer);

                return(storedcurveslayer)
}

function $lerp(a, b, delta) {
    return [ a[0] * (1 - delta) + b[0] * delta,
             a[1] * (1 - delta) + b[1] * delta ];
}
