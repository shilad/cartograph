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
    params.messages = messages;

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