(function(root){
    'use strict';
    const $=id=>document.getElementById(id), i18n=root.suntrainI18n;
    const date=iso=>new Date(iso+'T12:00:00Z');
    const iso=value=>value.toISOString().slice(0,10);
    const move=(day,n)=>{const value=date(day);value.setUTCDate(value.getUTCDate()+n);return iso(value);};
    const shiftMonth=(day,n)=>{const value=date(day), d=value.getUTCDate();value.setUTCDate(1);value.setUTCMonth(value.getUTCMonth()+n);const last=new Date(Date.UTC(value.getUTCFullYear(),value.getUTCMonth()+1,0)).getUTCDate();value.setUTCDate(Math.min(d,last));return iso(value);};
    if(typeof module!=='undefined' && module.exports)module.exports={date,iso,move,shiftMonth};
    if(!root.document)return;
    const format=(value,options)=>new Intl.DateTimeFormat(i18n.locale,{timeZone:'UTC',...options}).format(date(value));
    let selected,minimum,maximum,focused,month,opened=false,bound=false;
    function button(text,action){const b=document.createElement('button');b.type='button';b.textContent=text;b.addEventListener('click',action);return b;}
    function close(){opened=false;$('replay-calendar').hidden=true;$('replay-date-open').setAttribute('aria-expanded','false');$('replay-date-open').focus();}
    function focusDay(){ $('replay-calendar').querySelector('[data-date="'+focused+'"]')?.focus(); }
    function choose(value){root.dash_clientside.set_props('replay-date',{data:value});close();}
    function render(){
        if(!selected)return;
        $('replay-date-open').textContent=format(selected,{day:'numeric',month:'short',year:'numeric'});
        const badge=$('replay-period');if(badge)badge.textContent=minimum===maximum?format(minimum,{day:'numeric',month:'short',year:'numeric'}):format(minimum,{day:'numeric',month:'short',year:'numeric'})+' – '+format(maximum,{day:'numeric',month:'short',year:'numeric'});
        const host=$('replay-calendar');if(!opened)return;
        host.hidden=false;host.replaceChildren();host.setAttribute('role','dialog');host.setAttribute('aria-label',i18n.t('Calendar'));
        const head=document.createElement('div');head.className='calendar-navigation';
        const previous=button('‹',()=>{focused=shiftMonth(focused,-1);focused=focused<minimum?minimum:focused;month=focused.slice(0,7);render();focusDay();});
        previous.setAttribute('aria-label',i18n.t('Previous month'));previous.disabled=month<=minimum.slice(0,7);
        const next=button('›',()=>{focused=shiftMonth(focused,1);focused=focused>maximum?maximum:focused;month=focused.slice(0,7);render();focusDay();});
        next.setAttribute('aria-label',i18n.t('Next month'));next.disabled=month>=maximum.slice(0,7);
        const title=document.createElement('strong');title.textContent=format(month+'-01',{month:'long',year:'numeric'});title.setAttribute('aria-live','polite');
        head.append(previous,title,next);host.append(head);
        const grid=document.createElement('div');grid.className='calendar-grid';grid.setAttribute('role','grid');grid.setAttribute('aria-label',title.textContent);
        const first=month+'-01', offset=(date(first).getUTCDay()+6)%7;
        const header=document.createElement('div');header.setAttribute('role','row');
        for(let d=0;d<7;d++){const cell=document.createElement('span');cell.setAttribute('role','columnheader');cell.textContent=format(move('2024-01-01',d),{weekday:'short'});header.append(cell);}grid.append(header);
        for(let week=0;week<6;week++){
            const row=document.createElement('div');row.setAttribute('role','row');
            for(let day=0;day<7;day++){
                const value=move(first,week*7+day-offset), cell=button(String(date(value).getUTCDate()),()=>choose(value));
                cell.dataset.date=value;cell.setAttribute('role','gridcell');cell.setAttribute('aria-label',format(value,{weekday:'long',day:'numeric',month:'long',year:'numeric'}));
                cell.setAttribute('aria-selected',String(value===selected));cell.disabled=value<minimum||value>maximum||!value.startsWith(month);
                cell.tabIndex=value===focused?0:-1;
                cell.addEventListener('keydown',event=>{
                    let target;
                    if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))target=move(value,{ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[event.key]);
                    if(event.key==='Home')target=move(value,-((date(value).getUTCDay()+6)%7));
                    if(event.key==='End')target=move(value,6-((date(value).getUTCDay()+6)%7));
                    if(event.key==='PageUp'||event.key==='PageDown')target=shiftMonth(value,event.key==='PageUp'?-1:1);
                    if(target){event.preventDefault();focused=target<minimum?minimum:target>maximum?maximum:target;month=focused.slice(0,7);render();focusDay();}
                });row.append(cell);
            }grid.append(row);
        }host.append(grid,button(i18n.t('Close calendar'),close));
        position();
    }
    function position(){
        if(!opened)return;
        const host=$('replay-calendar'),control=$('replay-date-open').getBoundingClientRect();
        const width=host.offsetWidth,height=host.offsetHeight;
        host.style.left=Math.max(12,Math.min(control.left,root.innerWidth-width-12))+'px';
        host.style.top=Math.max(12,Math.min(control.bottom+6,root.innerHeight-height-12))+'px';
    }
    function bind(){
        if(bound)return;bound=true;
        $('replay-date-open').addEventListener('click',()=>{if(opened){close();return;}opened=true;focused=selected;month=selected.slice(0,7);$('replay-date-open').setAttribute('aria-expanded','true');render();focusDay();});
        $('replay-calendar').addEventListener('keydown',event=>{
            if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close();}
            if(event.key==='Tab'){
                const nodes=[...$('replay-calendar').querySelectorAll('button:not(:disabled)')].filter(n=>n.tabIndex>=0);
                const index=nodes.indexOf(document.activeElement);
                if(event.shiftKey&&index===0){event.preventDefault();nodes.at(-1).focus();}
                else if(!event.shiftKey&&index===nodes.length-1){event.preventDefault();nodes[0].focus();}
            }
        });
        document.addEventListener('suntrain:languagechange',()=>{const hadFocus=$('replay-calendar').contains(document.activeElement);render();if(hadFocus)focusDay();});
        document.addEventListener('keydown',event=>{if(opened && event.key==='Escape'){event.preventDefault();event.stopImmediatePropagation();close();}},true);
        root.addEventListener('resize',position);
        document.addEventListener('pointerdown',event=>{if(opened&&!event.target.closest('.replay-calendar-field')&&!event.target.closest('#replay-calendar')&&!event.target.closest('[data-language-select]'))close();});
    }
    root.dash_clientside=Object.assign({},root.dash_clientside,{suntrainCalendar:{sync:(value,min,max)=>{
        bind();const changed=selected!==value||minimum!==min||maximum!==max;
        selected=value;minimum=min;maximum=max;
        if(changed){focused=value;month=value.slice(0,7);}render();return {value,min,max};
    }}});
})(typeof window!=="undefined"?window:globalThis);
