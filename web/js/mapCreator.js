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

    $(".btn-generateMap").click(function () {
        // Perform Ajax call to generate the map
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
        window.location.href = '../' + $("#map_name").val() + '/static/iui2017.html';
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
        console.log(file);
        console.log(data);

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

                $("#mapConfig").show();
                $("#map_name").prop('disabled', true);

                // Show metric options after hitting addVisualization button.
                $(".btn-addVisualization").click(function () {
                    $("#newRequirements").show();
                    CG.data = data;
                    // Automatically choose a field and corresponding data type.
                    createSelectFields(data.columns);
                    createSelectTypes(document.getElementById("fields"));
                    createNumClasses(document.getElementById("fields"), document.getElementById("types"));
                    createSelectPalettes(document.getElementById("types"), document.getElementById("number-classes"));
                });
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR, textStatus, errorThrown);
            }
        }, {}));

    });

    // Process the metric form after hitting Generate Map button
    var metricsForm = $("#metricsForm");
    metricsForm.on('submit', function (event) {
        event.stopPropagation(); // Stop stuff happening
        event.preventDefault(); // Totally stop stuff happening

        // Perform Ajax call to apply metric
        var metricData = {
            metric_name: $("#title").val(),
            column: $("#fields").val(),
            color_palette: $("#color-scheme").val() + "_" + $("#number-classes").val(),
            description: $("#description").val()
        };

        $.ajax({
            url: '../' + $("#map_name").val() + '/add_metric/' + $("#types").val(),
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
    });
});

function createSelectFields(dataCol){
    // Create a drop down list of fields
    var fields = document.getElementById("fields"), // get the select
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
    var types = document.getElementById("types"), // get the select
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
    var numClasses = document.getElementById("number-classes"), // get the select
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
    d3.select("body").selectAll(".palette").remove();  // Remove previously shown palette.
    d3.select('body').select('.container').select("#newRequirements")
        .selectAll(".palette")
            .data(d3.entries(scheme))
            .enter().append("span")
            .attr("class", "palette")
            .attr("title", function(d) { return d;})
            .on("click", function(d) {
                console.log(d3.values(d)[0]);
                $("#color-scheme").val(d3.values(d)[0]);
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


var schemeNames = {sequential: ["BuGn","BuPu","GnBu","OrRd","PuBu","PuBuGn","PuRd","RdPu","YlGn","YlGnBu","YlOrBr","YlOrRd"],
					singlehue:["Blues","Greens","Greys","Oranges","Purples","Reds"],
					diverging: ["BrBG","PiYG","PRGn","PuOr","RdBu","RdGy","RdYlBu","RdYlGn","Spectral"],
					qualitative: ["Accent","Dark2","Paired","Pastel1","Pastel2","Set1","Set2","Set3"] };

function createMapDescription(){
   $("h3").append(description);
}