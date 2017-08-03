/**
 * Created by sen on 6/29/17.
 */

$(document).ready(function () {
    var bar = $('.bar');
    var percent = $('.percent');
    var status = $('#status');

    // Process the upload form after hitting "Submit" button
    var uploadForm = $("#uploadForm");
    // $('input[type="file"]').change(function (e) {
    //     uploadForm.submit();
    // });


    showUploadError = function(message) {
        $("#upload-error .alert").html(message).parent().show();
    };

    uploadForm.on('submit', function (event) {
        event.stopPropagation(); // Stop stuff happening
        event.preventDefault(); // Totally stop stuff happening

        $("#upload-error").hide();

        var mapName = $("#map_name").val();
        if (!/^[a-z0-9_]+$/i.test(mapName)) {
            showUploadError("Map name can only contain alphanumeric characters");
            return;
        }

        // Declare a form data object
        var data = new FormData();
        data.append('map_name', mapName);
        var file = uploadForm.find('input[type=file]')[0].files[0];
        var fileName = file.name;
        data.append('file', file);

        // Perform Ajax call to show add visualization part
        $.ajax($.extend({}, {
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
                console.log(data);
                CG.uploadData = data;
                CG.metricCounter = 0; // A counter of input metrics.
                createDataInfo(data, fileName);

                // Display Generate Map button that submits all metric forms
                $("#mapConfig").append(`<button type="submit" class="btn btn-generateMap" form="metricsForm0" value="GenerateMap" id="submitButton"> GENERATE MAP! </button>`)

                CG.mapBuilt = false;  // A boolean indicating whether the map has been built to avoid building it again when hitting GenerateMap
                $(`#submitButton`).click(function () {
                    // Build the map
                    if (! CG.mapBuilt) {
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

                // Show metric options after hitting addVisualization button.
                $(".btn-addVisualization").click(createNewMetricHtml);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR, textStatus, errorThrown);
            }
        }, {}));
    });
});

function createNewMetricHtml() {
    CG.metricCounter += 1;
    $("#newRequirements").show();
    appendVisualizationRequirements(CG.metricCounter);

    // Automatically fill in metric input fields.
    createSelectFields(CG.uploadData.columns, CG.metricCounter);
    createSelectTypes(document.getElementById("fields" + CG.metricCounter), CG.metricCounter);
    createNumClasses(document.getElementById("fields" + CG.metricCounter), document.getElementById("types" + CG.metricCounter), CG.metricCounter);
    createSelectPalettes(document.getElementById("types" + CG.metricCounter), document.getElementById("number-classes" + CG.metricCounter), CG.metricCounter);

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
    })
    $("h3").append("<p>Please wait while we create your map...</p>");
    // createMapDescription(vizName, vizDescription);

}

function submit_forms(){
    $('form').each(function () {
        if ($(this).attr("id") !== "uploadForm") {
            $(this).validate({errorElement: 'metricErrors',});  // Validate the form
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

function ajax_metrics(i) {
    // Ajax call to add the ith metric

    var metricsForm = $(`#metricsForm${i}`);
    event.stopPropagation(); // Stop stuff happening
    event.preventDefault(); // Totally stop stuff happening

    // Perform Ajax call to apply metric
    var metricData = {
        metric_name: $(`#title${i}`).val(),
        column: $(`#fields${i}`).val(),
        color_palette: $(`#color-scheme${i}`).val() + "_" + $(`#number-classes${i}`).val(),
        description: $(`#description${i}`).val()
    };

    $.ajax({
        url: '../' + $("#map_name").val() + '/add_metric/' + $(`#types${i}`).val(),
        type: 'POST',
        data: metricData,
        dataType: 'json',
        cache: false,
        processData: true,
        async: false,
        contentType: false, // Set content type to false as jQuery will tell the server its a query string request
        success: function (textStatus, jqXHR) {
            console.log("Successfully added metric to the map!");
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR, textStatus, errorThrown);
        }
    })
}

function createSelectFields(dataCol, count) {
    // Create a drop down list of fields
    var fields = document.getElementById("fields" + count), // get the select
        df = document.createDocumentFragment(); // create a document fragment to hold the options while we create them
    // dataCol[0] = 'Fields'
    for (var i = 1; i < dataCol.length; i++) {
        var option = document.createElement('option'); // create the option element
        option.value = dataCol[i]; // set the value property
        option.appendChild(document.createTextNode(dataCol[i])); // set the textContent in a safe way.
        df.appendChild(option); // append the option to the document fragment
    }
    fields.appendChild(df); // append the document fragment to the DOM
}

function createSelectTypes(fieldSelected, count) {
    // Create a drop down list of types
    var col = fieldSelected.selectedIndex + 1; // Start from index 1
    var types = document.getElementById("types" + count), // get the select
        df = document.createDocumentFragment(); // create a document fragment to hold the options while we create them
    // Remove child nodes of types from previously selected fields.
    while (types.firstChild) {
        types.removeChild(types.firstChild);
    }
    for (var key in CG.uploadData.types[col]) {
        if (CG.uploadData.types[col][key]) {
            var option = document.createElement('option');
            option.value = key;
            option.appendChild(document.createTextNode(key)); // set the textContent in a safe way.
            df.appendChild(option); // append the option to the document fragment
        }
    }
    types.appendChild(df); // append the document fragment to the DOM
}

function createNumClasses(fieldSelected, typeSelected, count) {
    // Create a drop down list to select the number of data classes
    var type = typeSelected.options[typeSelected.selectedIndex].value;
    var col = fieldSelected.selectedIndex;
    var numClasses = document.getElementById("number-classes" + count), // get the select
        df = document.createDocumentFragment(); // create a document fragment to hold the options while we create them
    // Remove child nodes of types from previously selected fields.
    while (numClasses.firstChild) {
        numClasses.removeChild(numClasses.firstChild);
    }
    if (type === 'qualitative') {
        var option = document.createElement('option');
        option.value = CG.uploadData.num_classes[col];
        option.appendChild(document.createTextNode(option.value)); // set the textContent in a safe way.
        df.appendChild(option);
    } else {
        if (type === 'sequential') {
            var i = [3, 9]; // Range of colorbrewer's palettes
        } else if (type === 'diverging') {
            var i = [3, 11]; // Range of colorbrewer's palettes
        }
        for (var j = i[0]; j <= i[1]; j++) {
            var option = document.createElement('option');
            option.value = j;
            option.appendChild(document.createTextNode(j)); // set the textContent in a safe way.
            df.appendChild(option);
        }
    }
    numClasses.appendChild(df); // append the document fragment to the DOM
}

function createSelectPalettes(typeSelected, numColorSelected, count) {
    // Display color palettes
    var type = typeSelected.options[typeSelected.selectedIndex].value;
    var numColor = numColorSelected.options[numColorSelected.selectedIndex].value;
    var scheme = {};
    for (var i = 0; i < schemeNames[type].length; i++) {
        scheme[schemeNames[type][i]] = colorbrewer[schemeNames[type][i]][numColor];
    }

    d3.select("body").select('.mapMaker-body').select("#newRequirements")
        .select("#newMetric" + count).selectAll(".palette").remove();  // Remove previously shown palette.

    d3.select('body').select('.mapMaker-body').select("#newRequirements").select("#newMetric" + count)
        .selectAll(".palette")
        .data(d3.entries(scheme))
        .enter().append("span")
        .attr("class", "palette")
        .attr("title", function (d) {
            return d;
        })
        .on("click", function (d) {
            console.log(d3.values(d)[0]);
            // Proceed if the color scheme is not disabled
            if (!$("#color-scheme" + count).prop("disabled")) {
                $("#color-scheme" + count).val(d3.values(d)[0]);
                // Change background color of selected palette
                d3.select(this.parentNode).selectAll(".palette").style("background-color", "#fff");
                d3.select(this).style("background-color", "Indigo");
            }
        })
        .selectAll(".swatch")
        .data(function (d) {
            return d.value;
        })
        .enter().append("span")
        .attr("class", "swatch")
        .style("background-color", function (d) {
            return d;
        });
}

function createDataInfo(dataObject, fileName){

    /**
     * Switch to html template element
     * @type {string}
     */
    var dataTitle = [
    '<div class="panel panel-data">',
        '<div class="panel-heading">',
          '<h2 class="panel-title">',
          '<font color="#E2E1D9">',
          fileName,
          '</font>',
          '</h2>',
        '</div>',
    '</div>'].join("\n");

    var dataTypes = "<table border=1 width=100%>";
    dataTypes += "<tr>";
    for(var i=0; i<dataObject.columns.length; i++) {
        dataTypes += "<td>";
        dataTypes += dataObject.columns[i] + " ";
        dataTypes += "</td>";
    }

    dataTypes += "</tr><tr>";
    dataTypes += "<td>";
    dataTypes += dataObject.types[0];
    dataTypes += "</td>";

    for(var i=1; i<dataObject.types.length; i++) {
        dataTypes += "<td>";
        if (dataObject.types[i].diverging && dataObject.types[i].sequential){
            dataTypes += "Diverging or Sequential " + "<br/>";
        }
        if (dataObject.types[i].qualitative){
            dataTypes += "Qualitative" + "<br/>";
        }
        dataTypes += "</td>";
    }
    dataTypes += "</tr>";
    dataTypes += "</table>";

    var dataInfo = [
    '<div class="panel panel-data">',
        '<div class="panel-body">',
          '<p></p>',
          '<p>Number of Rows:',
          dataObject.num_rows,
          '</p>',
          '<p>Errors that need repair:</p>',
        '</div>',
    '</div>',
    ].join("\n");

    $("#uploadInformation").append(dataTitle);
    $("#uploadInformation").append(dataTypes);
    $("#uploadInformation").append(dataInfo);
}

/**
 * TODO: remove template literals.
 * @param count
 */
function appendVisualizationRequirements(count) {
    var newReqs = $([
        `<div id="newMetric${count}">`,
        `<form onsubmit="ajax_metrics(${count}); return false;" id="metricsForm${count}">`,
        '<p>',
        '<label>Title:</label>',
        `<textarea required name="title" id = "title${count}" rows = "1" cols = "40" placeholder="What do you want to call this visualization?"></textarea>`,
        '</p>',
        '<p>',
        '<label>Description:</label>',
        `<textarea name="description" id = "description${count}" rows = "3" cols = "40" placeholder="This shows..."></textarea>`,
        '</p>',
        `<p> Pick a field <select required name="field" id="fields${count}" onchange="createSelectTypes(this, ${count}); createNumClasses(this, document.getElementById(\'types${count}\'), ${count}); createSelectPalettes(document.getElementById(\'types${count}\'),  document.getElementById(\'number-classes${count}\'), ${count});" > </select> </p>`,
        '<p></p>',
        `<p> Pick a type <select required name="type" id="types${count}" onchange="createNumClasses(document.getElementById(\'fields${count}\'), this, ${count}); createSelectPalettes(this, document.getElementById(\'number-classes${count}\'), ${count});"> </select></p>`,
        '<p></p>',
        `<p> Pick a number of data classes <select required name="num_classes" id="number-classes${count}" onchange="createSelectPalettes(document.getElementById(\'types${count}\'), this, ${count});"> </select></p>`,
        '<p></p>',
        `<input required type="text" name="color_scheme" id="color-scheme${count}" maxlength="20" placeholder="Color Scheme"/>`,
        '<hr>',
        '</form>',
        '</div>'
    ].join("\n"));
    $("#newRequirements").append(newReqs);
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