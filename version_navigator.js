// DO NOT ALTER THIS LINE
var all_versions = ["0.11.3","0.11.2","0.11.1","0.11.0","0.10.1","0.10.0","0.9.0","0.8.6","0.8.5","0.8.4","0.8.3","0.8.2","0.8.1","0.8.0","0.7.2","0.7.1","0.7.0","0.6.1","0.6.0","0.5.1"];
// Used in gh-pages generation

function create_nav_link(version, name=null){
    // create the hyperlink
    var link = document.createElement("a");
    if (name === null){
        link.innerHTML = "v" + version;
    } else {
        link.innerHTML = name;
    }
    link.className = "navigation";
    link.href = new URL("docs/" + version, get_version_navigation_base_url()).href;

    // create the list item and append link to it
    var item = document.createElement("li");
    item.className = "navigation";
    item.appendChild(link);
    return item;
}

if (all_versions.length > 0){
    const navigator_div = document.getElementById("custom-version-navigation");

    // create header
    var header = document.createElement('h2');
    header.innerHTML = "Version";
    navigator_div.appendChild(header);

    // create the navigation UL
    const navigator = document.createElement("ul");

    navigator.appendChild(create_nav_link(all_versions[0], "Latest"));

    for (var i = 0; i < all_versions.length; i++){
        navigator.appendChild(create_nav_link(all_versions[i]));
    }

    navigator_div.appendChild(navigator);
}