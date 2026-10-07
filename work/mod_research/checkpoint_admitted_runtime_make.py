"""Derive only the new owned runtime; never modify frozen fixture or core."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
frozen=json.loads((P/'checkpoint_session_input_admission_handoff.json').read_text())
source=P/'checkpoint_session_input_admission_fixture.cpp'
sha=hashlib.sha256(source.read_bytes()).hexdigest()
if sha!=frozen['source_sha256'][source.name]:raise RuntimeError('Frozen admitted fixture source changed')
text=source.read_text()
def change(old,new,count=1):
    global text
    if text.count(old)!=count:raise RuntimeError('Frozen extraction anchor changed: '+old)
    text=text.replace(old,new)
change('static pr::Observer planning;', 'static std::uint64_t runtimeAttempt=0,runtimeEpoch=0;\nstatic unsigned char runtimeBinding[32]{},runtimeAttemptId[16]{};\nstatic pr::Observer planning;')
change('epoch==17','epoch==runtimeEpoch')
change('printf("FAIL: %s\\n",s);','fprintf(stderr,"FAIL: %s\\n",s);')
start=text.index('static int finishReport(')
end=text.index('\nint wmain(',start)
text=text[:start]+'''static int finishReport(ns::Report&r,bool passedPhase){
    pr::Report p{};pr::Snapshot(planning,p);ad::Report ar{};
    check(admission.Snapshot(ar),"admission final snapshot");
    check(!ar.full_input_hold&&!ar.game_hook_installed,"partial admission has no global authority");
    check(!r.inputExclusionProven&&!r.presentationProven&&!r.nativePlanningReady&&!r.fullWorldVerified,"Session unsupported authority stays false");
    check(!p.fullWorldVerified&&!p.inputExclusionProven&&!p.pixelPresentationProven&&!p.oldStateDestructorsDirectlyObserved&&!p.allWorkersFinishedProven,"planning observation is not authority");
    (void)passedPhase;return failures?1:0;
}
''' +text[end:]
change('int wmain(int argc,wchar_t**argv){','static int runBoundSession(int argc,wchar_t**argv){')
change('fclose(file);setup();','fclose(file);setup();layout.config.attempt=runtimeAttempt;')
change('memset(c.request.ownerBinding,0x63,32);','memcpy(c.request.ownerBinding,runtimeBinding,32);')
change('memset(c.identity.ownerBinding,0x63,32);','memcpy(c.identity.ownerBinding,runtimeBinding,32);')
change('planningConfig.epoch=17;','planningConfig.epoch=runtimeEpoch;')
change('ac.pending.binding.attempt.fill(0xA1);ac.pending.binding.attachment.fill(0xB2);ac.pending.binding.owner_generation=17;',
       'memcpy(ac.pending.binding.attempt.data(),runtimeAttemptId,16);memcpy(ac.pending.binding.attachment.data(),runtimeBinding+16,16);ac.pending.binding.owner_generation=runtimeEpoch;')
change('''        if(scenario==L"player-pending"||scenario==L"entry-ui"||scenario==L"missing-prefetch"){
            const auto oldCalls=userBodies;GuestSessionUserInvoke(layout.config.states[4],1,2,3);session.Snapshot(r);
            check(userBodies==oldCalls+1&&!queueBodies&&!r.casPublished&&r.userControllerCalls==1,"subsequent original frame runs, refused attempt never retries queue");
        }
''','''        // Owned runtime ends this one attempted update here. The frozen source
        // separately tests that later original frames run without queue retry.
''')
text=text.replace('L"player-pending"','L"entry-pending"').replace('L"late-ui"','L"late-pending"')
(P/'checkpoint_admitted_runtime_fixture.cpp').write_text('// Owned runtime derived from '+source.name+'\n// Frozen source SHA256: '+sha+'\n'+text+'\n#include "checkpoint_admitted_runtime_control.inc"\n')
build=(P/'checkpoint_session_input_admission_build.cmd').read_text()
# Rename only output artifacts. The C++/assembly core inputs remain frozen files.
import re
build=re.sub(r'checkpoint_session_input_admission_([A-Za-z0-9_]+)\.(obj|exe)',r'checkpoint_admitted_runtime_\1.\2',build)
build=build.replace('checkpoint_session_input_admission_fixture.cpp','checkpoint_admitted_runtime_fixture.cpp')
(P/'checkpoint_admitted_runtime_build.cmd').write_text(build)
print('Generated new owned admitted runtime and isolated build; frozen sources untouched')
