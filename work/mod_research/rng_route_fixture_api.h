#pragma once
#include <cstdint>
// Fixture API only. No process attachment, game patching, or hook installation.
using TextFunction = void* (*)(void*);
using RandomFunction = int (*)(int);
struct RouteConfig {
    unsigned size, mode; // 0: observe/pass through, 1: isolate candidates
    uint32_t presentation_seed;
    TextFunction text;
    RandomFunction range, percentage;
};
struct RouteSnapshot {
    unsigned size, mode, local_depth;
    uint32_t presentation_seed;
    long active;
    long long text_calls, expression_native, expression_private;
    long long voice_native, voice_private, private_advances;
};
using ConfigureFunction = int (*)(const RouteConfig*);
using SnapshotFunction = int (*)(RouteSnapshot*);
