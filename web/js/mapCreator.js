/**
 * Created by sen on 6/29/17.
 */

$(document).ready(function(){
    $("#uploadFile").click(function(){
        $("h2").append("<p>File being processed...</p>");
    });
    $("#submitFile").click(function(){
        $("h2").append("<p>File being processed...</p>");
    });
    $(".btn-addVisualization").click(function(){
        appendVisualizationRequirements();
    });
    $(".btn-generateMap").click(function(){
        $("h3").append("<p>Let's pretend this is a new page with a map...</p>");
    });
});


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
    '<select>',
        '<option value="Field">Field</option>',
    '</select>',
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




