/**
 * Created by sen on 6/29/17.
 */

$(document).ready(function() {
    var bar = $('.bar');
    var percent = $('.percent');
    var status = $('#status');
    $('#myForm').ajaxForm({
        beforeSend: function () {
            status.empty();
            var percentVal = '0%';
            bar.width(percentVal);
            percent.html(percentVal);
        },
        uploadProgress: function (event, position, total, percentComplete) {
            var percentVal = percentComplete + '%';
            bar.width(percentVal);
            percent.html(percentVal);
        },
        complete: function (xhr) {
            status.html(xhr.responseText);
        }
    });

    $('input[type="file"]').change(function (e) {
        var fileName = e.target.files[0].name;
        createDataSample(fileName);
    });

    // Process the upload form after hitting "Submit" button
    var uploadForm = $("#uploadForm");
    uploadForm.on('submit', function (event) {

        event.stopPropagation(); // Stop stuff happening
        event.preventDefault(); // Totally stop stuff happening

        // Declare a form data object
        var data = new FormData();
        data.append('map_name', $("#map_name").val());
        var file = uploadForm.find('input[type=file]')[0].files[0];
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
                console.log(data);
                CG.uploadData = data;
                CG.metricCounter = 0; // A counter of input metrics.

                // Display Generate Map button that submits all metric forms
                $("#mapConfig").append( `<button type="submit" class="btn btn-generateMap" form="metricsForm${CG.metricCounter}" value="GenerateMap" id="submitButton"> GENERATE MAP! </button>`)
                
                $(`#submitButton`).click(function(){
                    // Build the map
                    ajax_buildMap();
                    $('form').each(function(){
                        if ($(this).attr("id") !== "uploadForm") {
                            $(this).submit();
                        }
                    });
                    // window.location.href = '../' + $("#map_name").val() + '/static/iui2017.html';
                });

                $("#mapConfig").show();
                $("#map_name").prop('disabled', true);
                $("#uploadFile").prop('disabled', true);

                // Show metric options after hitting addVisualization button.
                $(".btn-addVisualization").click(function () {
                    CG.metricCounter += 1;
                    CG.data = data;
                    $("#newRequirements").show();
                    appendVisualizationRequirements(CG.metricCounter);

                    // Automatically fill in metric input fields.
                    createSelectFields(data.columns);
                    createSelectTypes(document.getElementById("fields"+ CG.metricCounter));
                    createNumClasses(document.getElementById("fields"+ CG.metricCounter), document.getElementById("types" + CG.metricCounter));
                    createSelectPalettes(document.getElementById("types"+ CG.metricCounter), document.getElementById("number-classes" + CG.metricCounter));
                })
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR, textStatus, errorThrown);
            }
        }, {}));
    });
});

function ajax_buildMap(){
    // Ajax call to build the map
    $.ajax({
        url: '../add_map/' + $("#map_name").val(),
        type: 'POST',
        success: function (textStatus, jqXHR) {
            console.log('Successfully generated a map!');
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR, textStatus, errorThrown);
        }
    });
    $("h3").append("<p>Please wait while we create your map...</p>");
}

function ajax_metrics(i){
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
        contentType: false, // Set content type to false as jQuery will tell the server its a query string request
        success: function (textStatus, jqXHR) {
            console.log("Successfully added metric to the map!");
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log(jqXHR, textStatus, errorThrown);
        }
    })
}

function createSelectFields(dataCol){
    // Create a drop down list of fields
    var fields = document.getElementById("fields" + CG.metricCounter), // get the select
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

function createSelectTypes(fieldSelected){
    // Create a drop down list of types
    var col = fieldSelected.selectedIndex + 1; // Start from index 1
    var types = document.getElementById("types"+ CG.metricCounter), // get the select
        df = document.createDocumentFragment(); // create a document fragment to hold the options while we create them
    // Remove child nodes of types from previously selected fields.
    while (types.firstChild) {
        types.removeChild(types.firstChild);
    }
    for (var key in CG.uploadData.types[col]) {
        if (CG.uploadData.types[col][key]){
            var option = document.createElement('option');
            option.value = key;
            option.appendChild(document.createTextNode(key)); // set the textContent in a safe way.
            df.appendChild(option); // append the option to the document fragment
        }
    }
    types.appendChild(df); // append the document fragment to the DOM
}

function createNumClasses(fieldSelected, typeSelected){
    // Create a drop down list to select the number of data classes
    var type = typeSelected.options[typeSelected.selectedIndex].value;
    var col = fieldSelected.selectedIndex;
    var numClasses = document.getElementById("number-classes"+ CG.metricCounter), // get the select
        df = document.createDocumentFragment(); // create a document fragment to hold the options while we create them
    // Remove child nodes of types from previously selected fields.
    while (numClasses.firstChild) {
        numClasses.removeChild(numClasses.firstChild);
    }
    if (type === 'qualitative'){
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
        for (var j = i[0]; j <= i[1]; j++){
            var option = document.createElement('option');
            option.value = j;
            option.appendChild(document.createTextNode(j)); // set the textContent in a safe way.
            df.appendChild(option);
        }
    }
    numClasses.appendChild(df); // append the document fragment to the DOM
}

function createSelectPalettes(typeSelected, numColorSelected){
    // Display color palettes
    var type = typeSelected.options[typeSelected.selectedIndex].value;
    var numColor = numColorSelected.options[numColorSelected.selectedIndex].value;
    var scheme = {};
    for (var i = 0; i < schemeNames[type].length; i++) {
        scheme[schemeNames[type][i]] = colorbrewer[schemeNames[type][i]][numColor];
    }

    d3.select("body").select('.container').select("#newRequirements")
        .select("#newMetric" + CG.metricCounter).selectAll(".palette").remove();  // Remove previously shown palette.

    d3.select('body').select('.container').select("#newRequirements").select("#newMetric" + CG.metricCounter)
        .selectAll(".palette")
            .data(d3.entries(scheme))
            .enter().append("span")
            .attr("class", "palette")
            .attr("title", function(d) { return d;})
            .on("click", function(d) {
                console.log(d3.values(d)[0]);
                $("#color-scheme" + CG.metricCounter).val(d3.values(d)[0]);
                // Change background color of selected palette
                d3.select(this.parentNode).selectAll(".palette").style("background-color", "#fff");
                d3.select(this).style("background-color", "Indigo");
            })
            .selectAll(".swatch")
                .data(function(d) {return d.value;})
                .enter().append("span")
                .attr("class", "swatch")
                .style("background-color", function(d) { return d; });
}

function createDataSample(fileName){

    var dataSample = [
    '<div class="panel panel-data">',
            '<div class="panel-heading">',
              '<h2 class="panel-title">',
              fileName,
              '</h2>',
            '</div>',
            '<div class="panel-body">',
              '<p>Number of Columns:</p>',
              '<p>Number of Rows:</p>',
              '<p>Types of Data:</p>',
              '<p>Errors that need repair:</p>',
            '</div>',
    '</div>',
    ].join("\n");

    $("#uploadInformation").append(dataSample);
}

function appendVisualizationRequirements(count){
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
                '<hr>',
                `<p> Pick a field <select required name="field" id="fields${count}" onchange="createSelectTypes(this); createNumClasses(this, document.getElementById(\'types${count}\')); createSelectPalettes(document.getElementById(\'types${count}\'),  document.getElementById(\'number-classes${count}\'));" > </select> </p>`,
                '<p></p>',
                `<p> Pick a type <select required name="type" id="types${count}" onchange="createNumClasses(document.getElementById(\'fields${count}\'), this); createSelectPalettes(this, document.getElementById(\'number-classes${count}\'));"> </select></p>`,
                '<p></p>',
                `<p> Pick a number of data classes <select required name="num_classes" id="number-classes${count}" onchange="createSelectPalettes(document.getElementById(\'types${count}\'), this);"> </select></p>`,
                '<p></p>',
                `<input required type="text" name="color_scheme" id="color-scheme${count}" maxlength="20" placeholder="Color Scheme"/>`,
                '<hr>',
            '</form>',
        '</div>'
    ].join("\n"));
    $("#newRequirements").append(newReqs);
}


var schemeNames = {sequential: ["BuGn","BuPu","GnBu","OrRd","PuBu","PuBuGn","PuRd","RdPu","YlGn","YlGnBu","YlOrBr","YlOrRd"],
					singlehue:["Blues","Greens","Greys","Oranges","Purples","Reds"],
					diverging: ["BrBG","PiYG","PRGn","PuOr","RdBu","RdGy","RdYlBu","RdYlGn","Spectral"],
					qualitative: ["Accent","Dark2","Paired","Pastel1","Pastel2","Set1","Set2","Set3"] };

function createMapDescription(){
   $("h3").append(description);
}