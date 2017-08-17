/**
 * Created by sen on 6/29/17.
 */

/**
 * TODO: This should come from the server, really...
 */
var CLUSTER_LAYER_INFO = {
    range: [],
    sequential: false,
    numUnique: 12,
    name: 'Clusters',
    title: false,
    diverging: false,
    qualitative: true
};

var CLUSTER_LAYER_INIT = {
    field: 'Clusters',
    title: 'Thematic Clusters',
    description: 'This visualization shows groups of thematically related articles.',
    id: 'clusters',
    dataType: 'qualitative',
    numColors: 7,
    colorScheme: 'Paired'
};

var COLOR_SCHEME_NAMES = {
    sequential: ["BuGn", "BuPu", "GnBu", "OrRd", "PuBu", "PuBuGn", "PuRd", "RdPu", "YlGn", "YlGnBu", "YlOrBr", "YlOrRd"],
    singlehue: ["Blues", "Greens", "Greys", "Oranges", "Purples", "Reds"],
    diverging: ["BrBG", "PiYG", "PRGn", "PuOr", "RdBu", "RdGy", "RdYlBu", "RdYlGn", "Spectral"],
    qualitative: ["Accent", "Dark2", "Paired", "Pastel1", "Pastel2", "Set1", "Set2", "Set3"]
};


$(document).ready(function () {
    // Enable the custom file input widget
    $('#inputFile').on('change', fileChangedHandler);

    $("#upload-form").on('submit', function (event) {
        event.stopPropagation(); // Stop stuff happening
        event.preventDefault(); // Totally stop stuff happening
        uploadFormHandler();
    });

    $("#add-layer-button").on('click', function (e) {
        e.preventDefault();
        addLayer();
    });
    $("#layer-form").on('submit', function(e) {
        e.preventDefault();
        submitMap();
    });
});


function ajax_buildMap() {
    // Ajax call to build the map
    $.ajax({
        url: '../add_map/' + $("#map_name").val(),
        type: 'POST',
        success: function (textStatus, jqXHR) {
            submit_forms();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR, textStatus, errorThrown);
        }
    });
    $("h3").append("<p>Please wait while we create your map...</p>");
    // createMapDescription(vizName, vizDescription);

}

function submit_forms() {
    $('form').each(function () {
        if ($(this).attr("id") !== "upload-form") {
            $(this).validate({errorElement: 'layerErrors',});  // Validate the form
            if ($(this).valid() && !$(this).hasClass('submitted')) {
                $(this).submit();
                // Add a class 'submitted' to this form and disable all its elements.
                $(this).addClass('submitted');
                var form = document.getElementById($(this).attr("id"));
                var elements = form.elements;
                for (var i = 0; i < elements.length; ++i) {
                    elements[i].disabled = true;
                }
            }
        }
    });

}

function ajax_layers(i) {
    // Ajax call to add the ith layer

    var layersForm = $(`#layersForm${i}`);
    event.stopPropagation(); // Stop stuff happening
    event.preventDefault(); // Totally stop stuff happening

    // Perform Ajax call to apply layer
    var layerData = {
        layer_name: $(`#title${i}`).val(),
        column: $(`#fields${i}`).val(),
        color_palette: $(`#color-scheme${i}`).val() + "_" + $(`#number-classes${i}`).val(),
        description: $(`#description${i}`).val()
    };

    $.ajax({
        url: '../' + $("#map_name").val() + '/add_layer/' + $(`#types${i}`).val(),
        type: 'POST',
        data: layerData,
        dataType: 'json',
        cache: false,
        processData: true,
        async: false,
        contentType: false, // Set content type to false as jQuery will tell the server its a query string request
        success: function (textStatus, jqXHR) {
            console.log("Successfully added layer to the map!");
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR, textStatus, errorThrown);
        }
    })
}

function uploadFormHandler() {
    var showUploadError = function (message) {
        $("#upload-error .alert").html(message).parent().show();
    };

    var showUploadProgress = function (percentComplete) {
        percentComplete = parseInt(percentComplete * 100);
        $("#upload-status").text(percentComplete + '% uploaded');
        if (percentComplete === 100) {
            $("#upload-status").text('Upload complete. Processing file...');
        }
    };


    var $uploadForm = $("#upload-form");
    var $layerForm = $("#layer-form");

    $("#upload-error").hide();

    var mapId = $("#map-id").val();
    if (!/^[a-z0-9_-]+$/i.test(mapId)) {
        showUploadError("Map id can only contain alphanumeric characters");
        return;
    }

    // Declare a form data object
    var data = new FormData();
    data.append('map-id', mapId);
    var file = $uploadForm.find('input[type=file]')[0].files[0];
    var fileName = file.name;
    data.append('file', file);

    // Perform Ajax call to show add visualization part
    $.ajax({
        url: $uploadForm.attr('action'),
        type: 'POST',
        data: data,
        cache: false,
        processData: false, // Don't process the files, we're using FormData
        contentType: false, // Set content type to false as jQuery will tell the server its a query string request
        xhr: function () {
            var xhr = new window.XMLHttpRequest();
            xhr.upload.addEventListener("progress", function (evt) {
                if (evt.lengthComputable) {
                    showUploadProgress(evt.loaded / evt.total);
                }
            }, false);
            return xhr;
        },
        success: function (data, textStatus, jqXHR) {
            if (!data.success) {
                showUploadError("<strong>Upload Failed</strong> " + data.error);
                return;
            }
            CG.uploadData = data;

            // Disable changes to the map id, show layer UI, and remove all existing layers
            $("#map-id").attr('disabled', '');
            $("div.layer:visible").remove();
            $("#upload-status").hide();
            $("div.step").addClass('active');

            showFileInfo(fileName);
            addLayer(CLUSTER_LAYER_INIT);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR, textStatus, errorThrown);
        }
    });
}

function showFileInfo(fileName) {
    var data = CG.uploadData;

    $("#file-info table tbody tr").not(':first').remove();
    $('#file-info .summary span:nth-child(1)').text(fileName);
    $('#file-info .summary span:nth-child(2)').text(data.num_rows);

    for (var i = 0; i < data.columns.length; i++) {
        var col = data.columns[i];
        var row = $("#row-template").clone();
        row.removeAttr('id');
        row.removeClass('hidden');

        $(row).find("th").text("#" + (i + 1));
        $(row).find("td:nth-of-type(1)").text(col.name);
        $(row).find("td:nth-of-type(2)").text(col.num);

        var types = ['sequential', 'diverging', 'qualitative', 'title'].filter(function (t) {
            return col[t];
        })
        $(row).find("td:nth-of-type(3)").text(types);

        var vals = col.values ? col.values.join(', ') : ('min: ' + col.range[0] + 'max: ' + col.range[1]);
        $(row).find("td:nth-of-type(4)").text(vals);

        $("#file-info tbody").append(row);
    }

    $("#upload-status").hide();
    $("#file-info").show();
}

function addLayer(layerInfo) {
    var data = CG.uploadData;
    var layerInfo = layerInfo || {};
    var cols = data.columns.filter(function (col) {
        return col.name !== 'Article';
    });

    // Calculate layer index
    var layerIndex = 1;
    $("#layer-container div.layer:visible").each(function () {
        var id = $(this).attr('id');
        CG.assert(id.startsWith('layer-'), 'Malformed layer id: ' + id);
        id = parseInt(id.substr('layer-'.length));
        if (id >= layerIndex) {
            layerIndex = id + 1;
        }
    });

    var $elem = $("#layer-template")
        .clone()
        .attr("id", 'layer-' + layerIndex)
        .removeClass("hidden");

    // Replace "__NUM__" with index in layer ids
    $elem.find("input,select,textarea")
        .each(function (i, elem) {
            var e = $(elem);
            var name = e.attr('name');
            if (/__NUM__/.test(name)) {
                e.attr('name', name.replace('__NUM__', layerIndex));
            }
            e.attr('required', '');
        });

    // Useful sub elements for layer
    var $fields = $elem.find(".layer-field");
    var $numColors = $elem.find(".layer-num-colors");
    var $dataType = $elem.find(".layer-datatype");
    var $schemes = $elem.find(".color-schemes");
    var $schemeName = $elem.find(".color-scheme-name");

    // Add available fields
    $fields.empty();
    cols.forEach(function (c) {
        $fields.append($("<option/>").text(c.name));
    });
    $fields.append($("<option/>").text("Clusters"));

    // Gets information about the selected field.
    var getFieldInfo = function () {
        var f = $fields.val();
        var fieldInfo = null;
        if (f === 'Clusters') {
            fieldInfo = CLUSTER_LAYER_INFO;
        } else {
            data.columns.forEach(function (c, i) {
                if (c.name === f) {
                    fieldInfo = c;
                }
            });
        }
        CG.assert(fieldInfo != null, "No layer " + f + " found");
        return fieldInfo;
    };

    // Handler for changing the field
    var fieldHandler = function (ev, layerInfo) {
        var fi = getFieldInfo();
        $dataType.empty();
        if (fi.sequential) $dataType.append($("<option>sequential</option>"));
        if (fi.diverging) $dataType.append($("<option>diverging</option>"));
        if (fi.qualitative) $dataType.append($("<option>qualitative</option>"));
        if (layerInfo && layerInfo.dataType) {
            $dataType.val(layerInfo.dataType);
        }
        $dataType.trigger('change', layerInfo);
    };
    $fields.on('change', fieldHandler);

    // Handler for changing the data type
    var dataTypeHandler = function (ev, layerInfo) {
        var colorRange;
        var fi = getFieldInfo();
        var dt = $dataType.val();
        if (fi.name === 'Clusters') {
            colorRange = [3, 12];
        } else if (dt === 'sequential') {
            colorRange = [3, 9];
        } else if (dt === 'diverging') {
            colorRange = [3, 11];
        } else {
            CG.assert(dt === 'qualitative');
            CG.assert(fi.numUnique <= 12, "Too many unique values: " + fi.numUnique);
            colorRange = [fi.numUnique, fi.numUnique];
        }
        $numColors.empty();
        for (var i = colorRange[0]; i <= colorRange[1]; i++) {
            $numColors.append($("<option>" + i + "</option>"))
        }
        if (layerInfo && layerInfo.numColors) {
            $numColors.val(layerInfo.numColors);
        }
        $numColors.trigger('change', layerInfo);
    };
    $dataType.on("change", dataTypeHandler);

    // Handler for changing the number of colors
    var numColorHandler = function (ev, layerInfo) {
        var fi = getFieldInfo();
        var dt = $dataType.val();
        var nc = $numColors.val();
        $schemes.css('height', nc * 10 + 4);

        // Clear out everything but the template.
        $schemes.children().each(function () {
            if (!$(this).hasClass('template')) {
                $(this).remove();
            }
        });
        COLOR_SCHEME_NAMES[dt].forEach(function (n) {
            var colors = colorbrewer[n][nc];
            if (!colors) return;
            var $schemeDiv = $schemes.find('.template')
                .clone()
                .removeClass('template')
                .removeClass('hidden')
                .css('display', 'inline-block')
                .css('height', nc * 10);
            var $rectTemplate = $schemeDiv.find('rect');
            var $schemeSvg = $schemeDiv.find("svg").empty();
            for (var i = 0; i < colors.length; i++) {
                var $rect = $rectTemplate.clone()
                    .removeClass('template')
                    .removeClass('hidden')
                    .attr('y', i * $rectTemplate.attr('width'))
                    .attr('fill', colors[i]);
                $schemeSvg.append($rect);
            }
            if (layerInfo && layerInfo.colorScheme === n) {
                $schemeDiv.addClass('active');
                $schemeName.val(n + '_' + nc);
            }
            $schemes.append($schemeDiv);

            // Handler for selecting a specific color
            $schemeDiv.on('click', function () {
                $schemes.find('div.scheme').removeClass('active');
                $(this).addClass('active');
                $schemeName.val(n + '_' + nc);
            });
        });
        // If no schemes are active, set the first as active
        if ($schemes.find('.active').length === 0) {
            $schemes.find('div.scheme:visible').first().click();
        }
    };
    $numColors.on("change", numColorHandler);

    $("#add-layer-button").before($elem);

    // These do not have any dependencies, so they can safely be set
    if (layerInfo.id) {
        $elem.find('.layer-id').val(layerInfo.id);
    }
    if (layerInfo.title) {
        $elem.find('.layer-title').val(layerInfo.title);
    }
    if (layerInfo.description) {
        $elem.find('.layer-description').val(layerInfo.description);
    }

    // Kick off the updates to the component
    if (layerInfo.field) {
        $fields.val(layerInfo.field);
    }
    $fields.trigger('change', layerInfo);

    // Enable the user to remove the layer.
    $elem.find(".layer-remove").on('click', function () {
        $elem.slideUp("slow", function () {
            $(this).remove();
        });
    });
}


function submitMap() {
    var $layerForm = $("#layer-form");

    var mapJs = {
        mapId     : $("#map-id").val(),
        mapTitle  : $("#map-title").val(),
        email     : $("#email-input").val(),
        layers    : []
    };

    $("#layer-container").find("div.layer:visible").each(
        function () {
            var $e = $(this);
            var layer = {
                field       : $e.find(".layer-field").val(),
                id          : $e.find(".layer-id").val(),
                title       : $e.find(".layer-title").val(),
                description : $e.find(".layer-description").val(),
                datatype    : $e.find(".layer-datatype").val(),
                numColors   : $e.find(".layer-num-colors").val(),
                colorScheme : $e.find(".color-scheme-name").val()
            };
            mapJs.layers.push(layer);
        }
    );

    console.log(mapJs);
}

/**
 * Custom file upload widget
 * See https://stackoverflow.com/questions/43250263/bootstrap-4-file-input
 * See https://github.com/twbs/bootstrap/issues/20813
 */
function fileChangedHandler() {
    var $input = $(this);
    var target = $input.data('target');
    var $target = $(target);

    // set original content so we can revert if user deselects file
    if (!$target.attr('data-original-content'))
        $target.attr('data-original-content', $target.attr('data-content'));

    var input = $input.get(0);

    var name = (input && input.files && input.files.length && input.files[0])
        ? input.files[0].name : $input.val();

    if (!name) name = $target.attr('data-original-content');
    $target.attr('data-content', name);

    // Change the visual feedback
    $(this).next('.custom-file-control').addClass("selected").html(name);
};

function createMapDescription(vizName, vizDescription) {
    var description = [
        '<div class="legend" id="legend-cluster">',
        '<h1>',
        "Map Description",
        '</h1>',
        '<p>',
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
        '</p>',
        '</div>'
    ].join("\n");

    $("h3").append(description);
}