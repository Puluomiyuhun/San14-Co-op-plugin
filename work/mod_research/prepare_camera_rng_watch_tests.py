from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'camera_route_payload_fixture.cpp').read_text(encoding='utf-8').replace('observe_camera_route.cpp','observe_camera_rng_watch.cpp')
s=s.replace('c.Rip=base+0x3aa805;c.Rax=5678;c.Rcx=3;put<uint32_t>(base+0x18eb8b0,1234);',
'''c.Rip=base+0x3aa80b;c.Dr6=4;c.Rax=5678;c.Rcx=3;
        rngAddress=base+0x18eb8b0;previousObservedRng=1234;put<uint32_t>(rngAddress,5678);''')
s=s.replace('c.Rip=base+0x3f9344;', 'c.Dr6=0;c.Rip=base+0x3f9344;')
# Two other known stores and an unknown writer: classification uses a data watch,
# never a hard-coded list of RNG helper functions.
s=s.replace('        put<uint8_t>(world+0x37,21);', '''        c.Dr6=4;
        for(uint64_t ip:{uint64_t(0x3aa3db),uint64_t(0x3aa441),uint64_t(0x3aa3e6),uint64_t(0x101010)}){
            c.Rip=base+ip;put<uint32_t>(rngAddress,rd<uint32_t>(GetCurrentProcess(),rngAddress)+1);
            if(observe(stdout,GetCurrentProcess(),base,c,1))return 10;
        }
        put<uint8_t>(world+0x37,21);''')
(ROOT/'camera_rng_watch_payload_fixture.cpp').write_text(s,encoding='utf-8')

s=(ROOT/'test_pending_watch_observer.py').read_text(encoding='utf-8')
s=s.replace('observe_pending_writes.exe','observe_camera_rng_watch.exe')
s=s.replace('*[hex(x) for x in info[\'rvas\']],','hex(info[\'rvas\'][0]),')
s=s.replace("r['event']=='field_write'", "r['event']=='fixture_write'")
s=s.replace("(r['slot'],r['previous_observed'],r['observed_after'])", "(r['previous_observed'],r['observed_after'])")
s=s.replace('[(0,7,11),(0,11,11),(0,11,0x100000b),(0,0x100000b,0x2000b),(0,0x2000b,33),(1,9,55),(0,33,66)]',
            '[(7,11),(11,11),(11,0x100000b),(0x100000b,0x2000b),(0x2000b,33),(33,66),(66,77)]')
s=s.replace("                assert len([r for r in rows if r['event']=='load_rng_setter'])==1\n",'')
s=s.replace("                assert len([r for r in rows if r['event']=='combat_gate'])==1\n",'')
s=s.replace('pending-watch-fixtures.json','camera-rng-watch-fixtures.json')
(ROOT/'test_camera_rng_watch.py').write_text(s,encoding='utf-8')

commands=['@echo off','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1']
for name in ('observe_camera_rng_watch','camera_rng_watch_payload_fixture'):
    commands.extend([f'cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\\mod_research\\{name}.exe /Fo:work\\mod_research\\{name}.obj work\\mod_research\\{name}.cpp','if errorlevel 1 exit /b 1'])
(ROOT/'build_camera_rng_watch.cmd').write_text('\n'.join(commands)+'\n',encoding='ascii')

