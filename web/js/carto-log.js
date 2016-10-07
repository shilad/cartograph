var CG = CG || {};

CG.uid = Cookies.get("CARTO_UID");
if (!CG.uid) {
    CG.uid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
        return v.toString(16);
    });
    Cookies.set("CARTO_UID", CG.uid, { expires : 14 });
}

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

    $.ajax({
      type: "POST",
      url: "../log",
      data: JSON.stringify(params),
      success: function() {},
      dataType: 'application/json'
    });
};


CG.mapMoveTimeout = null;
CG.addMapLogging = function(map) {
    var logBuffer = {};
    ['load', 'moveend', 'dragend', 'zoomend', 'click', 'doubleclick'].forEach(
        function (eventName) {
            map.on(eventName, function() {
                if (CG.mapMoveTimeout) clearTimeout(CG.mapMoveTimeout);
                var now = $.now();
                if (logBuffer[eventName]) {
                    logBuffer[eventName].endTstamp = now;
                    logBuffer[eventName].count += 1;
                } else {
                    logBuffer[eventName] = {
                        begTstamp : now, endTstamp : now,
                        count : 1, event: eventName
                    };
                }
                CG.mapMoveTimeout = setTimeout(function() {
                    for (var n in logBuffer) {
                        CG.log(logBuffer[n]);
                        delete logBuffer[n];
                    }
                }, 500);
            });
        }
    );
};