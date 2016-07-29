var createMap = function(){

//=================== MAP INITIALIZATION========================//

	
	var map = L.map('map').setView([0, 0], 3);
  	var page_info_box = document.getElementById('page-info-box');

  
//set up layer toggling for density and centroid

var density = L.tileLayer('../map_density/{z}/{x}/{y}.png',
    {
      maxZoom: 18,
      attribution: "WikiBrain / Sen Research Lab 2016"
    }).addTo(map);

var centroid = L.tileLayer('../map_centroid/{z}/{x}/{y}.png',
    {
      maxZoom: 18,
      attribution: "WikiBrain / Sen Research Lab 2016"
    })

var baseMaps = {
    "Density Contours": density,
    "Centroid Contours": centroid
};

L.control.layers(baseMaps, null, {
    collapsed: false,
    position: 'topleft'
}
).addTo(map);
  
//================= MAP CLICK FUNCTIONALITY ====================//


  //function to handle which utfgrid layers gets shown
  map.on('zoomend', function (e) {
    handleUTFGrid();
	});

handleUTFGrid();

//determines which utf grid gets shown
function handleUTFGrid() {
    var currentZoom = map.getZoom();
    var currentLayer = new L.UtfGrid('../map_0_utfgrid/{z}/{x}/{y}.json?callback={cb}');
    var countrygrid = new L.UtfGrid('../map_countrygrid/{z}/{x}/{y}.json?callback={cb}')
    
    switch (currentZoom) {
        case 0:
        case 1:	
        case 2:
        case 3:
        case 4:
            clearUTFLayers();
            map.addLayer(countrygrid);

        break;
        case 5:
        	clearUTFLayers();
        	var utfgrid5 = new L.UtfGrid('../map_5_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid5;
			map.addLayer(utfgrid5);

        break;
        case 6:
        	clearUTFLayers();
        	var utfgrid6 = new L.UtfGrid('../map_6_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid6;
			map.addLayer(utfgrid6);
			
        break;
        case 7:
        	clearUTFLayers();
        	var utfgrid7 = new L.UtfGrid('../map_7_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid7;
			map.addLayer(utfgrid7);

        break;
        case 8:
        	clearUTFLayers();
        	var utfgrid8 = new L.UtfGrid('../map_8_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid8;
			map.addLayer(utfgrid8);
			
        break;
        case 9:
        	clearUTFLayers();
        	var utfgrid9 = new L.UtfGrid('../map_9_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid9;
			map.addLayer(utfgrid9);
			
        break;
        case 10:
        	clearUTFLayers();
        	var utfgrid10 = new L.UtfGrid('../map_10_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid10;
			map.addLayer(utfgrid10);
        break;
        case 11:
        	clearUTFLayers();
        	var utfgrid11 = new L.UtfGrid('../map_11_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid11;
			map.addLayer(utfgrid11);
        break;
        case 12:
         	clearUTFLayers();
        	var utfgrid12 = new L.UtfGrid('../map_12_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid12;
			map.addLayer(utfgrid12);
        break;
        case 13:
        	clearUTFLayers();
        	var utfgrid13 = new L.UtfGrid('../map_13_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid13;
			map.addLayer(utfgrid13);
        break;
        case 14:
        	clearUTFLayers();
        	var utfgrid14 = new L.UtfGrid('../map_14_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid14;
			map.addLayer(utfgrid14);
        break;
        case 15:
        	clearUTFLayers();
        	var utfgrid15 = new L.UtfGrid('../map_15_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid15;
			map.addLayer(utfgrid15);
        break;
        case 16:
        	clearUTFLayers();
        	var utfgrid16 = new L.UtfGrid('../map_16_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid16;
			map.addLayer(utfgrid16);
        break;
        case 17:
        	clearUTFLayers();
        	var utfgrid17 = new L.UtfGrid('../map_17_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid17;
			map.addLayer(utfgrid17);
        break;
        default:
        	//default is 17 for when users zoom past there but there's no more data to show
        	clearUTFLayers();
        	var utfgrid17 = new L.UtfGrid('../map_17_utfgrid/{z}/{x}/{y}.json?callback={cb}');
        	currentLayer = utfgrid17;
			map.addLayer(utfgrid17);
        break;
    }

    //click functionality/shows wikipedia link in sidebar
    currentLayer.on('mouseover', function(e) {
		if(e.data){
            console.log(e.data)
            var title = e.data.citylabel;
            var labelstrings = title.split(" ");
            var url = "https://wikipedia.org/wiki/";
            for(var i = 0; i < labelstrings.length; i++){
                url += labelstrings[i];
                if(i < labelstrings.length -1) {
                    url += "_";
                }
            }

            var marker = new L.Marker([e.data.y, e.data.x], {opacity: 1.0});
            marker.setIcon(new L.Icon({iconUrl: './images/blackDot.png'}))
            marker.addTo(map);
             $(marker._icon).addClass('tooltip');
            $('.tooltip').tooltipster({
                content: "<a href =" + url + ">" + title + "</a>",
                trigger: "hover",
                interactive: "true",
                contentAsHTML: "true"
            });
            

			//NOTE: could make this much simpler in the future by using JQuery and 'append' - to look into 
		  	page_info_box.innerHTML = '<div class = "centered"><style>#explanation {padding-top: 20px}</style> <h4 id="explanation"> Article Name: </h4><p style = "font-size: 23"><strong> ' + e.data.citylabel + '</strong> </p> <p style = "font-size: 21"> Visit the <a href = "'+ url + '" target = "_blank"> Wikipedia Page </a></p> </div>';
		} else {
			page_info_box.innerHTML = '';
   		}

    });

    countrygrid.on('click', function(e) {
        if(e.data){
            var title = e.data.labels;
            switch(title){
                case "Music":
                    map.setView(new L.LatLng(13.529, -2.131), 6);
                    break;
                case "Sports":
                    map.setView(new L.LatLng(16.689, -7.778), 6);
                    break;
                case "Physics & Maths":
                    map.setView(new L.LatLng(8.679, -4.592), 6);
                    break;
                case "Technology":
                    map.setView(new L.LatLng(7.504, -14.603), 6);
                    break;
                case "Politics & Econ":
                    map.setView(new L.LatLng(-3.917, -8.569), 6);
                    break;
                case "Aviaton & Warfare":
                    map.setView(new L.LatLng(-2.274, -17.073), 6);
                    break;
                case "History & Geography":
                    map.setView(new L.LatLng(-5.605, -1.978), 6);
                    break;
                case "Entertainers & Media":
                    map.setView(new L.LatLng(-12.972, 4.460), 6);
                    break;
                case "TV & Movies":
                    map.setView(new L.LatLng(-7.264, 9.141), 6);
                    break;
                case "Anime & Gaming":
                    map.setView(new L.LatLng(-9.178, 4.788), 6);
                    break;
                case "Natural World":
                    map.setView(new L.LatLng(2.449, 9.514), 6);
                    break;
                case "Biology & Medicine":
                    map.setView(new L.LatLng(8.135, 9.778), 6);
                    break;
                case "India":
                    map.setView(new L.LatLng(14.743, 11.470), 6);
                    break;
                default:
                    map.setView()
            }
        }
    });

};



//clears all existing utf grids layers (helper function for handleUTFGRID)
function clearUTFLayers(){
	map.eachLayer(function(layer){
		if(layer instanceof L.UtfGrid){
			map.removeLayer(layer);
		}
	})
}

//========================== MAP SEARCH FUNCTIONALITY===========================//

var search = new L.control.search({
	url: '../dynamic/search?q={s}',
	textPlaceholder: 'Search for an article',
	collapsed: false,
	markerLocation: true,
	markerIcon: new L.Icon({iconUrl:'blue-circleicon.png', iconSize: [20,20]})
});

search.addTo(map);

//move search to sidebar rather than map itself
var htmlObject = search.getContainer();
var searchdiv = document.getElementById('search-box');

function setParent(elem, newParent){
	newParent.appendChild(elem);
}

setParent(htmlObject, searchdiv);

//========================= MAP HASH FOR SOCIAL MEDIA LINK SHARING/LINKING TO SPECIFIC LOCATIONS =============================//

var hash = new L.Hash(map);

//========================= SOCIAL SHARING FUNCTIONALITY ============================//

}