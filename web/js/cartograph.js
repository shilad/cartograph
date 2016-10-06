var CG = CG || {};


CG.map = L.map('map');
CG.mapEl = $("#map");  // optimization
CG.ttEl = $("#tooltip");

CG.layer = Tangram.leafletLayer({
    scene: '../template/scene.yaml',
    attribution: '<a href="https://nokomis.macalester.edu/cartograph" target="_blank">Cartograph</a> | &copy; Shilad Sen & contributors'
});
CG.activeLayer = null;

CG.getLayer = function() {
    var src = CG.layer.scene.config.sources.vector;
    var i = src.url.indexOf('/vector/');
    if (i < 0) {
        console.log('couldnt find srcName ' + srcName + ' in ' + src.url);
        return;
    }
    var j = i + '/vector/'.length;
    var k = src.url.indexOf('/', j + 1);
    return src.url.substring(j, k);
};

CG.changeLayer = function(newLayer) {
    var changed = false;
    ["vector", "raster"].forEach(function (srcName) {
        var src = CG.layer.scene.config.sources[srcName];
        var i = src.url.indexOf('/' + srcName + '/');
        if (i < 0) {
            console.log('couldnt find srcName ' + srcName + ' in ' + src.url);
            return;
        }
        var j = i + srcName.length + 2;
        var k = src.url.indexOf('/', j + 1);
        var newUrl = src.url.substring(0, j) + newLayer + src.url.substring(k);
        if (newUrl != src.url) {
            src.url = newUrl;
            changed = true;
        }
    });
    if (changed) {
        CG.layer.scene.updateConfig();
    }
};


// var grid = L.gridLayer({
//     attribution: 'Grid Layer',
//     tileSize: L.point(256, 256)
// });
// grid.createTile = function (coords, done) {
//     var tile = document.createElement('div');
//     tile.innerHTML = [coords.x, coords.y, coords.z].join(', ');
//     tile.style.border = '2px solid red';
// // 			tile.style.background = 'white';
//     // test async
//     setTimeout(function () {
//         done(null, tile);
//     }, 0);
//     return tile;
// };
// grid.addTo(CG.map);

// window.setTimeout(function() { CG.changeLayer('gender') }, 3000);

CG.layer.addTo(CG.map);

CG.cursorTimer = null;

CG.layer.scene.subscribe({
  load : function(e) {
      CG.hash = new L.Hash(CG.map);
      var container = $('.leaflet-container');

      CG.layer.setSelectionEvents({
       hover: function(selection) {
           if (selection.feature) {
               container.css('cursor','pointer');
               if (CG.cursorTimer) {
                   clearTimeout(CG.cursorTimer);
                   CG.cursorTimer = null;
               }
           } else if (!CG.cursorTimer) {
               CG.cursorTimer = setTimeout(function() {
               container.css('cursor','');
               }, 50);
           }
       },
       click: function(selection) {
         if (selection.feature && selection.feature.properties.name) {
           var ev = selection.leaflet_event.originalEvent;
           CG.handleCityHover(
                   ev.clientX,
                   ev.clientY,
                   selection.feature.properties.name);
         } else {
           CG.cancelCityHover();
         }
       }
    });
  },
  error: function (e) {
      console.log('scene error:', e);
  },
  warning: function (e) {
      console.log('scene warning:', e);
  }
});

CG.map.setView([0, 0], 4);

$('#search-field').autocomplete({
    serviceUrl: '../search.json',
    paramName: 'q',
    autoSelectFirst: true,
    onSelect: function (suggestion) {
      var info = suggestion.data;
      CG.map.flyTo(info.loc, info.zoom + 2, { duration : 0.4 });
      L.marker(info.loc).addTo(CG.map);
    }
});

CG.ttEl.tooltipster({
    content: 'Loading...',
    theme: 'tooltipster-shadow',
    contentAsHTML: true,
    trigger: 'custom',
    triggerOpen: {},
    interactive: true,
    delay: [400, 1000],
    updateAnimation: 'fade',
    maxWidth: 400,
    triggerClose: {
        mouseleave: true,
        originClick: true,
        touchleave: true
    }
});


CG.ttShowTimer = 0;
CG.ttHideTimer = 0;
CG.tt = CG.ttEl.tooltipster("instance");

CG.handleCityHover = function (mapX, mapY, title) {
  clearTimeout(CG.ttHideTimer);
  CG.ttHideTimer = 0;

  if (CG.ttShowTimer && CG.ttEl.data("toLoad") == title) {
    return; // in progress!
  }
  CG.ttEl.data("toLoad", title);
  if (CG.ttShowTimer) {
    clearTimeout(CG.ttShowTimer);
  }
  CG.ttShowTimer = setTimeout(function () {
    CG.ttShowTimer = null;
    CG.showCityTooltip(mapX, mapY, title);
  }, 0);
};

CG.cancelCityHover = function () {
  clearTimeout(CG.ttShowTimer);
  CG.ttShowTimer = 0;
  if (CG.tt.status().open && !CG.ttHideTimer) {
    CG.ttHideTimer = setTimeout(function () {
      CG.ttHideTimer = null;
      CG.tt.close();
      }, 1000);
  }
};

CG.showCityTooltip = function (mapX, mapY, title) {
  var isOpen = CG.tt.status().open;
  if (CG.ttEl.data("loading") == title) {
    if (!isOpen) CG.tt.open();
    return;
  }
  CG.ttEl.data("loading", title);

   var offset = CG.mapEl.offset();
   CG.ttEl.offset({
     top : offset.top + mapY - CG.ttEl.height() / 2,
     left : offset.left + mapX - CG.ttEl.width() / 2,
   });

  var html = '<b>' + title + '</b><br/>loading...';
  CG.tt.content(html);
  CG.tt.open();
  if (isOpen) {
    CG.tt.reposition();
  }
  var encoded = encodeURIComponent(title);
  var uri = 'https://en.wikipedia.org/w/api.php?action=query&format=json&titles=' + encoded + '&prop=pageimages|extracts&exintro&explaintext&exchars=400&callback=?';
  $.getJSON(uri, function(json){
    var info = null;
    for (var pageId in json.query.pages) {
      info = json.query.pages[pageId];
      break;
    }
    var text = info.extract;
    var img = info.thumbnail;
    var html = "";
    if (img) {
      html += '<img align=left src="' + img.source + '" width=' + img.width + ' height=' + img.height + '>';
    }
    html += '<b>' + title + ':</b> &nbsp; &nbsp;' + text;

    var wpUrl = 'http://en.wikipedia.org/wiki/' + encoded;
    html += '[<a target="_new" href="' + wpUrl + '">see Wikipedia article</a>]';

    // call the 'content' method to update the content of our tooltip with the returned data
    CG.tt.content(html);

    // to remember that the data has been loaded
    CG.ttEl.data('loaded', title);

    if (!CG.ttEl.data("mouseInBound")) {
      CG.ttEl.data("mouseInBound", true);
      $(".tooltipster-base").on("mouseenter", function() {
        clearTimeout(CG.ttHideTimer);
        CG.ttHideTimer = null;
      });
    }
  });
}