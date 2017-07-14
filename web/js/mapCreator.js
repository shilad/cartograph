/**
 * Created by sen on 6/29/17.
 */

$(document).ready(function(){
    var bar = $('.bar');
    var percent = $('.percent');
    var status = $('#status');
    $('#myForm').ajaxForm({
        beforeSend: function() {
            status.empty();
            var percentVal = '0%';
            bar.width(percentVal);
            percent.html(percentVal);
        },
        uploadProgress: function(event, position, total, percentComplete) {
            var percentVal = percentComplete + '%';
            bar.width(percentVal);
            percent.html(percentVal);
        },
        complete: function(xhr) {
            status.html(xhr.responseText);
        }
    });

    $('input[type="file"]').change(function(e){
            var fileName = e.target.files[0].name;
            $("h2").append("<p>" + fileName + "</p>");
    });
    $("#submitFile").click(function(){
        $("h2").append("<h3>File being processed...</h3>");
    });
    // $(".btn-addVisualization").click(function(){
    //     appendVisualizationRequirements();
    //     createSelectFields(data['columns']);
    //
    // });
    $(".btn-generateMap").click(function(){
        $("h3").append("<p>Let's pretend this is a new page with a map...</p>");
        createMapDescription();
    });

    var uploadForm = $("#uploadForm");
    uploadForm.on('submit', function(event) {

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
            success: function(data, textStatus, jqXHR){
                CG.uploadData = data;
                $("#mapConfig").show();
                $(".btn-addVisualization").click(function(){
                    appendVisualizationRequirements();
                    var dataCol = data.columns;
                    dataCol[0] = 'Fields';
                    createSelectFields(dataCol);
                });
            },
            error: function(jqXHR, textStatus, errorThrown){ console.log(jqXHR, textStatus, errorThrown); }
        }, {}))

    });

});

function createSelectFields(dataCol){
    var fields = document.getElementById("fields"), // get the select
        df = document.createDocumentFragment(); // create a document fragment to hold the options while we create them
    for (var i = 0; i < dataCol.length; i++) { // loop, i like 42.
        var option = document.createElement('option'); // create the option element
        option.value = dataCol[i]; // set the value property
        option.appendChild(document.createTextNode(dataCol[i])); // set the textContent in a safe way.
        df.appendChild(option); // append the option to the document fragment
    }
    fields.appendChild(df); // append the document fragment to the DOM
}


var fullColorDiv = [
    '<div id="scheme1" style="width: 100px;">',
    '<div id="ramps">',
    '<div class="ramp BuGn"><svg width="15" height="75">',
    '<rect fill="rgb(237,248,251)" width="15" height="15" y="0"></rect>',
    '<rect fill="rgb(178,226,226)" width="15" height="15" y="15"></rect>',
    '<rect fill="rgb(102,194,164)" width="15" height="15" y="30"></rect>',
    '<rect fill="rgb(44,162,95)" width="15" height="15" y="45"></rect>',
    '<rect fill="rgb(0,109,44)" width="15" height="15" y="60"></rect>',
    '</svg></div>',
    '<div class="ramp BuPu"><svg width="15" height="75">',
    '<rect fill="rgb(237,248,251)" width="15" height="15" y="0"></rect>',
    '<rect fill="rgb(179,205,227)" width="15" height="15" y="15"></rect>',
    '<rect fill="rgb(140,150,198)" width="15" height="15" y="30"></rect>',
    '<rect fill="rgb(136,86,167)" width="15" height="15" y="45"></rect>',
    '<rect fill="rgb(129,15,124)" width="15" height="15" y="60"></rect>',
    '</svg></div>',
    '<div class="ramp GnBu"><svg width="15" height="75">',
    '<rect fill="rgb(240,249,232)" width="15" height="15" y="0"></rect>',
    '<rect fill="rgb(186,228,188)" width="15" height="15" y="15"></rect>',
    '<rect fill="rgb(123,204,196)" width="15" height="15" y="30"></rect>',
    '<rect fill="rgb(67,162,202)" width="15" height="15" y="45"></rect>',
    '<rect fill="rgb(8,104,172)" width="15" height="15" y="60"></rect>',
    '</svg></div>',
    '</div>',
    '</div>'
    ].join("\n");

var newReqs = [
    '<div>',
    '<select class="selectpicker" id="fields"></select>',
    '<p></p>',
    '<select>',
        '<option value="Type">Type</option>',
        '<option value="Quantitative">Quantitative</option>',
        '<option value="Divergent">Divergent</option>',
        '<option value="Qualitative">Qualitative</option>',
    '</select>',
    '<p></p>',
    '<label>Pick a Color Scheme:</label>',
    fullColorDiv,
    '<br>',
    '<p></p>',
    '<p>',
        '<label>Title:</label>',
        '<textarea id = "Title"rows = "1"cols = "40">What do you want to call this visualization?</textarea>',
    '</p>',
    '<p>',
        '<label>Description:</label>',
        '<textarea id = "Description"rows = "3"cols = "40">This shows...</textarea>',
    '</p>',
    '<hr>',
    '</div>'
    ].join("\n");

function appendVisualizationRequirements(){
    $("#newRequirements").append(newReqs);
}

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




