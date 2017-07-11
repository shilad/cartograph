var CG = CG || {};

CG.uid = Cookies.get("CARTO_UID");
if (!CG.uid) {
    CG.uid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
        return v.toString(16);
    });
    Cookies.set("CARTO_UID", CG.uid, { expires : 14 });
}

CG.logToConsole = false;

CG.log = function(params) {
    var map = CG.map;
    var center = map.getCenter(),
        zoom = map.getZoom(),
        precision = Math.max(0, Math.ceil(Math.log(zoom) / Math.LN2));

    if (!params.begTstamp) {
        params.tstamp =  $.now();
    }
    params.uid = CG.uid;
    params.layer = CG.getLayer();
    params.zoom = zoom;
    params.lat = center.lat.toFixed(precision);
    params.lng = center.lng.toFixed(precision);
    params.url = location.href;

    if (CG.logToConsole) {
        console.log(params);
    } else {
        $.ajax({
          type: "POST",
          url: "../log",
          data: JSON.stringify(params),
          success: function() {},
          dataType: 'application/json'
        });
    }

};

CG.lastLoc = {lat:0, lng:0}; //last location of the map shown to user
CG.lastZoom = 0; //last zoom level of the map shown to user
CG.logMany = function(messages) {

    var map = CG.map;
    var center = map.getCenter(),
        zoom = map.getZoom(),
        precision = Math.max(0, Math.ceil(Math.log(zoom) / Math.LN2));

    var params = {};
    params.uid = CG.uid;
    params.layer = CG.getLayer();
    params.zoom = zoom;
    params.lat = center.lat.toFixed(precision);
    params.lng = center.lng.toFixed(precision);
    params.url = location.href;
    params.messages = messages;


    if (CG.logToConsole) {
        console.log(params);
    } else {
       //if user moved the map far enough, or zoomed in or out far enough it will send a call to the server to recalculate paths and redraw them to the screen
        if((Math.abs(CG.lastLoc.lat.toFixed(precision) - params.lat) >= 2 && Math.abs(CG.lastLoc.lng.toFixed(precision) - params.lng) >= 2) ||
            (Math.abs(CG.lastZoom - params.zoom)>= 1)){
            removePathsInViewPort();
            getPathsInViewPort();
        }

        CG.lastLoc = center; //set last location as current location
        CG.lastZoom = params.zoom;  //set last zoom level as current zoom level
        $.ajax({
          type: "POST",
          url: "../log",
          data: JSON.stringify(params),
          success: function() {

          },
          dataType: 'application/json'
        });
    }

};


CG.mapMoveTimeout = null;
CG.addMapLogging = function(map) {
    var logBuffer = {};
    ['load', 'moveend', 'dragend', 'zoomend', 'click', 'doubleclick'].forEach(
        function (eventName) {
            map.on(eventName, function() {
                var center = map.getCenter(),
                    zoom = map.getZoom(),
                    precision = Math.max(0, Math.ceil(Math.log(zoom) / Math.LN2));

                if (CG.mapMoveTimeout) clearTimeout(CG.mapMoveTimeout);
                var now = $.now();
                if (!logBuffer[eventName]) {
                    logBuffer[eventName] = {
                        begTstamp : now,
                        begZoom : zoom,
                        begLat : center.lat.toFixed(precision),
                        begLng : center.lng.toFixed(precision),
                        count : 0,
                        event: eventName
                    };
                }

                logBuffer[eventName].endZoom = zoom;
                logBuffer[eventName].endLat = center.lat.toFixed(precision);
                logBuffer[eventName].endLng = center.lng.toFixed(precision);
                logBuffer[eventName].endTstamp = now;
                logBuffer[eventName].count += 1;

                CG.mapMoveTimeout = setTimeout(function() {
                    var messages = [];
                    for (var n in logBuffer) {
                        messages.push(logBuffer[n]);
                        delete logBuffer[n];
                    }
                    CG.logMany(messages);
                }, 500);
            });
        }
    );
};