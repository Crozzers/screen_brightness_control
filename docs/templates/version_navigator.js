// DO NOT ALTER THESE LINES
var all_nav_links = {};
var mark_latest = {};
// Used in gh-pages generation

function newElement(parent, elem){
    var element = document.createElement(elem);
    parent.appendChild(element);
    return element;
}

function navLink(link){
    var name = link.split("/").slice(-1).pop().replace('.html', '');
    var url = new URL(link, get_version_navigation_base_url()).href;
    return [name, url];
}

class Menu{
    constructor(parent){
        this.container = newElement(parent, "ul");
        this.frame = this.container;
        this._numItems = 0;
    }

    addItem(item){
        this._incrementItemCount();
        var [name, href] = navLink(item);

        var listItem = newElement(this.frame, "li");
        listItem.className = "navigation";

        var item = newElement(listItem, "a");
        item.className = "navigation";
        item.href = href;
        item.innerHTML = name;
    }

    addItems(items){
        for (const item of items){
            this.addItem(item);
        }
    }

    addSubMenu(){
        this._incrementItemCount();
        var subMenu = new SubMenu(this.frame);
        return subMenu;
    }

    _incrementItemCount(){
        if (this._numItems === 5){
            this.frame = newElement(this.frame, "details");
            newElement(this.frame, "summary").innerHTML = "More";
        }
        this._numItems += 1
    }
}

class SubMenu{
    constructor(parent){
        this.container = newElement(parent, "div");
        this.button = newElement(this.container, "button");
        this.button.innerHTML = "+";
        this.button.className = "dropdown";
        this.button.onclick = this.toggleHidden();
    }

    addItem(item, is_title_item=false){
        var [name, href] = navLink(item);

        var listItem = newElement(this.container, "li");
        listItem.className = "navigation dropdown";
        if (!is_title_item){
            listItem.className += " subversion";
        }

        var item = newElement(listItem, "a");
        item.className = "navigation";
        item.href = href;
        item.innerHTML = name;
    }

    addItems(items, title_item=null){
        if (title_item !== null){
            this.addItem(title_item, true);
        }
        for (const item of items){
            this.addItem(item);
        }
    }

    toggleHidden(){
        let subMenu = this;
        return function(){
            if (subMenu.button.innerHTML === "+"){
                subMenu.button.innerHTML = "-";
            } else {
                subMenu.button.innerHTML = "+";
            }

            for (const elem of subMenu.container.getElementsByClassName("subversion")){
                if (window.getComputedStyle(elem).getPropertyValue("display") === "none"){
                    elem.style.display = "inline-block";
                } else {
                    elem.style.display = "none";
                }
            }
        }
    }
}

function is_dict(v) {
    return typeof v==='object' && v!==null && !(v instanceof Array);
}

function create_navigation_menu(){
    if (Object.keys(all_nav_links).length <= 0){
        return;
    } 

    const navigator_div = document.getElementById("custom-version-navigation");

    for (const [category, nav_links] of Object.entries(all_nav_links)){
        newElement(navigator_div, 'h2').innerHTML = category;

        const menu = new Menu(navigator_div);

        if (is_dict(nav_links)){
            for (const [link, sub_links] of Object.entries(nav_links)){
                if (sub_links.length === 0){
                    menu.addItem(link);
                    continue;
                }

                let subMenu = menu.addSubMenu();
                subMenu.addItems(sub_links, link);
            }
        } else {
            menu.addItems(nav_links);
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