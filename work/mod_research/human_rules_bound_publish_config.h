#pragma once
// Production build is tied to this audited pure-forward stage, not caller input.
#ifdef HUMAN_RULES_BOUND_FIXTURE
#include "human_rules_bound_fixture_hashes.h"
#else
constexpr unsigned ExpectedFixture=0;
constexpr const char* ApprovedExeSha="42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025";
constexpr const char* ApprovedStageSha="ca4c3b7bc7483c752e06e5fc6e5c6b72edb20f2ecd70c8d7341cb70fc70d88b3";
constexpr const char* ApprovedImageSha=ApprovedExeSha;
#endif
