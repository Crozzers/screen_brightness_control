var all_nav_links={"API Version":{"docs/0.21.0":[],"docs/0.20.0":[],"docs/0.19.0":[],"docs/0.18.0":[],"docs/0.17.0":[],"docs/0.16.2":["docs/0.16.1","docs/0.16.0"],"docs/0.15.5":["docs/0.15.4","docs/0.15.3","docs/0.15.2","docs/0.15.1","docs/0.15.0"],"docs/0.14.2":["docs/0.14.1","docs/0.14.0"],"docs/0.13.2":["docs/0.13.1","docs/0.13.0"],"docs/0.12.0":[],"docs/0.11.5":["docs/0.11.4","docs/0.11.3","docs/0.11.2","docs/0.11.1","docs/0.11.0"],"docs/0.10.1":["docs/0.10.0"],"docs/0.9.0":[],"docs/0.8.6":["docs/0.8.5","docs/0.8.4","docs/0.8.3","docs/0.8.2","docs/0.8.1","docs/0.8.0"],"docs/0.7.2":["docs/0.7.1","docs/0.7.0"],"docs/0.6.1":["docs/0.6.0"],"docs/0.5.1":[]},"Extras":["extras/Examples.html","extras/FAQ.html","extras/Installing On Linux.html","extras/Quick Start Guide.html"]};var mark_latest={"API Version":"docs/0.21.0"};function newElement(parent,elem){var element=document.createElement(elem);parent.appendChild(element);return element;}
function navLink(link){var name=link.split("/").slice(-1).pop().replace('.html','');var url=new URL(link,get_version_navigation_base_url()).href;return[name,url];}
class Menu{constructor(parent){this.container=newElement(parent,"ul");this.frame=this.container;this._numItems=0;}
addItem(item){this._incrementItemCount();var[name,href]=navLink(item);var listItem=newElement(this.frame,"li");listItem.className="navigation";var item=newElement(listItem,"a");item.className="navigation";item.href=href;item.innerHTML=name;}
addItems(items){for(const item of items){this.addItem(item);}}
addSubMenu(){this._incrementItemCount();var subMenu=new SubMenu(this.frame);return subMenu;}
_incrementItemCount(){if(this._numItems===5){this.frame=newElement(this.frame,"details");newElement(this.frame,"summary").innerHTML="More";}
this._numItems+=1}}
class SubMenu{constructor(parent){this.container=newElement(parent,"div");this.button=newElement(this.container,"button");this.button.innerHTML="+";this.button.className="dropdown";this.button.onclick=this.toggleHidden();}
addItem(item,is_title_item=false){var[name,href]=navLink(item);var listItem=newElement(this.container,"li");listItem.className="navigation dropdown";if(!is_title_item){listItem.className+=" subversion";}
var item=newElement(listItem,"a");item.className="navigation";item.href=href;item.innerHTML=name;}
addItems(items,title_item=null){if(title_item!==null){this.addItem(title_item,true);}
for(const item of items){this.addItem(item);}}
toggleHidden(){let subMenu=this;return function(){if(subMenu.button.innerHTML==="+"){subMenu.button.innerHTML="-";}else{subMenu.button.innerHTML="+";}
for(const elem of subMenu.container.getElementsByClassName("subversion")){if(window.getComputedStyle(elem).getPropertyValue("display")==="none"){elem.style.display="inline-block";}else{elem.style.display="none";}}}}}
function is_dict(v){return typeof v==='object'&&v!==null&&!(v instanceof Array);}
function create_navigation_menu(){if(Object.keys(all_nav_links).length<=0){return;}
const navigator_div=document.getElementById("custom-version-navigation");for(const[category,nav_links]of Object.entries(all_nav_links)){newElement(navigator_div,'h2').innerHTML=category;const menu=new Menu(navigator_div);if(is_dict(nav_links)){for(const[link,sub_links]of Object.entries(nav_links)){if(sub_links.length===0){menu.addItem(link);continue;}
let subMenu=menu.addSubMenu();subMenu.addItems(sub_links,link);}}else{menu.addItems(nav_links);}}}
function spawn_outofdate_label(latest_url){var div=document.createElement("div");div.className="pdoc notice-marker";var latest=document.createElement("a");latest.href=latest_url;latest.innerHTML="This page is out of date. Click here to see the latest version";div.appendChild(latest);var main=document.getElementsByTagName("body")[0];main.appendChild(div);}
function check_outofdate(){loop1:for(const[category,latest]of Object.entries(mark_latest)){let latest_url=new URL(latest,get_version_navigation_base_url());if(window.location.href.startsWith(latest_url)){break;}
loop2:var to_check=all_nav_links[category];if(is_dict(all_nav_links[category])){to_check=Object.keys(to_check).concat(Object.values(to_check).flat());}
for(var i=0;i<to_check.length;i++){var url_stub=to_check[i];if(url_stub===latest){continue;}
if(window.location.href.startsWith(new URL(url_stub,get_version_navigation_base_url()))){spawn_outofdate_label(latest_url);break loop1;}}}}
create_navigation_menu();check_outofdate();