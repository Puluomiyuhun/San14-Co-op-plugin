from pathlib import Path
p=Path('work/mod_research/checkpoint_native_task_provider_fixture.cpp')
s=p.read_text();s=s.replace('    tp::Config pcfg{};', '#undef session\n    tp::Config pcfg{};').replace('    check(provider.Register(pcfg)', '#define session (*currentSession)\n    check(provider.Register(pcfg)');p.write_text(s)
p=Path('work/mod_research/checkpoint_native_task_provider.cpp');s=p.read_text()
s=s.replace('if(v.report.loadBound&&belongs){b=&v;rva=off;break;}', '''if(v.report.loadBound&&belongs&&!v.report.closed){
                const unsigned role=off==0x4F7079?0:off==0x4AAF64?1:2;
                if((off==0x4CC690&&v.report.titleCallback)||((off==0x4F7079||off==0x4AAF64||off==0x4AAF89)&&v.report.roles[role].joined))continue;
                if(roleMatch)return reject(&v,Error::Order);roleMatch=&v;roleRva=off;}''')
s=s.replace('    if(!active){for(unsigned i=0;', '    Bank*roleMatch=nullptr;std::uint64_t roleRva=0;\n    if(!active){for(unsigned i=0;')
s=s.replace('    NEED(b,Window);++b->report.events;++sequence_;', '    if(roleMatch){b=roleMatch;rva=roleRva;}\n    NEED(b,Window);++sequence_;')
# count accepted-events only after final bank association. Creation branch b already uniquely selected.
s=s.replace('b->selected=true;', '++b->report.events;b->selected=true;').replace('b->selected=false;return record', '++b->report.events;b->selected=false;return record')
s=s.replace('b->report.loadBound=1;', '++b->report.events;b->report.loadBound=1;').replace('b->report.titleCallback=1;', '++b->report.events;b->report.titleCallback=1;')
s=s.replace('w.creation=t.serial;', '++b->report.events;w.creation=t.serial;').replace('t->entered=true;', '++b->report.events;t->entered=true;')
s=s.replace('b->report.roles[role].payloadEntry=sequence_;', '++b->report.events;b->report.roles[role].payloadEntry=sequence_;')
s=s.replace('active->returned=true;', '++b->report.events;active->returned=true;').replace('t->done=true;', '++b->report.events;t->done=true;').replace('t->complete=true;', '++b->report.events;t->complete=true;')
s=s.replace('        if(b.report.threeJoins', '        bool drained=!b.selected;for(unsigned j=0;j<b.count;++j)drained=drained&&b.records[j].complete;\n        if(drained&&b.report.threeJoins')
p.write_text(s)
