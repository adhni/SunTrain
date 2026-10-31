(function(root) {
    'use strict';
    const catalogues = root.suntrainCatalogues || {en:{}, id:{}};
    let language = 'en';
    try { if (localStorage.getItem('suntrain-language') === 'id') language='id'; } catch (_) {}
    const sourceNames = new Set();
    const patterns = Object.keys(catalogues.en).filter(key=>key.includes('{')).map(key=>{
        const names=[];
        const expression=key.split(/(\{[^}]+\})/).map(part=>{
            if(part.startsWith('{') && part.endsWith('}')) { names.push(part.slice(1,-1)); return '(.+?)'; }
            return part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
        }).join('');
        return {key,names,expression:new RegExp('^'+expression+'$')};
    }).sort((a,b)=>b.key.replace(/\{[^}]+\}/g,'').length-a.key.replace(/\{[^}]+\}/g,'').length);
    function resolve(text) {
        if(typeof text!=='string' || sourceNames.has(text)) return null;
        if(Object.hasOwn(catalogues.en,text)) return {key:text,params:{}};
        for(const pattern of patterns) {
            const match=pattern.expression.exec(text);
            if(match) return {key:pattern.key,params:Object.fromEntries(pattern.names.map((name,i)=>[name,match[i+1]]))};
        }
        return null;
    }
    function t(key,params={}) {
        const value=catalogues[language]?.[key] ?? catalogues.en[key] ?? key;
        return String(value).replace(/\{([^}]+)\}/g,(match,name)=>params[name] ?? match);
    }
    function translate(text,sourceLanguage=language) {
        const value=resolve(text); if(!value)return text;
        for(const name of ['n','total','page','pages']) if(value.params[name] && /^\d[\d.,]*$/.test(value.params[name])) {
            const normalized=sourceLanguage==='id'?value.params[name].replaceAll('.','').replace(',','.'):value.params[name].replaceAll(',','');
            value.params[name]=Number(normalized).toLocaleString(language==='id'?'id-ID':'en-AU');
        }
        return t(value.key,value.params);
    }
    function bind(element,text,attribute=null) {
        if(!element) return;
        const value=resolve(text);
        const marker=attribute?'data-l10n-'+attribute:'data-l10n';
        if(value) { if(element.getAttribute(marker)!==text) element.setAttribute(marker,text); element.setAttribute("data-l10n-language",language); } else element.removeAttribute(marker);
        const rendered=translate(text);
        if(attribute) { if(element.getAttribute(attribute)!==String(rendered)) element.setAttribute(attribute,rendered); }
        else if(element.textContent!==String(rendered)) element.textContent=rendered;
    }
    function refresh() {
        document.documentElement.lang=language;
        for(const [selector,text] of Object.entries({'.maplibregl-ctrl-zoom-in':'Zoom in','.maplibregl-ctrl-zoom-out':'Zoom out','.maplibregl-ctrl-compass':'Reset bearing to north','.maplibregl-ctrl-attrib-button':'Toggle attribution'}))
            for(const element of document.querySelectorAll(selector)){bind(element,text,'aria-label');bind(element,text,'title');}
        const labels=['Home','Transport Replay','Overview'];
        document.querySelectorAll('#view-tabs .tab').forEach((element,index)=>{if(labels[index]) bind(element,labels[index]);});
        const placeholders={"home-place":"Find a place or airport…","replay-place":"Find a place or airport…","replay-modes":"All modes","replay-lines":"All routes / lines","replay-operators":"All operators / feeds","replay-directions":"All directions","replay-stations":"Any stop or station","replay-number":"e.g. 6200","replay-from-countries":"All countries","replay-to-countries":"All countries"};
        for(const [id,key] of Object.entries(placeholders)){
            const element=document.getElementById(id);
            if(element && element.dataset.locale!==language && root.dash_clientside?.set_props){
                element.dataset.locale=language;const props={placeholder:t(key)};
                if(id!=='replay-number')props.labels={search:t('Search'),clear_search:t('Clear search'),clear_selection:t('Clear selection'),no_options_found:t('No options found'),select_all:t('Select all'),deselect_all:t('Deselect all'),selected_count:t('{count} selected')};
                root.dash_clientside.set_props(id,props);
            }
        }
        for(const select of document.querySelectorAll('[data-language-select]')) select.value=language;
        for(const element of document.querySelectorAll('[data-l10n]')) {
            const text=translate(element.getAttribute('data-l10n'),element.getAttribute('data-l10n-language') || 'en');
            if(element.textContent!==text) element.textContent=text;
        }
        for(const attribute of ['title','placeholder','aria-label']) for(const element of document.querySelectorAll('[data-l10n-'+attribute+']')) {
            const text=translate(element.getAttribute('data-l10n-'+attribute));
            if(element.getAttribute(attribute)!==text) element.setAttribute(attribute,text);
        }
    }
    function setLanguage(value) {
        if(!['en','id'].includes(value)) return;
        language=value;
        try { localStorage.setItem('suntrain-language',value); } catch (_) {}
        refresh();
        document.dispatchEvent(new CustomEvent('suntrain:languagechange',{detail:{language:value}}));
    }
    root.suntrainI18n={t,translate,bind,refresh,setLanguage,sourceNames,
        get language(){return language;},get locale(){return language==='id'?'id-ID':'en-AU';},
        number:value=>Number(value).toLocaleString(language==='id'?'id-ID':'en-AU')};
    document.documentElement.lang=language;
    document.addEventListener('change',event=>{if(event.target.matches?.('[data-language-select]'))setLanguage(event.target.value);});
    function start(){
        refresh();let queued=false;
        new MutationObserver(()=>{if(!queued){queued=true;queueMicrotask(()=>{queued=false;refresh();});}})
            .observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['data-l10n','data-l10n-title','data-l10n-placeholder','data-l10n-aria-label']});
    }
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})(window);
