// DO NOT ALTER THIS LINE
var all_versions = {};
// Used in gh-pages generation

function create_nav_link(version, hidden=false){
    // create the hyperlink
    var link = document.createElement("a");
    link.innerHTML = "v" + version;
    link.className = "navigation";
    link.href = new URL("docs/" + version, get_version_navigation_base_url()).href;

    // create the list item and append link to it
    var item = document.createElement("li");
    item.className = "navigation";
    if (hidden === true){
        item.className += " dropdown subversion";
    }
    item.appendChild(link);
    return item;
}

function toggle_subversions(div){
    for (elem of div.getElementsByClassName("subversion")){
        if (window.getComputedStyle(elem).getPropertyValue("display") === "none"){
            elem.style = "display: inline-block;";
        } else {
            elem.style = "display: none;";
        }
    }
}

function toggle_btn_text(button){
    if (button.innerHTML === "+"){
        button.innerHTML = "-";
    } else {
        button.innerHTML = "+";
    }
}

function create_dropdown_nav_link(version){
    var div = document.createElement('div');

    var expand_btn = document.createElement('button');
    expand_btn.innerHTML = "+";
    expand_btn.onclick = function(){toggle_subversions(div);toggle_btn_text(expand_btn)};
    expand_btn.className = "dropdown";
    div.appendChild(expand_btn);

    var nav_link = create_nav_link(version);
    nav_link.className = "navigation dropdown";
    div.appendChild(nav_link);

    return div;
}

if (Object.keys(all_versions).length > 0){
    const navigator_div = document.getElementById("custom-version-navigation");

    // create header
    var header = document.createElement('h2');
    header.innerHTML = "Version";
    navigator_div.appendChild(header);

    // create the navigation UL
    const navigator = document.createElement("ul");

    for (const [version, elders] of Object.entries(all_versions)){
        if (elders.length === 0){
            navigator.appendChild(create_nav_link(version));
        } else {
            var dropdown = create_dropdown_nav_link(version);
            for (var i = 0; i < elders.length; i++){
                dropdown.appendChild(create_nav_link(elders[i], true));
            }
            navigator.appendChild(dropdown);
        }
    }

    navigator_div.appendChild(navigator);
}