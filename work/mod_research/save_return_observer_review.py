"""Offline review/scope only. No process access, debugger, compilation or install."""
from pathlib import Path
from datetime import datetime
import json,hashlib
P=Path(__file__).resolve().parent
source=P/'save_return_user_shadow.py'
evidence=P/'save_return_user_shadow_20261006-192041-401446.json'
r=json.loads(evidence.read_text(encoding='utf8'))
assert r['result']=='PASS' and len(r['cases'])==4
checks=[]
for i,c in enumerate(r['cases']):
 b,m,a=c['before'],c['paused'],c['after']
 assert c['result']=='PASS' and b['stack']==a['stack']
 assert m['stack'][-1]=='Save'
 assert b['user_phase']==m['user_phase']==a['user_phase']==2
 assert [b['control_pause'],m['control_pause'],a['control_pause']]==[0,1,0]
 assert [b['cursor_enabled'],m['cursor_enabled'],a['cursor_enabled']]==[1,0,1]
 assert a['advance_game']==a['advance_panel']==0
 assert a['pending_menu']==-1
 checks.append({'case':i,'result':'PASS','selected':c['selected'],'valid':c['selection_valid'],
                'visible':c['panel_visible'],'selected_after':a['selected'],
                'callback_carriers_changed':b['callback_2b0']!=a['callback_2b0'] and b['callback_330']!=a['callback_330']})
report={
 'schema':'san14.save-return-observer-scope.v1','result':'REVIEW_COMPLETE_SCOPE_ONLY',
 'game_access':False,'compiled':False,'installed':False,'live_execution_allowed':False,
 'reviewed_source':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'reviewed_evidence':evidence.name,'evidence_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),
 'checked_cases':checks,
 'review_conclusion':'No contradiction found in the explicitly bounded claims. Four native User callbacks, selected clear path and callback container helpers really run inside copied queue/apply. This does not prove the skipped UI/service behavior, world invariance or export safety.',
 'material_limits':[
  'All four cases begin with both coordinator callback containers empty; replacing and destroying pre-existing callbacks is not covered.',
  'Selection probes use onlyUser+4A8. Independent+4B0/+4B8, multiple simultaneous selected objects and their real virtual validity callbacks are not exercised.',
  'Lookup509460 always returns synthetic Game, several nested UI chains are null, and peripheral virtual/service callbacks return fixed values. Native branch bodies are not complete live side-effect coverage.',
  'Special context5086A0 is deliberately null,145A90 mode is3,2F5F70 is0 and1C1A70 is0. This supports a bounded ordinary-mode case, not all menu states.',
  'Only idleUser phase2 is tested. The normal event path that can map phase1 to2 and other phases are deliberately out of scope.',
  'Game+47C/panel+1B0 start at synthetic zero. Date, world+20A8, global/world RNG and full business arrays are not part of this snapshot assertion.',
  'Coordinator low flag starts1 and C020 clears it; snapshot does not include this field and the later8F50 is stubbed. It cannot establish all pause/coordinator state is restored.',
  'The old queue harness constructs the Save object with a stub and supplies synthetic worker success; save serialization and worker effects remain absent.',
  'Valid selection clearing and callback reconstruction are expected real UI effects. A strict all-byte User/UI equality criterion would falsely reject the normal path.',
  'This evidence does not test new wrapper ABI, return register preservation or asynchronous detach lifecycle. These need separate observer-specific fixtures.'
 ],
 'minimum_first_run':{
  'user_action':'Only open and close the normal Config menu. Optionally open SaveLoad and cancel without choosing/confirming a save. Do not ask for selection changes or a save export.',
  'normal_sequences':['User->Config->User','User->Config->SaveLoad->Config->User'],
  'expected_user_events':['exit(kind0)','pause','resume','enter(kind1)'],
  'not_required':'No new Save native call, binder, queue creation, worker call, date advancement, menu automation or ordinary-slot write.',
  'scope':'Match actual User identity, entry/return args, true boundaries and restored planning; this is a lifecycle observation, not a checkpoint test.'},
 'observation_choices':[
  {'method':'ExternalReadProcessMemory only','meaning':'Pure data read with no code/vtable/debug-register edits','covers':'Idle/profile and coarse stack/phase timeline','gap':'Cannot reliably capture short callback boundaries or original returnRAX; do not label sampling as precise main-loop recording'},
  {'method':'Four adaptive hardware execution breakpoints','meaning':'No code/vtable/data patch or injected wrapper; debugger modifies thread debug context and pauses hits','covers':'Each User callback entry and its actual return registers by temporarily replacing that thread slot with return address','required_guards':['No competing debugger/breakpoints','Save per-thread original debug context','Thread+entryRSP+expected returnRSP identity for return pairing','Reject unmatched/nested/reentrant pairing and dropped events','Restore breakpoints on all existing/new threads; bounded timeout and detach','Preserve all general/vector registers and ABI; change only debug bits required to resume'],
   'gaps':['Timing altered by debugger','Same-function reentry can escape an entry point while its slot tracks return; mark this run inconclusive if the profile cannot rule it out','All4 DR slots occupied: exact independent loop entry/exit needs another round or a separately reviewed observation point']},
  {'method':'Vtable observer DLL','meaning':'Temporarily writes4 User vtable slots; cannot be called pure read-only','covers':'Entry/exit on4 callbacks without instruction patching','required_guards':['Exact current binary/RTTI/vtable values','原函数恰好调用一次','Known pause/resume integer return and eventvoid ABI; assembly wrapper preserves rawRAX even for void','Preserve inputRCX/RDX/R8/R9, requiredXMM/stack arguments, Win64alignment/shadowspace/nonvolatiles and unwind behavior','Do not swallow game exceptions','Only private preallocated ring writes; no blockingI/O in callback','Recordoverflow as incomplete','Cancel/drain callbacks before restoring/unloading; original slot/protection CAS verification'],
   'gaps':['Needs compiled isolated ABI/return/cleanup fixtures before any install','UserUpdate hook alone cannot observe main loop while modal menus are top; do not claim full loop coverage']}
 ],
 'record_contract':{
  'identity':['run nonce','thread id','monotonic sequence andclock','callback kind','entry orreturn','entrycaller/returnaddress','entryRSP/expectedreturnRSP','originalRAX onreturn','inputRCX/RDX/R8/R9','originalUser pointer/vtable'],
  'state':['manager stackcount andbounded pointer/name/vtable snapshot','pending count/capacity andboundedkind/state records','User+470 phase,+474 loadsubphase','User rawselection+4A8/+4B0/+4B8 andpointer identity','User+500/+510..610 selectedtransform state, selectively notallraw bytes','User+478 UI toolbar andUser+480 gameplay panel keptdistinct','toolbar+88pendingmenu','Game+47C andGame+480 panel+1B0advance flags','menuConfig+488 and+8 resultwhenpresent','cache manager+8/+3EC/+3F0','control+28pause','cursor+13Cenable','coordinator flag and+2B0/+330 containers normalized asfunctiontype/owner plusrawbytes','world date/+20A8/identity/RNG via verifiedreadonlyprofile','request slot/name/caption emptiness; heapcapacity retainedislegal'],
  'reading_rules':['Use already resolved pointers from root readonlyprofile or globals validated by exact build/RTTI; do not call native singleton getters just to log','Bound lengths/counts; safe reads/missingfield bits; no dereference of untrusted freedselection','Store raw values plus interpretation; do not hash-only','Full businessarrays/hex/RNGbeforeafter capturedexternally atstableidle, notinsideeach callback','Callback pointer changes judged semantically, notrawaddressequality']},
 'completion_contract':[
  'Return to sameUser object, sameRoot/Motor/Game/Strategy/User stack, phase2, date/force unchanged andpendingqueueempty atstableidle.',
  'Match all4 expected User entry/returnpairs; preserve原函数return andrecord ordering. No gaps/overflow/guard mismatch.',
  'Menu cancellation never entersCSaveState/CLoadState/AI/report. Ifunexpected state/date appears, stop observation and preserveevidence; never cancelnativegameactions or repairmemory.',
  'Read-onlybeforeafter compares businessrecords/hex/RNG separately; selectionclear/UIcallbackrebuild are allowed only when actually matched to normal native behavior.',
  'Observe cleanup restoresdebug/vtable/protection fully; report observerinterference separately fromgameoutcome.',
  'Even successfulmenu observation doesnotauthorize automaticcheckpoint export.'
 ],
 'next_step':'Root chooses pure readonlysampling first. If exactcallback evidence is needed, select and separatelyvalidate one bounded observer implementation; no live installer has been produced here.'
}
stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f');path=P/f'save_return_observer_scope_{stamp}.json'
with path.open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'result':report['result'],'review_cases':len(checks),'evidence':str(path),'game_access':False,'compiled':False,'installed':False}))
