"""One-shot fixture composition; does not edit any frozen component."""
from pathlib import Path
P=Path(__file__).resolve().parent
def replace(s,a,b):
 assert s.count(a)==1,(a[:90],s.count(a))
 return s.replace(a,b)
def main():
 destination=P/'checkpoint_persistent_runtime_fixture.cpp';test=P/'checkpoint_persistent_runtime_test.py'
 assert not destination.exists() and not test.exists()
 s=(P/'checkpoint_dynamic_native_queue_fixture.cpp').read_text()
 s=replace(s,'#include "checkpoint_persistent_route_six_adapter.h"','#include "checkpoint_persistent_route_six_adapter.h"\n#include "checkpoint_persistent_physical_owner.h"')
 s=replace(s,'static rt::Router router;static rt::SixAdapter routeAdapter;', '''namespace po=checkpoint_persistent_physical_owner;
static po::Owner physicalOwner;
// Game build/attachment validator remains an explicit fixture double. Real
// physical owner, page protection, bridge installation and queue Adapter run.
static bool physicalGuard(void*,po::Point,unsigned) noexcept {return true;}
static po::Report physicalReport(){po::Report r{};physicalOwner.Snapshot(r);return r;}''')
 s=replace(s,'    check(session.Initialize(c),"fresh Session owns fresh core objects");\n','')
 start=s.index('    if(!generationIndex){\n        rt::Config route{};route.initial=logical->RouteGeneration();')
 end=s.index('    check(session.ActivateForOfflineExercise()',start)
 s=s[:start]+'''    if(!generationIndex){
        DWORD protection=0;check(VirtualProtect(GuestSessionSlots,4096,PAGE_READONLY,&protection)!=0,"native slots read-only before owner publication");
        po::Config p{};memcpy(p.hooks,c.hooks,sizeof p.hooks);p.userForward=reinterpret_cast<void*>(&CheckpointPersistentAuthorizedOriginal);
        p.initial=logical->RouteGeneration();p.validate=physicalGuard;p.context=&physicalOwner;
        check(physicalOwner.Install(p),"real owner installs all six resident bridges once");
    }else{
        check(physicalOwner.PublishForOfflineExercise(generationIndex,logical->RouteGeneration()),"owner-controlled fixture generation transition");
    }
    check(physicalOwner.Verify(),"all six original bindings/protections still owned");
    check(session.Initialize(c),"fresh Session initialized after physical ownership established");
'''+s[end:]
 s=s.replace('!routeAdapter.Faults()','!physicalReport().routeFaults').replace('router.Snapshot(routing);','routing=physicalReport().route;').replace('router.Snapshot(report);','report=physicalReport().route;')
 assert 'router.' not in s and 'routeAdapter.' not in s
 s=replace(s,'    check(report.transitions==1&&report.generations==2&&report.entered==report.released&&!report.active,"two generations on one six-entry installation");','''    check(report.transitions==1&&report.generations==2&&report.entered==report.released&&!report.active,"two generations on one six-entry installation");
    const auto installed=physicalReport();check(installed.installed&&installed.configured==6&&installed.published==6&&installed.hooksRetained&&installed.error==po::Error::None,"physical owner remains singular and healthy after two loads");''')
 destination.write_text(s)
 t=(P/'checkpoint_dynamic_native_queue_test.py').read_text().replace('checkpoint_dynamic_native_queue_fixture\'','checkpoint_persistent_runtime_fixture\'').replace("P/'checkpoint_dynamic_native_queue_runs'","P/'checkpoint_persistent_runtime_runs'").replace("'checkpoint_dynamic_native_queue_test.py'","'checkpoint_persistent_runtime_test.py'")
 t=replace(t,"UNITS=['checkpoint_native_queue_adapter_core'","UNITS=['checkpoint_persistent_physical_owner','checkpoint_load_hook_set','checkpoint_native_queue_adapter_core'")
 t=replace(t,"DEFS='/DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE","DEFS='/DCHECKPOINT_PERSISTENT_PHYSICAL_OWNER_FIXTURE /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE")
 start=t.index('CASES=');end=t.index('\n',start)
 cases=['success','actual-byte-mismatch','load-exception','read-exception','title-exception','user-exception','stop-after-cas','post-cas-reject','alternate-factions','planning-wrong-date','planning-wrong-district','planning-wrong-hash','planning-source-generation','planning-source-drift','planning-missing-join','planning-native-exception','planning-old-report','planning-reuse-load','input-pending','input-missing-prefetch','queue-wrong-generation','queue-stale-ticket','queue-wrong-controller','queue-copied-frame','queue-stop-authorized','queue-stop-native','queue-native-exception']
 t=t[:start]+'CASES='+repr(cases)+t[end:]
 t=t.replace("'san14.dynamic-native-queue", "'san14.persistent-runtime")
 # The upstream honest scope remains; append this additional verified layer.
 t=t.replace("if not result['sources_unchanged']:","result['persistent_physical_owner_integrated']=True\n result['scope'] += ' Real physical owner configures and publishes six protected slots once, verifies original forwarding/protection, and retains them across both fixture generations. Real game runtime guards and production scheduler handoff remain unintegrated.'\n if not result['sources_unchanged']:")
 test.write_text(t)
 print(destination);print(test)
if __name__=='__main__':main()
