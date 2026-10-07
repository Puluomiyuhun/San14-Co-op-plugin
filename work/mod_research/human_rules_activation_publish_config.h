#pragma once
#ifdef HUMAN_RULES_ACTIVATION_PUBLISH_FIXTURE
#include "human_rules_activation_publish_fixture_hashes.h"
#include "human_rules_activation_publish_fixture_counters.h"
#else
constexpr unsigned ExpectedFixture=0;
constexpr const char* ApprovedExeSha="42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025";
constexpr const char* ApprovedStageSha="fffd793bfd65c7082c838f11aec15506d193fc489f45ee50bd53f22455b3222d";
constexpr const char* ApprovedImageSha=ApprovedExeSha;
#include "human_rules_activation_publish_production_counters.h"
#endif
