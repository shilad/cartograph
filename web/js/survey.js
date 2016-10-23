/*
 * survey.js
 * @author Bret Jackson
 */

function Survey(parentContainer) {
	this.parentContainer = parentContainer;
	this.tasks = parentContainer.find('.task');
	this.currentIndex = 0;

	var constraints = {
		task1 : {
			feedback : { presence: true, length : { minimum : 3 }}
		},
		task2 : {
			feedback : { presence: true, length : { minimum : 3 }}
		},
		task3 : {
			feedback : { presence: true, length : { minimum : 3 }}
		},
		customtheme1 : {
			age : { presence: true, numericality : true },
			gender: { presence: true },
			quick: { presence: true },
			explain: { presence: true },
			grouping: { presence: true },
			learned: { presence: true }
		},
		customtheme2 : {
			easy: { presence: true },
			fun: { presence: true },
			successful: { presence: true },
			editFreq: { presence: true },
			genderFreq: { presence: true }
		},
		customtheme3 : {
		}

	};
	
	// Randomize Task order
	this.tasks = shuffle(this.tasks);

	for (var i = 0; i < this.tasks.length; i++) {
		console.log($(this.tasks[i]).find("form label span"));
		$(this.tasks[i]).find("form label span").text("Task " + (i + 1) + " of 3");
	}

	// Add the questions last so they aren't randomized
	this.tasks.push($('#surveyQuestions1'));
	this.tasks.push($('#surveyQuestions2'));
	this.tasks.push($('#surveyQuestions3'));
	this.tasks.push($('#thankYou'));
	
	for(var i=0; i < this.tasks.length; i++){
		if( i == this.currentIndex ){
			$(this.tasks[i]).show();
		} else {
			$(this.tasks[i]).hide();
		}

	}
	
	this.next = function() {
		//this.scrollIntoView();
		var curTask = $(this.tasks[this.currentIndex]);
		var curForm = curTask.find("form")[0];
		var values = validate.collectFormValues(curForm);
		var result = validate(values, constraints[curForm.id]);
		var errorP = $(curForm).find("p.error");
		if (result) {
			var errorMsgs = [];
			for (var k in result) {
				if (result[k].length) {
					errorMsgs.push(htmlEncode(result[k][0]));
				}
			}
			errorP.html(errorMsgs.join('<br/>')).fadeIn(500);
			return this;
		}

		errorP.text('').hide();

		CG.log({ event : 'survey', 'formid' : curForm.id, values : values, index : this.currentIndex });

		var nextTask = (this.currentIndex < this.tasks.length-1)
			? $(this.tasks[this.currentIndex + 1])
			: null;

		curTask.fadeOut(200, function () {
			if (nextTask) nextTask.fadeIn(100);
		});
		this.currentIndex++;

		return this;
	};
	
	var thisSurvey = this;
	this.parentContainer.on('click', '[data-action=next]', function(e){
		e.preventDefault();
		thisSurvey.next();
	});
	
}

/**
 * HTML escape a string. From http://stackoverflow.com/a/1219983/141245
 * @param value
 * @returns {*|jQuery}
 */
function htmlEncode(value){
  //create a in-memory div, set it's inner text(which jQuery automatically encodes)
  //then grab the encoded contents back out.  The div never exists on the page.
  return $('<div/>').text(value).html();
}

//Fisher-Yates shuffle algorithm from http://stackoverflow.com/questions/2450954/how-to-randomize-shuffle-a-javascript-array
function shuffle(array) {
  var currentIndex = array.length, temporaryValue, randomIndex;

  // While there remain elements to shuffle...
  while (0 !== currentIndex) {

    // Pick a remaining element...
    randomIndex = Math.floor(Math.random() * currentIndex);
    currentIndex -= 1;

    // And swap it with the current element.
    temporaryValue = array[currentIndex];
    array[currentIndex] = array[randomIndex];
    array[randomIndex] = temporaryValue;
  }

  return array;
}

function showCartoDemo() {
	var cityHolder = $("#cityHolder")[0];

	introJs()
		.onbeforechange(function(targetElement) {
			if (targetElement == cityHolder) {
				$(cityHolder).show();
			} else {
				$(cityHolder).hide();
			}
		})
		.setOption('overlayOpacity', 0.5)
		.start();
}

$(document).ready(function() {
	$('#startStudyButton').click(function() {
		$('body').chardinJs('start'); // Show the directions
		$('#introContainer').hide();
		showCartoDemo();
	});
	CG.log({ event : 'startSurvey' });
});