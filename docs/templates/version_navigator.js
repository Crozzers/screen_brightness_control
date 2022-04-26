// DO NOT ALTER THESE LINES
var all_nav_links = {};
var mark_latest = {};
// Used in gh-pages generation

function create_nav_link(item, hidden=false){
    // create the hyperlink
    var link = document.createElement("a");
    link.innerHTML = item.split("/").slice(-1).pop().replace('.html', '');
    link.className = "navigation";
    link.href = new URL(item, get_version_navigation_base_url()).href;

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

function is_dict(v) {
    return typeof v==='object' && v!==null && !(v instanceof Array);
}

function create_navigation_menu(){
    if (Object.keys(all_nav_links).length > 0){
        const navigator_div = document.getElementById("custom-version-navigation");

        for (const [category, nav_links] of Object.entries(all_nav_links)){
            // create header
            var header = document.createElement('h2');
            header.innerHTML = category;
            navigator_div.appendChild(header);

            // create the navigation UL
            const navigator = document.createElement("ul");

            if (is_dict(nav_links)){
                for (const [link, sub_links] of Object.entries(nav_links)){
                    if (sub_links.length === 0){
                        navigator.appendChild(create_nav_link(link));
                    } else {
                        var dropdown = create_dropdown_nav_link(link);
                        for (var i = 0; i < sub_links.length; i++){
                            dropdown.appendChild(create_nav_link(sub_links[i], true));
                        }
                        navigator.appendChild(dropdown);
                    }
                }
            }else{
                for (var i = 0; i < nav_links.length; i++){
                    navigator.appendChild(create_nav_link(nav_links[i]));
                }
            }

            navigator_div.appendChild(navigator);
        }
    }
}

function spawn_outofdate_label(latest_url){
    var div = document.createElement("div");
    div.className = "pdoc notice-marker";

    var latest = document.createElement("a");
    latest.href = latest_url;
    latest.innerHTML = "This page is out of date. Click here to see the latest version";
    div.appendChild(latest);

    var main = document.getElementsByTagName("body")[0];
    main.appendChild(div);
}

function check_outofdate(){
    // check if this page is out of date and mark it if so
    loop1:
        for (const [category, latest] of Object.entries(mark_latest)){
            let latest_url = new URL(latest, get_version_navigation_base_url());
            if (window.location.href.startsWith(latest_url)){
                // if we are at the latest URL then exit
                break;
            }
            loop2:
                var to_check = all_nav_links[category];
                if (is_dict(all_nav_links[category])){
                    to_check = Object.keys(to_check).concat(Object.values(to_check).flat());
                }

                for (var i = 0; i < to_check.length; i++){
                    var url_stub = to_check[i];
                    if (url_stub === latest){
                        // if url stub is the latest then ignore
                        continue;
                    }
                    if (window.location.href.startsWith(new URL(url_stub, get_version_navigation_base_url()))){
                        // if our URL starts with a stub that isn't the latest, then exit
                        spawn_outofdate_label(latest_url);
                        break loop1;
                    }
                }
        }
}

create_navigation_menu();
check_outofdate();