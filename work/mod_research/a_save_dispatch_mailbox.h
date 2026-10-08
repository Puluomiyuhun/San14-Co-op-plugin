#pragma once
#include "checkpoint_fresh_save.h"

// Copied transport only. Take is NOT evidence of a native Root boundary,
// permission to save, input exclusion, or serializer completion.
namespace a_save_dispatch_mailbox {
namespace fs=checkpoint_fresh_save;
enum class State:unsigned {Empty,Queued,Claimed,Accepted,Complete,Delivered,Cancelled,Unknown};
struct Envelope {std::uint64_t ticket=0;fs::Request request{};unsigned char binding[32]{};};
struct Record {Envelope message{};State state=State::Empty;DWORD publisher=0;};
struct Report {bool initialized=false,stopped=false;DWORD host=0;unsigned count=0;Record records[2]{};};
class Mailbox final {
public:
 Mailbox()=default;Mailbox(const Mailbox&)=delete;Mailbox&operator=(const Mailbox&)=delete;
 // Must be called on the already-established host control thread.
 bool Initialize()noexcept;
 bool Enqueue(const fs::Request&,const unsigned char binding[32])noexcept;
 bool Take(Envelope&)noexcept;
 // Host calls only AFTER its real Submit returned true. Not Save completion.
 bool Accept(const Envelope&)noexcept;
 bool WaitAccepted(std::uint64_t generation,DWORD timeoutMs)noexcept;
 // Publish once after the host's real completion chain. This class only checks
 // transport identity and copies bytes; it does not verify their SHA/world.
 bool Complete(const Envelope&,const fs::Artifact&)noexcept;
 bool Unknown(const Envelope&)noexcept;
 bool Copy(std::uint64_t,fs::Artifact&)noexcept;
 void Stop()noexcept;
 void Snapshot(Report&)noexcept;
private:
 SRWLOCK lock_=SRWLOCK_INIT;CONDITION_VARIABLE changed_=CONDITION_VARIABLE_INIT;
 Report report_{};fs::Artifact artifacts_[2];
 void stopLocked()noexcept;
 int claimed(const Envelope&)const noexcept;
};
// Signature-compatible held_ipc execution ports. Submit waits for host Accept,
// not just Enqueue. Config/lifetime are trusted local immutable host data.
// Existing Server does not propagate Stop: a host shutdown coordinator MUST
// call adapter.Stop() on disconnect/shutdown BEFORE joining the pipe/host.
struct Adapter {
 Mailbox*mailbox=nullptr;DWORD timeoutMs=1000;
 static bool SubmitPort(void*,const fs::Request&,const unsigned char[32])noexcept;
 static bool CopyPort(void*,std::uint64_t,fs::Artifact&)noexcept;
 void Stop()noexcept {if(mailbox)mailbox->Stop();}
};
}
