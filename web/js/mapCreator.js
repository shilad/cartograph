/**
 * Created by sen on 6/29/17.
 */

/**
 * TODO: This should come from the server, really...
 */
var CLUSTER_LAYER_INFO = {
            "range": [],
            "sequential": false,
            "numUnique": 12,
            "name": "Clusters",
            "title": false,
            "diverging": false,
            "qualitative": true,
            "num": 460
        };

$(document).ready(function () {
    var bar = $('.bar');
    var percent = $('.percent');
    var status = $('#status');
    var uploadForm = $("#uploadForm");


    // Handle custom file inputs
    // See https://stackoverflow.com/questions/43250263/bootstrap-4-file-input
    // and https://github.com/twbs/bootstrap/issues/20813
    $('#inputFile').on('change', function (ev) {
      const $input = $(this);
      const target = $input.data('target');
      const $target = $(target);

      // set original content so we can revert if user deselects file
      if (!$target.attr('data-original-content'))
        $target.attr('data-original-content', $target.attr('data-content'));

      const input = $input.get(0);

      let name = (input && input.files && input.files.length && input.files[0])
          ? input.files[0].name : $input.val();

      if (!name) name = $target.attr('data-original-content');
      $target.attr('data-content', name);

      // Change the visual feedback
      $(this).next('.custom-file-control').addClass("selected").html(name);

    });


    var data = {
        "map_name": "a",
        "num_rows": 460,
        "columns": [{
            "range": [],
            "sequential": false,
            "numUnique": 459,
            "name": "Article",
            "title": true,
            "diverging": false,
            "values": [],
            "qualitative": false,
            "num": 460
        }, {
            "range": [],
            "sequential": true,
            "numUnique": 9,
            "name": "Popularity",
            "title": false,
            "diverging": true,
            "values": [0, 13, 15, 22, 25, 50, 75, 90, 100],
            "qualitative": true,
            "num": 460
        }, {
            "range": [],
            "sequential": false,
            "numUnique": 3,
            "name": "Category",
            "title": false,
            "diverging": false,
            "values": ["a", "b", "c"],
            "qualitative": true,
            "num": 460
        }],
        "success": true
    };
    addLayer(data, {
        field : 'Clusters',
        title : 'Thematic Clusters',
        description : 'This visualization shows groups of thematically related articles.',
        id : 'clusters',
        dataType : 'qualitative',
        numColors : 7
    });

    $("#add-layer-button").on('click', function(e) {
        e.preventDefault();
        addLayer(data);
    });


    showUploadError = function (message) {
        $("#upload-error .alert").html(message).parent().show();
    };

    uploadForm.on('submit', function (event) {
        event.stopPropagation(); // Stop stuff happening
        event.preventDefault(); // Totally stop stuff happening

        $("#upload-error").hide();

        var mapId = $("#map-id").val();
        if (!/^[a-z0-9_]+$/i.test(mapId)) {
            showUploadError("Map id can only contain alphanumeric characters");
            return;
        }

        // Declare a form data object
        var data = new FormData();
        data.append('map-id', mapId);
        var file = uploadForm.find('input[type=file]')[0].files[0];
        var fileName = file.name;
        data.append('file', file);

        // Perform Ajax call to show add visualization part
        $.ajax({
            url: uploadForm.attr('action'),
            type: 'POST',
            data: data,
            cache: false,
            processData: false, // Don't process the files, we're using FormData
            contentType: false, // Set content type to false as jQuery will tell the server its a query string request
            success: function (data, textStatus, jqXHR) {
                if (!data.success) {
                    showUploadError("<strong>Upload Failed</strong> " + data.error);
                    return;
                }
                CG.uploadData = data;
                CG.layerCounter = 0; // A counter of input layers.

                showFileInfo(data, fileName);
                addLayer(data,
                    {field : 'Clusters', 'num-colors': 7, 'type' : 'qualitative'});

                // Display Generate Map button that submits all layer forms
                $("#mapConfig").append(`<button type="submit" class="btn btn-generateMap" form="layersForm0" value="GenerateMap" id="submitButton"> GENERATE MAP! </button>`)

                CG.mapBuilt = false;  // A boolean indicating whether the map has been built to avoid building it again when hitting GenerateMap
                $(`#submitButton`).click(function () {
                    // Build the map
                    if (!CG.mapBuilt) {
                        ajax_buildMap();
                        CG.mapBuilt = true;
                    } else {
                        submit_forms();
                    }
                    // window.location.href = '../' + $("#map_name").val() + '/static/iui2017.html';
                });

                $("#mapConfig").show();
                $("#map_name").prop('disabled', true);
                $("#uploadFile").prop('disabled', true);

                // Show layer options after hitting addVisualization button.
                $(".btn-addVisualization").click(createNewMetricHtml);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR, textStatus, errorThrown);
            }
        });
    });
});

function createNewMetricHtml() {
    CG.layerCounter += 1;
    $("#newRequirements").show();
    appendVisualizationRequirements(CG.layerCounter);

    // Automatically fill in layer input fields.
    createSelectFields(CG.uploadData.columns, CG.layerCounter);
    createSelectTypes(document.getElementById("fields" + CG.layerCounter), CG.layerCounter);
    createNumClasses(document.getElementById("fields" + CG.layerCounter), document.getElementById("types" + CG.layerCounter), CG.layerCounter);
    createSelectPalettes(document.getElementById("types" + CG.layerCounter), document.getElementById("number-classes" + CG.layerCounter), CG.layerCounter);

}


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
        if ($(this).attr("id") !== "uploadForm") {
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

function showFileInfo(data, fileName) {
    $("#file-info table tbody tr").not(':first').remove();
    $('#file-info h4 span:nth-child(1)').text(fileName);
    $('#file-info h4 span:nth-child(2)').text(data.num_rows);

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

        console.log(row);
        $("#file-info tbody").append(row);
    }

    $("#file-info").show();
}

function addLayer(data, layerInfo) {
    var layerInfo = layerInfo || {};
    var cols = data.columns;
    var $elem = $("#layer-template")
        .clone()
        .removeAttr("id")
        .removeClass("hidden");

    // Replace "__NUM__" with index in layer ids
    var layerIndex = $("#layer-container div.layer").length;
    $elem.find("input,select,textarea")
        .each(function (i, elem) {
            var e = $(elem);
            var name = e.attr('name');
            if (/__NUM__/.test(name)) {
                e.attr('name', name.replace('__NUM__', layerIndex));
            }
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
    var getFieldInfo = function() {
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
    var fieldHandler = function() {
        var fi = getFieldInfo();
        $dataType.empty();
        if (fi.sequential) $dataType.append($("<option>sequential</option>"));
        if (fi.diverging) $dataType.append($("<option>diverging</option>"));
        if (fi.qualitative) $dataType.append($("<option>qualitative</option>"));
        // if ($dataType.children().length === 1) {
            $dataType.trigger('change');
        // }
    };
    $fields.on('change', fieldHandler);

    // Handler for changing the data type
    var dataTypeHandler = function() {
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
        // if ($numColors.children().length === 1) {
            $numColors.trigger('change');
        // }
    };
    $dataType.on("change", dataTypeHandler);

    // Handler for changing the number of colors
    var numColorHandler = function() {
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
        schemeNames[dt].forEach(function (n) {
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
            $schemes.append($schemeDiv);

            // Handler for selecting a specific color
            $schemeDiv.on('click', function() {
                $schemes.find('div.scheme').removeClass('active');
                $(this).addClass('active');
                $schemeName.val(n + '_' + nc);
            });
        });
    };
    $numColors.on("change", numColorHandler);

    $("#add-layer-button").before($elem);

    // Auto-populate the fields with the specified information
    if (cols.length === 0) {
        $fields.trigger('change');
    } else if (layerInfo.field) {
        $fields.val(layerInfo.field).trigger('change');
    }
    if (layerInfo.id) {
        $elem.find('.layer-id').val(layerInfo.id);
    }
    if (layerInfo.title) {
        $elem.find('.layer-title').val(layerInfo.title);
    }
    if (layerInfo.description) {
        $elem.find('.layer-description').val(layerInfo.description);
    }
    if (layerInfo.numColors) {
        $numColors.val(layerInfo.numColors).trigger('change');
    }
    if (layerInfo.colorScheme) {
        $numColors.val(layerInfo.numColors).trigger('change');
    }

    // Enable the user to remove the layer.
    // TODO:
    $elem.find(".layer-remove").on('click', function() {
        $elem.slideUp("slow", function() { $(this).remove(); });
    });

}

var schemeNames = {
    sequential: ["BuGn", "BuPu", "GnBu", "OrRd", "PuBu", "PuBuGn", "PuRd", "RdPu", "YlGn", "YlGnBu", "YlOrBr", "YlOrRd"],
    singlehue: ["Blues", "Greens", "Greys", "Oranges", "Purples", "Reds"],
    diverging: ["BrBG", "PiYG", "PRGn", "PuOr", "RdBu", "RdGy", "RdYlBu", "RdYlGn", "Spectral"],
    qualitative: ["Accent", "Dark2", "Paired", "Pastel1", "Pastel2", "Set1", "Set2", "Set3"]
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