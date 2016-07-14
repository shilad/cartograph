var createMap = function(){

//=================== MAP INITIALIZATION========================//

	var map = L.map('map').setView([0, 0], 3);
  	var infobox = document.getElementById('infobox');

  // load a tile layer
  	L.tileLayer('http://localhost:8080/map/{z}/{x}/{y}.png',
    {
      maxZoom: 18,
      attribution: "WikiBrain / Sen Research Lab 2016"
    }).addTo(map);

	 var utfgrid0;
	 var utfgrid1;
	 var utfgrid2;
	 var utfgrid3;
	 var utfgrid4;
	 var utfgrid5;
	 var utfgrid6;
	 var utfgrid7;
	 var utfgrid8;
	 var utfgrid9;
	 var utfgrid10;
	 var utfgrid11;
	 var utfgrid12;
	 var utfgrid13;
	 var utfgrid14;
	 var utfgrid15;
	 var utfgrid16;
	 var utfgrid17;
  


  
//================= MAP CLICK FUNCTIONALITY ====================//


  //function to handle which utfgrid layers gets shown
  map.on('zoomend', function (e) {
    handleUTFGrid();
	});

handleUTFGrid();

//determines which utf grid gets shown
function handleUTFGrid() {
    var currentZoom = map.getZoom();
    var currentLayer = new L.UtfGrid('http://localhost:8080/map_0_utfgrid/{z}/{x}/{y}.json?callback={cb}');
    
    switch (currentZoom) {
        case 0:
        	clearUTFLayers();
        	var utfgrid0 = new L.UtfGrid('http://localhost:8080/map_0_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid0;
			map.addLayer(utfgrid0);
			console.log("current grid is 0");
        break;
        case 1:
        	clearUTFLayers();
        	var utfgrid1 = new L.UtfGrid('http://localhost:8080/map_1_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid1;
			map.addLayer(utfgrid1);
			console.log("current grid is 1");
        break;
        case 2:
        	clearUTFLayers();
        	var utfgrid2 = new L.UtfGrid('http://localhost:8080/map_2_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid2;
			map.addLayer(utfgrid2);
			console.log("current grid is 2");
        break;
        case 3:
        	clearUTFLayers();
        	var utfgrid3 = new L.UtfGrid('http://localhost:8080/map_3_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid3;
			map.addLayer(utfgrid3);
			if(map.hasLayer(utfgrid3)){
				console.log("current grid utf 3");
			}
			
        break;
        case 4:
        	clearUTFLayers();
        	var utfgrid4 = new L.UtfGrid('http://localhost:8080/map_4_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid4;
			map.addLayer(utfgrid4);
			if(map.hasLayer(utfgrid3)){
				console.log("utfgrid3 still exists")
			}
			if(map.hasLayer(utfgrid4)){
				console.log("utfgrid4 exists")
			}
        break;
        case 5:
        	clearUTFLayers();
        	var utfgrid5 = new L.UtfGrid('http://localhost:8080/map_5_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid5;
			map.addLayer(utfgrid5);
			console.log("current grid is 5");
			if(map.hasLayer(utfgrid3)){
				console.log("utfgrid3 still exists")
			}
			if(map.hasLayer(utfgrid4)){
				console.log("utfgrid4 still exists")
			}
			if(map.hasLayer(utfgrid5)){
				console.log("utfgrid5 exists")
			}
			
        break;
        case 6:
        	clearUTFLayers();
        	var utfgrid6 = new L.UtfGrid('http://localhost:8080/map_6_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid6;
			map.addLayer(utfgrid6);
			console.log("current grid is 6");
			if(map.hasLayer(utfgrid3)){
				console.log("utfgrid3 still exists")
			}
			if(map.hasLayer(utfgrid4)){
				console.log("utfgrid4 still exists")
			}
			if(map.hasLayer(utfgrid5)){
				console.log("utfgrid5 still exists")
			}
			if(map.hasLayer(utfgrid6)){
				console.log("utfgrid6 exists")
			}
			
        break;
        case 7:
        	clearUTFLayers();
        	var utfgrid7 = new L.UtfGrid('http://localhost:8080/map_7_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid7;
			map.addLayer(utfgrid7);
			console.log("current grid is 7");
			if(map.hasLayer(utfgrid3)){
				console.log("utfgrid3 still exists")
			}
			if(map.hasLayer(utfgrid4)){
				console.log("utfgrid4 still exists")
			}
			if(map.hasLayer(utfgrid5)){
				console.log("utfgrid5 still exists")
			}
			if(map.hasLayer(utfgrid6)){
				console.log("utfgrid6 still exists")
			}
			if(map.hasLayer(utfgrid7)){
				console.log("utfgrid7 exists")
			}
        break;
        case 8:
        	clearUTFLayers();
        	var utfgrid8 = new L.UtfGrid('http://localhost:8080/map_8_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid8;
			map.addLayer(utfgrid8);
			console.log("current grid is 8");
        break;
        case 9:
        	clearUTFLayers();
        	var utfgrid9 = new L.UtfGrid('http://localhost:8080/map_9_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid9;
			map.addLayer(utfgrid9);
			console.log("current grid is 9");
        break;
        case 10:
        	clearUTFLayers();
        	var utfgrid10 = new L.UtfGrid('http://localhost:8080/map_10_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid10;
			map.addLayer(utfgrid10);
        break;
        case 11:
        	clearUTFLayers();
        	var utfgrid11 = new L.UtfGrid('http://localhost:8080/map_11_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid11;
			map.addLayer(utfgrid11);
        break;
        case 12:
         	clearUTFLayers();
        	var utfgrid12 = new L.UtfGrid('http://localhost:8080/map_12_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid12;
			map.addLayer(utfgrid12);
        break;
        case 13:
        	clearUTFLayers();
        	var utfgrid13 = new L.UtfGrid('http://localhost:8080/map_13_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid13;
			map.addLayer(utfgrid13);
        break;
        case 14:
        	clearUTFLayers();
        	var utfgrid14 = new L.UtfGrid('http://localhost:8080/map_14_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid14;
			map.addLayer(utfgrid14);
        break;
        case 15:
        	clearUTFLayers();
        	var utfgrid15 = new L.UtfGrid('http://localhost:8080/map_15_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid15;
			map.addLayer(utfgrid15);
        break;
        case 16:
        	clearUTFLayers();
        	var utfgrid16 = new L.UtfGrid('http://localhost:8080/map_16_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid16;
			map.addLayer(utfgrid16);
        break;
        case 17:
        	clearUTFLayers();
        	var utfgrid17 = new L.UtfGrid('http://localhost:8080/map_17_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid17;
			map.addLayer(utfgrid17);
        break;
        default:
        	//default is 17 for when users zoom past there but there's no more data to show
        	clearUTFLayers();
        	var utfgrid17 = new L.UtfGrid('http://localhost:8080/map_17_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid17;
			map.addLayer(utfgrid17);
        break;
    }

    //click functionality/shows wikipedia link in sidebar
    currentLayer.on('click', function(e) {
		if(e.data){
			console.log("clicked on a city");
			var title = e.data.citylabel;
			console.log(title);
			var labelstrings = title.split(" ");
			var url = "https://wikipedia.org/wiki/";
			for(var i = 0; i < labelstrings.length; i++){
				url += labelstrings[i];
				if(i < labelstrings.length -1) {
					url += "_";
				}
			}

			//NOTE: could make this much simpler in the future by using JQuery and 'append' - to look into 
		  	infobox.innerHTML = '<div class = "centered"> <h1 id = "title"> Welcome to the World of English Wikipedia </h1> <h3> City Name: <strong> ' + e.data.citylabel + '</strong> </h3> <p> Visit <a href = "'+ url + '" target = "_blank"> Wikipedia Page </a></p> </div>';
		} else {
			infobox.innerHTML = '<h1 id = "title" class = "centered"> Welcome to the World of English Wikipedia </h1>';
   		 }

});

}

//clears all existing utf grids layers (helper function for handleUTFGRID)
function clearUTFLayers(){
	map.eachLayer(function(layer){
		if(layer instanceof L.UtfGrid){
			map.removeLayer(layer);
			console.log("removed");
		}
	})
}

//========================== MAP SEARCH FUNCTIONALITY===========================//

map.addControl(new L.control.search({
	url: '../dynamic/search?q={s}',
	textPlaceholder: 'Search for an article',
	collapsed: false,
	markerLocation: true,
	markerIcon: new L.Icon({iconUrl:'blue-circleicon.png', iconSize: [20,20]})
}));



}