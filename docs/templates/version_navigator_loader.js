var url = new URL("version_navigator.js", get_version_navigation_base_url());

console.log(url);

window.onload = function(){
    var s = document.createElement("script");
    s.type = "text/javascript";
    s.src = url;
    document.getElementById("custom-version-navigation").appendChild(s);
}