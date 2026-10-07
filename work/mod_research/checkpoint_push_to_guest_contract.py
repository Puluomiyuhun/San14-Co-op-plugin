"""Pure offline A export -> B preparation evidence contract, not a live adapter.

Inputs are locally reviewed evidence, not trusted claims from a network peer.
No imports of live readers, process APIs, metadata core or auto_reload launcher.
No file writes, native calls, pending-slot writes, or load authorization.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "san14.push-to-guest-preparation.v1"
GAME_SHA = "42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025"
FILENAME = "mppush01.s14"
FORENSIC_SHA = "b9500d662fb4a394ce03279e8491616719d12a799b2881a67e9d2a5553c3914a"
WORLD_PROFILE = "san14.partial-783-records-48400-hex-rng-world.v1"
STACK = ["CRootState", "CMotorGameState", "CGameState", "CStrategyState", "CUserStrategyState"]
WORLD_DOMAINS = {"normalized_records_783", "hex_48400_fields_242000", "global_rng", "world_fields"}


class ContractError(ValueError):
    """Fail closed; reason is suitable for a preparation report."""


def need(condition, reason):
    if not condition:
        raise ContractError(reason)


def digest(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def token(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value) is not None


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def attachment(value):
    need(isinstance(value, dict), "attachment_missing")
    need(set(value) == {"pid", "process_start_100ns", "base", "nonce", "game_sha256"}, "attachment_shape")
    need(integer(value["pid"], 1) and integer(value["process_start_100ns"], 1), "attachment_process_identity")
    need(integer(value["base"], 0x10000) and token(value["nonce"]), "attachment_address_or_nonce")
    need(value["game_sha256"] == GAME_SHA, "unsupported_game_build")


def world(value):
    need(isinstance(value, dict), "partial_world_missing")
    need(set(value) == {"profile", "domains", "two_reads_equal", "full_world_verified"}, "partial_world_shape")
    need(value["profile"] == WORLD_PROFILE, "unsupported_partial_world_profile")
    need(value["two_reads_equal"] is True and value["full_world_verified"] is False, "partial_world_scope_or_stability")
    need(isinstance(value["domains"], dict) and set(value["domains"]) == WORLD_DOMAINS, "partial_world_domains_missing")
    need(all(digest(v) for v in value["domains"].values()), "partial_world_invalid_digest")


def planning(value, identity):
    need(isinstance(value, dict), "planning_missing")
    need(value.get("stack") == STACK and value.get("phase") == 2, "not_final_idle_User")
    need(value.get("force_id") == identity[0] and value.get("ruler_id") == identity[1], "planning_identity_mismatch")
    need(value.get("date") == [203, 8, 11], "unsupported_planning_date")
    need(integer(value.get("user_pointer"), 0x10000), "planning_User_pointer_missing")
    for key in ("pending_state_commands", "advance_game", "panel_advance", "control_pause"):
        need(type(value.get(key)) is int and value[key] == 0, "planning_busy_" + key)
    need(type(value.get("pending_menu")) is int and value["pending_menu"] == -1, "planning_menu_pending")
    need(type(value.get("pending_load")) is int and value["pending_load"] == -1, "planning_load_pending")
    need(value.get("new_commands_frozen") is True, "new_commands_not_frozen")


def prepare_guest_checkpoint(*, source, current_source, current_guest, target_binding, expected, staged_bytes):
    """Validate evidence and return a non-executable research preparation manifest.

    expected is a caller-pinned local review plan. Its hashes/IDs must originate
    independently of a received packet. Matching JSON is not authentication.
    target_binding describes an already-reviewed explicit metadata binding;
    this function cannot create one. Missing/invalidation means rejection.
    staged_bytes is a local staging read, not a native Steam storage read.
    """
    try:
        return _prepare(source, current_source, current_guest, target_binding, expected, staged_bytes)
    except (KeyError, TypeError, AttributeError, OverflowError) as error:
        raise ContractError("malformed_or_missing_evidence") from error


def _prepare(source, current_source, current_guest, target, expected, staged_bytes):
    need(expected["schema"] == SCHEMA, "wrong_contract_schema")
    for key in ("attempt_id", "intent_id", "room_id", "checkpoint_id"):
        need(token(expected[key]), "invalid_expected_" + key)
        need(source[key] == expected[key], "source_binding_mismatch_" + key)
    for key in ("epoch", "turn", "last_command_seq"):
        need(integer(expected[key]) and type(source[key]) is int and source[key] == expected[key], "authority_boundary_mismatch_" + key)
    need(expected["filename"] == FILENAME and source["filename"] == FILENAME, "forensic_or_unsupported_filename")
    need(type(source["export_slot"]) is int and source["export_slot"] == -1, "export_must_use_private_sentinel")
    need(expected["guest_identity"] == {"force_id": 2, "ruler_id": 952}, "unsupported_guest_identity")
    need(expected["evidence_origin"] in ("synthetic_fixture", "reviewed_native_capture"), "evidence_origin_missing")
    need(source["evidence_origin"] == expected["evidence_origin"], "evidence_origin_mismatch")
    need(digest(expected["source_trace_sha256"]) and source["trace_sha256"] == expected["source_trace_sha256"], "source_trace_not_pinned")
    need(digest(expected["source_receipt_sha256"]) and canonical_sha(source) == expected["source_receipt_sha256"], "source_receipt_not_pinned")
    for side, current in (("source", current_source), ("guest", current_guest)):
        attachment(expected[side + "_attachment"])
        need(current["attachment"] == expected[side + "_attachment"], "stale_" + side + "_attachment")
        for key in ("room_id", "epoch", "turn", "last_command_seq"):
            need(current[key] == expected[key] and type(current[key]) is type(expected[key]), "stale_" + side + "_" + key)
    need(source["attachment"] == expected["source_attachment"], "old_source_receipt_attachment")

    need(source["outcome"] == "NATIVE_PUSH_EXPORT_OBSERVED_RETURNED_USER", "uncertain_or_header_only_save")
    need(source["forensic"] is False and source["uncertainties"] == [], "forensic_or_uncertain_save")
    need(source["queue_type"] == 0 and type(source["queue_type"]) is int, "replacement_entry_retired")
    intent = source["intent"]
    need(intent["id"] == expected["intent_id"] and intent["create_new"] is True and intent["flushed"] is True,
         "save_intent_not_durable")
    seq = source["sequence"]
    sequence_names = ("intent_durable", "binder", "queue", "worker_started", "worker_joined", "finalizer_returned", "returned_User", "file_stable")
    values = [seq[k] for k in sequence_names]
    need(all(integer(v, 1) for v in values) and all(a < b for a, b in zip(values, values[1:])), "save_effect_order_unproved")
    life = source["lifecycle"]
    for key in ("request_associated", "worker_success", "finalizer_returned", "request_globals_cleared",
                "observer_cleanly_detached", "hooks_restored", "existing_saves_unchanged"):
        need(life[key] is True, "save_lifecycle_missing_" + key)
    need(all(type(life[key]) is int and life[key] == 1 for key in ("binder_calls", "queue_calls", "worker_calls")), "save_not_single_request")
    need(life["stack_depths"] == [5, 6, 5] and life["save_state_pointer"] == life["worker_save_state_pointer"]
         and integer(life["save_state_pointer"], 0x10000), "save_state_association_or_push_stack")
    for snapshot in (source["before"], source["after"], current_source):
        planning(snapshot["planning"], (12, 666))
        world(snapshot["world"])
    need(source["before"]["planning"]["user_pointer"] == source["after"]["planning"]["user_pointer"]
         == current_source["planning"]["user_pointer"], "source_User_replaced")
    need(source["before"]["world"] == source["after"]["world"] == current_source["world"], "source_world_changed_in_covered_domains")
    planning(current_guest["planning"], (2, 952))

    file = source["file"]
    need(digest(file["sha256"]) and file["sha256"] != FORENSIC_SHA, "forensic_or_invalid_file_hash")
    need(integer(file["size"], 294) and file["size"] <= 0x7d000, "checkpoint_size")
    need(file["created_new"] is True and file["local_absent_before"] is True and file["native_absent_before"] is True, "new_file_absence_not_proven")
    samples = file["stable_samples"]
    need(isinstance(samples, list) and len(samples) >= 3, "stable_file_samples_missing")
    need(all(s["sha256"] == file["sha256"] and s["size"] == file["size"] and integer(s["tick_ms"]) for s in samples), "file_samples_mismatch")
    times = [s["tick_ms"] for s in samples]
    need(all(a < b for a, b in zip(times, times[1:])) and times[-1] - times[0] >= 1000, "file_stability_interval")
    need(type(staged_bytes) is bytes and len(staged_bytes) == file["size"] and hashlib.sha256(staged_bytes).hexdigest() == file["sha256"], "local_staged_bytes_mismatch")

    need(digest(expected["target_binding_sha256"]) and canonical_sha(target) == expected["target_binding_sha256"], "target_binding_not_pinned")
    need(target["status"] == "EXPLICIT_TARGET_PREBOUND_NO_LOAD", "target_not_prebound")
    need(target["attachment"] == expected["guest_attachment"], "target_old_attachment")
    need(target["checkpoint_id"] == expected["checkpoint_id"] and target["source_receipt_sha256"] == expected["source_receipt_sha256"], "target_wrong_checkpoint")
    need(target["filename"] == FILENAME and target["sha256"] == file["sha256"] and target["size"] == file["size"], "target_file_mismatch")
    need(integer(target["slot"], 63) and target["slot"] <= 109, "target_positive_reserved_slot_required")
    need(target["identity"] == expected["guest_identity"], "target_identity_not_prebound")
    need(target["fallback_slot"] is None and target["pending_load"] == -1, "fallback_or_load_already_pending")
    for key in ("local_formatted_slot_absent", "native_formatted_slot_absent", "table_owned_by_list", "filename_readback_matched", "parsed_header_matched"):
        need(target[key] is True, "target_binding_missing_" + key)
    need(integer(target["node"], 0x10000) and target["payload"] == target["node"] + 0x10, "target_node_identity")
    cache = current_guest["cache"]
    need(cache["mode"] == 0 and cache["pending"] == -1, "guest_cache_busy")
    need(token(target["cache_generation"]) and cache["generation"] == target["cache_generation"], "target_cache_invalidated")
    need(cache["slot"] == target["slot"] and cache["payload"] == target["payload"] and cache["filename"] == FILENAME,
         "target_not_currently_bound")
    need(target["native_full_file_identity"] == "UNVERIFIED", "native_file_identity_claim_not_verified_by_this_contract")
    need(target["metadata_adapter_profile"] == "future-mppush01-reviewed-profile", "legacy_metadata_core_not_compatible")

    return {
        "schema": SCHEMA, "result": "RESEARCH_PREPARATION_READY",
        "evidence_origin": expected["evidence_origin"], "checkpoint_id": expected["checkpoint_id"],
        "source_receipt_sha256": expected["source_receipt_sha256"], "source_trace_sha256": expected["source_trace_sha256"],
        "target_binding_sha256": expected["target_binding_sha256"],
        "authority_boundary": {k: expected[k] for k in ("room_id", "epoch", "turn", "last_command_seq")},
        "source_attachment": dict(expected["source_attachment"]), "guest_attachment": dict(expected["guest_attachment"]),
        "guest_target": {k: target[k] for k in ("slot", "filename", "sha256", "size", "identity", "cache_generation", "node", "payload")},
        "local_staged_sha256_verified": True, "native_full_file_identity_verified": False,
        "full_world_verified": False, "formal_room_checkpoint_usable": False,
        "load_authorized": False, "game_access": False, "adapter_enabled": False,
        "required_before_load": [
            "Bind the complete file bytes actually served by native storage; matching header/local SHA is insufficient.",
            "Implement and separately review mppush01 metadata and guest identity adapters; old fixed-name cores are incompatible.",
            "Revalidate this exact current attachment, cache generation, node, slot, filename and identity at the load safe point; never fall back to34.",
            "Use a new durable once intent before any load effect; uncertain attempts must not be retried automatically.",
            "Observe native worker completion, B identity initialization and returned planning state before classifying load outcome.",
            "Compare covered business fields at matched stages; full-world coverage and formal room barriers remain incomplete.",
        ],
    }
