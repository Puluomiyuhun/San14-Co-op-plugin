// Defect reproduction: original IsTop's covered-return is an explicit model.
static unsigned queuedGateError=0,queuedOwnerError=99,queuedOwnerStopped=0,coveredCalls=0;
extern "C" void coveredReturnModel(){}
static void coveredUser(){
 const auto original=ActionUserSnippet;ActionUserSnippet=reinterpret_cast<uintptr_t>(&coveredReturnModel);
 need(scopedDispatch(0,user)==0,"covered User actual Owner AFTER/FINALLY");ActionUserSnippet=original;++coveredCalls;
}
static void queuedGame(){
 need(get<std::uint64_t>(b+0x19E7310+0x10)==5&&get<std::uint64_t>(b+0x19E7310+0x30)==1,"actual Driver queued Save before modeled apply");
 need(scopedGame()==0,"actual Game bridge in queued-before-apply window");
 ag::Report g{};input->Snapshot(g);ss::Report u{};session->Snapshot(u);
 queuedGateError=unsigned(g.error);queuedOwnerError=unsigned(u.error);queuedOwnerStopped=u.stopped;
 need(queuedGateError==unsigned(ag::Error::Input)&&queuedOwnerError==0&&queuedOwnerStopped,"queue window reproduces Gate Input then Owner Stop without Owner error");
}
