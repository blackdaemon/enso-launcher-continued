var enso = {
  init: function() {
    var as = document.getElementsByTagName("a");
    for (var i=0; i<as.length; i++) {
      var main = as[i];
      if (main.rel != "ensocommand")
        continue;
      var form = document.createElement("form");
      form.action = "http://localhost:31750/";
      form.method = "POST";
      form.style.display = "inline";
      var inp = document.createElement("input");
      inp.type = "hidden"; inp.name = "url"; inp.value = main.href;
      var sub = document.createElement("input");
      sub.type = "submit"; sub.value = "Install";
      sub.className = "button enso-install-button";
      sub.title = "Pressing this button will install the command in Enso";
      form.appendChild(inp); form.appendChild(sub);
      var ifr = document.createElement("iframe");
      var ran = (new Date).getTime() + "_" + parseInt(Math.random()*10000);
      form.target = ran;
      ifr.name = ran;
      ifr.style.display = "none";
      if (main.nextSibling) {
        main.parentNode.insertBefore(ifr, main.nextSibling);
        main.parentNode.insertBefore(form, main.nextSibling);
      } else {
        main.parentNode.appendChild(form);
        main.parentNode.appendChild(ifr);
      }
    }
  }
};
(function(i) {var u =navigator.userAgent;var e=/*@cc_on!@*/false; var st =
setTimeout;if(/webkit/i.test(u)){st(function(){var dr=document.readyState;
if(dr=="loaded"||dr=="complete"){i()}else{st(arguments.callee,10);}},10);}
else if((/mozilla/i.test(u)&&!/(compati)/.test(u)) || (/opera/i.test(u))){
document.addEventListener("DOMContentLoaded",i,false); } else if(e){     (
function(){var t=document.createElement('doc:rdy');try{t.doScroll('left');
i();t=null;}catch(e){st(arguments.callee,0);}})();}else{window.onload=i;}})(enso.init);

