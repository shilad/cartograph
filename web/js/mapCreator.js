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
        $("h2").append("<p>" + fileName + "</p>");
    });
    $("#submitFile").click(function () {
        $("h2").append("<h3>File being processed...</h3>");
    });

    $(".btn-generateMap").click(function () {
        $.post('/add_map/' + $("#map_name").val());
        $("h3").append("<p>Let's pretend this is a new page with a map...</p>");
        createMapDescription();
    });

    var uploadForm = $("#uploadForm");
    uploadForm.on('submit', function (event) {

        event.stopPropagation(); // Stop stuff happening
        event.preventDefault(); // Totally stop stuff happening

        // Declare a form data object
        var data = new FormData();
        data.append('map_name', $("#map_name").val());
        var file = uploadForm.find('input[type=file]')[0].files[0];
        data.append('file', file);

        // Perform Ajax call
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
        }, {}))

        $.ajax({
            url: '../add_map/' + $("#map_name").val(),
            type: 'POST',
            success: function (textStatus, jqXHR) {
                console.log('Done');
            },
        },)

    });

    var metricsForm = $("#metricsForm");
    metricsForm.on('submit', function (event) {
        event.stopPropagation(); // Stop stuff happening
        event.preventDefault(); // Totally stop stuff happening

        // Declare a form data object
        var metricData = new FormData();
        metricData.append('map_name', $("#map_name").val());
        metricData.append('title', metricsForm.find("textarea[name='title']").val());
        metricData.append('description', metricsForm.find("textarea[name='description']").val());
        metricData.append('field', metricsForm.find("select[name='field']").val());
        metricData.append('type', metricsForm.find("select[name='type']").val());
        metricData.append('color_scheme', metricsForm.find("input[name='color_scheme']").val() + "_" + metricsForm.find("select[name='num_classes']").val());

        // Perform Ajax call
        $.ajax($.extend({}, {
            url: metricsForm.attr('action'),
            type: 'POST',
            data: metricData,
            cache: false,
            processData: false, // Don't process the files, we're using FormData
            contentType: false, // Set content type to false as jQuery will tell the server its a query string request
            success: function (data, textStatus, jqXHR) {
                console.log(data);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.log(jqXHR, textStatus, errorThrown);
            }
        }, {}))

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
            var i = [3, 9];
        } else if (type === 'diverging') {
            var i = [3, 11];
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
                // console.log(d3.values(d).map(JSON.stringify).join("\n"));
                console.log(d3.values(d)[0]);
                $("#color-scheme").val(d3.values(d)[0]);
            })
            .selectAll(".swatch")
                .data(function(d) {return d.value;})
                .enter().append("span")
                .attr("class", "swatch")
                .style("background-color", function(d) { return d; });
}

var schemeNames = {sequential: ["BuGn","BuPu","GnBu","OrRd","PuBu","PuBuGn","PuRd","RdPu","YlGn","YlGnBu","YlOrBr","YlOrRd"],
					singlehue:["Blues","Greens","Greys","Oranges","Purples","Reds"],
					diverging: ["BrBG","PiYG","PRGn","PuOr","RdBu","RdGy","RdYlBu","RdYlGn","Spectral"],
					qualitative: ["Accent","Dark2","Paired","Pastel1","Pastel2","Set1","Set2","Set3"] };

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

function createMapDescription(){
   $("h3").append(description);
}