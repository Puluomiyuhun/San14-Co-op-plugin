"""Generate only this new fixture from the frozen same-bridge Session fixture."""
from pathlib import Path
import hashlib
P=Path(__file__).resolve().parent
source=P/'checkpoint_planning_return_observer_session_fixture.cpp'
text=source.read_text(encoding='utf-8')
sha=hashlib.sha256(source.read_bytes()).hexdigest()
def change(old,new,count=1):
    global text
    if text.count(old)!=count:raise RuntimeError('Frozen extraction anchor changed')
    text=text.replace(old,new)
change('static pr::Observer planning;', 'static std::uint64_t runtimeAttempt=0,runtimeEpoch=0;\nstatic unsigned char runtimeBinding[32]{};\nstatic pr::Observer planning;')
change('epoch==17','epoch==runtimeEpoch')
start=text.index('    printf("{\\"case\\":')
end=text.index('    return failures?1:0;',start)
text=text[:start]+'    (void)passedPhase;\n'+text[end:]
change('int wmain(int argc,wchar_t**argv){','static int runBoundSession(int argc,wchar_t**argv){')
change('fclose(file);setup();','fclose(file);setup();layout.config.attempt=runtimeAttempt;')
change('memset(c.request.ownerBinding,0x63,32);','memcpy(c.request.ownerBinding,runtimeBinding,32);')
change('memset(c.identity.ownerBinding,0x63,32);','memcpy(c.identity.ownerBinding,runtimeBinding,32);')
change('planningConfig.epoch=17;','planningConfig.epoch=runtimeEpoch;')
prefix='// Independent fixture extracted from '+source.name+'\n// Frozen source SHA256: '+sha+'\n'
(P/'checkpoint_guest_runtime_fixture.cpp').write_text(prefix+text+'\n#include "checkpoint_guest_runtime_fixture_control.inc"\n',encoding='utf-8')
build=(P/'checkpoint_planning_return_observer_session_build.cmd').read_text(encoding='utf-8')
build=build.replace('checkpoint_planning_return_observer_session','checkpoint_guest_runtime_fixture')
build=build.replace('checkpoint_guest_runtime_fixture_fixture.','checkpoint_guest_runtime_fixture.')
(P/'checkpoint_guest_runtime_fixture_build.cmd').write_text(build,encoding='utf-8')
print('Generated isolated runtime fixture; no original source changed')
