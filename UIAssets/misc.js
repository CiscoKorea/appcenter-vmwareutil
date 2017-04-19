/*
	misc.js

	This file contains some miscellaneous JS functions.  
*/


/*
	getUrlVars
	
	Function to retrive the variables and their value passed by URL.
	For instance, if the URL is of the form .../getTenant.json?x=1&y=2,
	the output will be a JS dictionary {x:1, y:2}.
*/
function getUrlVars() {
    var vars = {};
    var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi,    
    function(m,key,value) {
      vars[key] = value;
    });
    return vars;
}


