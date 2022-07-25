var all_nav_links={"API Version":{"docs/0.15.3":["docs/0.15.2","docs/0.15.1","docs/0.15.0"],"docs/0.14.2":["docs/0.14.1","docs/0.14.0"],"docs/0.13.2":["docs/0.13.1","docs/0.13.0"],"docs/0.12.0":[],"docs/0.11.5":["docs/0.11.4","docs/0.11.3","docs/0.11.2","docs/0.11.1","docs/0.11.0"],"docs/0.10.1":["docs/0.10.0"],"docs/0.9.0":[],"docs/0.8.6":["docs/0.8.5","docs/0.8.4","docs/0.8.3","docs/0.8.2","docs/0.8.1","docs/0.8.0"],"docs/0.7.2":["docs/0.7.1","docs/0.7.0"],"docs/0.6.1":["docs/0.6.0"],"docs/0.5.1":[]},"Extras":["extras/Examples.html","extras/FAQ.html","extras/Installing On Linux.html","extras/Quick Start Guide.html"]};var mark_latest={"API Version":"docs/0.15.3"};function create_nav_link(item,hidden=false){var link=document.createElement("a");link.innerHTML=item.split("/").slice(-1).pop().replace('.html','');link.className="navigation";link.href=new URL(item,get_version_navigation_base_url()).href;var item=document.createElement("li");item.className="navigation";if(hidden===true){item.className+=" dropdown subversion";}
item.appendChild(link);return item;}
function toggle_subversions(div){for(elem of div.getElementsByClassName("subversion")){if(window.getComputedStyle(elem).getPropertyValue("display")==="none"){elem.style="display: inline-block;";}else{elem.style="display: none;";}}}
function toggle_btn_text(button){if(button.innerHTML==="+"){button.innerHTML="-";}else{button.innerHTML="+";}}
function create_dropdown_nav_link(version){var div=document.createElement('div');var expand_btn=document.createElement('button');expand_btn.innerHTML="+";expand_btn.onclick=function(){toggle_subversions(div);toggle_btn_text(expand_btn)};expand_btn.className="dropdown";div.appendChild(expand_btn);var nav_link=create_nav_link(version);nav_link.className="navigation dropdown";div.appendChild(nav_link);return div;}
function is_dict(v){return typeof v==='object'&&v!==null&&!(v instanceof Array);}
function create_navigation_menu(){if(Object.keys(all_nav_links).length>0){const navigator_div=document.getElementById("custom-version-navigation");for(const[category,nav_links]of Object.entries(all_nav_links)){var header=document.createElement('h2');header.innerHTML=category;navigator_div.appendChild(header);const navigator=document.createElement("ul");if(is_dict(nav_links)){for(const[link,sub_links]of Object.entries(nav_links)){if(sub_links.length===0){navigator.appendChild(create_nav_link(link));}else{var dropdown=create_dropdown_nav_link(link);for(var i=0;i<sub_links.length;i++){dropdown.appendChild(create_nav_link(sub_links[i],true));}
navigator.appendChild(dropdown);}}}else{for(var i=0;i<nav_links.length;i++){navigator.appendChild(create_nav_link(nav_links[i]));}}
navigator_div.appendChild(navigator);}}}
function spawn_outofdate_label(latest_url){var div=document.createElement("div");div.className="pdoc notice-marker";var latest=document.createElement("a");latest.href=latest_url;latest.innerHTML="This page is out of date. Click here to see the latest version";div.appendChild(latest);var main=document.getElementsByTagName("body")[0];main.appendChild(div);}
function check_outofdate(){loop1:for(const[category,latest]of Object.entries(mark_latest)){let latest_url=new URL(latest,get_version_navigation_base_url());if(window.location.href.startsWith(latest_url)){break;}
loop2:var to_check=all_nav_links[category];if(is_dict(all_nav_links[category])){to_check=Object.keys(to_check).concat(Object.values(to_check).flat());}
for(var i=0;i<to_check.length;i++){var url_stub=to_check[i];if(url_stub===latest){continue;}
if(window.location.href.startsWith(new URL(url_stub,get_version_navigation_base_url()))){spawn_outofdate_label(latest_url);break loop1;}}}}
create_navigation_menu();check_outofdate();