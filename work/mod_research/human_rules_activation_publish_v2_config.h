#pragma once
#ifdef HUMAN_RULES_ACTIVATION_PUBLISH_FIXTURE
#include "human_rules_activation_publish_v2_fixture_hashes.h"
#include "human_rules_activation_publish_v2_fixture_counters.h"
#else
constexpr unsigned ExpectedFixture=0;
constexpr const char* ApprovedExeSha="42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025";
constexpr const char* ApprovedStageSha="29d0f6e83531f3892d075b84b632a614bdf485a61293574ba68d590dc2d0e1ac";
constexpr const char* ApprovedImageSha=ApprovedExeSha;
#include "human_rules_activation_publish_v2_production_counters.h"
#endif
