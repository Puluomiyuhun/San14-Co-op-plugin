#pragma once
#include "checkpoint_guest_native_session.h"
namespace checkpoint_session_generation {
namespace ns=checkpoint_guest_native_session;
constexpr unsigned BankAbi=1, Capacity=2;
struct Identity {std::uint64_t generation=0,attempt=0;unsigned char attachment[32]{};};
struct Description {
    Identity identity{};ns::Session* session=nullptr;
    checkpoint_load_hook_set::Binding hooks[6]{};
};
// Internal same-process ABI. A trusted controller supplies a fully prepared
// Config. This is NOT a wire protocol, discovery interface, or game installer.
struct BankApi {
    unsigned size,version,configBytes,reportBytes;
    bool (*initialize)(const Identity*,const ns::Config*) noexcept;
    bool (*describe)(Description*) noexcept;
    bool (*arm)() noexcept;
    void (*stop)() noexcept;
    bool (*restoreBeforeCommit)() noexcept;
    void (*snapshot)(ns::Report*) noexcept;
    bool (*bindQueuedMenu)(const ns::QueueReceipt*) noexcept;
};
using GetBankApi=const BankApi*(*)() noexcept;
}
