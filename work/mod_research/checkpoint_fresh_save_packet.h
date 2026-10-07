#pragma once
#include "checkpoint_fresh_save.h"

// Local byte export only. This format neither authenticates a process nor
// authorizes publishing/loading a world. Call with Owner::CopyArtifact output.
namespace checkpoint_fresh_save_packet {
constexpr unsigned HeaderBytes=284;
constexpr std::uint64_t MaxBytes=64ULL*1024*1024;
enum class Error:unsigned {None,Request,Report,Bytes,Allocation};
// Explicit little endian fields: no native struct padding, pointers to data,
// paths, or game/Steam calls. On failure out is cleared (no stale export).
Error Encode(const checkpoint_fresh_save::Artifact&,
             std::vector<unsigned char>&out) noexcept;
}
