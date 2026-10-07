"""Isolated synthetic fixtures only. Never opens a game or an existing save."""
from pathlib import Path
from datetime import datetime
import copy
import hashlib
import json
import unittest

import checkpoint_push_to_guest_contract as c


def example():
    source_attachment = dict(pid=101, process_start_100ns=1001, base=0x140000000,
                             nonce="A-attachment-new", game_sha256=c.GAME_SHA)
    guest_attachment = dict(pid=202, process_start_100ns=2002, base=0x240000000,
                            nonce="B-attachment-new", game_sha256=c.GAME_SHA)
    def planning(force, ruler, user):
        return dict(stack=list(c.STACK), phase=2, date=[203,8,11], force_id=force, ruler_id=ruler,
                    user_pointer=user, pending_state_commands=0, advance_game=0, panel_advance=0,
                    control_pause=0, pending_menu=-1, pending_load=-1, new_commands_frozen=True)
    world = {"profile": c.WORLD_PROFILE, "domains": {k:hashlib.sha256(k.encode()).hexdigest() for k in c.WORLD_DOMAINS},
             "two_reads_equal": True, "full_world_verified": False}
    boundary = dict(room_id="fixture-room", epoch=4, turn=17, last_command_seq=63)
    data = b"SYNTHETIC fixture only: not an actual SAN14 file.\0" * 10
    file_sha = hashlib.sha256(data).hexdigest()
    source = dict(boundary, attempt_id="new-push-attempt", intent_id="new-durable-intent", checkpoint_id="checkpoint-17",
                  filename=c.FILENAME, export_slot=-1, evidence_origin="synthetic_fixture", trace_sha256="a"*64,
                  attachment=source_attachment, outcome="NATIVE_PUSH_EXPORT_OBSERVED_RETURNED_USER", forensic=False,
                  uncertainties=[], queue_type=0,
                  intent=dict(id="new-durable-intent", create_new=True, flushed=True),
                  sequence=dict(intent_durable=1,binder=2,queue=3,worker_started=4,worker_joined=5,finalizer_returned=6,returned_User=7,file_stable=8),
                  lifecycle=dict(request_associated=True,worker_success=True,finalizer_returned=True,request_globals_cleared=True,
                                 observer_cleanly_detached=True,hooks_restored=True,existing_saves_unchanged=True,
                                 binder_calls=1,queue_calls=1,worker_calls=1,stack_depths=[5,6,5],save_state_pointer=0x110000,worker_save_state_pointer=0x110000),
                  before=dict(planning=planning(12,666,0x100000),world=copy.deepcopy(world)),
                  after=dict(planning=planning(12,666,0x100000),world=copy.deepcopy(world)),
                  file=dict(sha256=file_sha,size=len(data),created_new=True,local_absent_before=True,native_absent_before=True,
                            stable_samples=[dict(sha256=file_sha,size=len(data),tick_ms=t) for t in (100,700,1300)]))
    current_source = dict(boundary, attachment=source_attachment, planning=planning(12,666,0x100000),world=copy.deepcopy(world))
    current_guest = dict(boundary, attachment=guest_attachment, planning=planning(2,952,0x200000),
                         cache=dict(mode=0,pending=-1,generation="cache-B-7",slot=63,payload=0x220010,filename=c.FILENAME))
    expected = dict(boundary, schema=c.SCHEMA,attempt_id=source["attempt_id"],intent_id=source["intent_id"],
                    checkpoint_id=source["checkpoint_id"],filename=c.FILENAME,evidence_origin="synthetic_fixture",
                    guest_identity=dict(force_id=2,ruler_id=952),source_trace_sha256=source["trace_sha256"],
                    source_receipt_sha256=c.canonical_sha(source),source_attachment=source_attachment,guest_attachment=guest_attachment)
    target = dict(status="EXPLICIT_TARGET_PREBOUND_NO_LOAD",attachment=guest_attachment,checkpoint_id=source["checkpoint_id"],
                  source_receipt_sha256=expected["source_receipt_sha256"],filename=c.FILENAME,sha256=file_sha,size=len(data),slot=63,
                  identity=dict(force_id=2,ruler_id=952),fallback_slot=None,pending_load=-1,
                  local_formatted_slot_absent=True,native_formatted_slot_absent=True,table_owned_by_list=True,
                  filename_readback_matched=True,parsed_header_matched=True,node=0x220000,payload=0x220010,
                  cache_generation="cache-B-7",native_full_file_identity="UNVERIFIED",metadata_adapter_profile="future-mppush01-reviewed-profile")
    expected["target_binding_sha256"]=c.canonical_sha(target)
    # Deepcopy the whole graph separately: malicious evidence changes must not
    # accidentally mutate the independently pinned expectation in a fixture.
    return {k:copy.deepcopy(v) for k,v in dict(source=source,current_source=current_source,current_guest=current_guest,
                                             target_binding=target,expected=expected,staged_bytes=data).items()}


def change(arguments, path, value):
    at=arguments
    for key in path[:-1]:
        at=at[key]
    at[path[-1]]=value


class ContractFixtures(unittest.TestCase):
    def test_complete_synthetic_evidence_stops_before_load(self):
        args=example(); before=copy.deepcopy(args)
        out=c.prepare_guest_checkpoint(**args)
        self.assertEqual(args,before)
        self.assertEqual(out["result"],"RESEARCH_PREPARATION_READY")
        self.assertEqual(out["evidence_origin"],"synthetic_fixture")
        self.assertTrue(out["local_staged_sha256_verified"])
        for key in ("load_authorized","native_full_file_identity_verified","full_world_verified","formal_room_checkpoint_usable","adapter_enabled","game_access"):
            self.assertIs(out[key],False,key)
        self.assertGreaterEqual(len(out["required_before_load"]),6)

    def test_rejections(self):
        cases=[
            ("forensic_name",("source","filename"),"mpckpt01.s14","forensic_or_unsupported_filename"),
            ("renamed_forensic_hash",("source","file","sha256"),c.FORENSIC_SHA,"forensic_or_invalid_file_hash"),
            ("header_only",("source","outcome"),"HEADER_MATCHED","uncertain_or_header_only_save"),
            ("queued_only",("source","outcome"),"QUEUED","uncertain_or_header_only_save"),
            ("unknown_save",("source","uncertainties"),["timeout"],"forensic_or_uncertain_save"),
            ("retired_replace",("source","queue_type"),2,"replacement_entry_retired"),
            ("unflushed_intent",("source","intent","flushed"),False,"save_intent_not_durable"),
            ("effect_before_intent",("source","sequence","intent_durable"),3,"save_effect_order_unproved"),
            ("worker_failed",("source","lifecycle","worker_success"),False,"save_lifecycle_missing_worker_success"),
            ("unmatched_worker",("source","lifecycle","worker_save_state_pointer"),0x120000,"save_state_association_or_push_stack"),
            ("finalizer_unknown",("source","lifecycle","finalizer_returned"),False,"save_lifecycle_missing_finalizer_returned"),
            ("not_User",("source","after","planning","stack"),c.STACK[:-1]+["CReportDisplayState"],"not_final_idle_User"),
            ("User_replaced",("source","after","planning","user_pointer"),0x130000,"source_User_replaced"),
            ("world_changed",("source","after","world","domains","world_fields"),"d"*64,"source_world_changed_in_covered_domains"),
            ("world_changed_after_receipt",("current_source","world","domains","hex_48400_fields_242000"),"e"*64,"source_world_changed_in_covered_domains"),
            ("missing_coverage",("source","after","world","domains"),{},"partial_world_domains_missing"),
            ("overclaim_world",("source","before","world","full_world_verified"),True,"partial_world_scope_or_stability"),
            ("old_A_attachment",("current_source","attachment","nonce"),"old-A","stale_source_attachment"),
            ("reused_B_pid",("current_guest","attachment","process_start_100ns"),2001,"stale_guest_attachment"),
            ("old_source_receipt",("source","attachment","nonce"),"old-A","old_source_receipt_attachment"),
            ("stale_commands",("current_source","last_command_seq"),64,"stale_source_last_command_seq"),
            ("B_input_unfrozen",("current_guest","planning","new_commands_frozen"),False,"new_commands_not_frozen"),
            ("native_absence_unproved",("source","file","native_absent_before"),False,"new_file_absence_not_proven"),
            ("file_not_stable",("source","file","stable_samples"),[],"stable_file_samples_missing"),
            ("no_binding",("target_binding","status"),"PLANNED_ONLY","target_not_prebound"),
            ("old_binding",("target_binding","attachment","nonce"),"old-B","target_old_attachment"),
            ("wrong_checkpoint",("target_binding","checkpoint_id"),"checkpoint-16","target_wrong_checkpoint"),
            ("fallback34",("target_binding","fallback_slot"),34,"fallback_or_load_already_pending"),
            ("negative_B_slot",("target_binding","slot"),-1,"target_positive_reserved_slot_required"),
            ("ordinary_B_slot",("target_binding","slot"),34,"target_positive_reserved_slot_required"),
            ("wrong_B_identity",("target_binding","identity","ruler_id"),666,"target_identity_not_prebound"),
            ("cache_invalidated",("current_guest","cache","generation"),"cache-B-8","target_cache_invalidated"),
            ("cache_replaced",("current_guest","cache","payload"),0x230010,"target_not_currently_bound"),
            ("native_identity_overclaim",("target_binding","native_full_file_identity"),"VERIFIED_BY_HEADER","native_file_identity_claim_not_verified_by_this_contract"),
            ("old_adapter",("target_binding","metadata_adapter_profile"),"mpckpt01-v1","legacy_metadata_core_not_compatible"),
        ]
        for name,path,value,reason in cases:
            with self.subTest(name=name):
                args=example();change(args,path,value)
                # Pin each altered receipt deliberately to exercise its semantic
                # guard, rather than stopping every case at the receipt hash.
                args["expected"]["source_receipt_sha256"]=c.canonical_sha(args["source"])
                args["target_binding"]["source_receipt_sha256"]=args["expected"]["source_receipt_sha256"]
                args["expected"]["target_binding_sha256"]=c.canonical_sha(args["target_binding"])
                with self.assertRaisesRegex(c.ContractError,"^"+reason+"$"):
                    c.prepare_guest_checkpoint(**args)

    def test_unpinned_receipt_rejected(self):
        args=example();args["source"]["file"]["created_new"]=False
        with self.assertRaisesRegex(c.ContractError,"source_receipt_not_pinned"):
            c.prepare_guest_checkpoint(**args)
        args=example();args["target_binding"]["slot"]=64
        with self.assertRaisesRegex(c.ContractError,"target_binding_not_pinned"):
            c.prepare_guest_checkpoint(**args)

    def test_malformed_and_corrupt_local_bytes(self):
        args=example();args["target_binding"]={}
        args["expected"]["target_binding_sha256"]=c.canonical_sha({})
        with self.assertRaisesRegex(c.ContractError,"malformed_or_missing_evidence"):
            c.prepare_guest_checkpoint(**args)
        args=example();args["staged_bytes"]=b"x"+args["staged_bytes"][1:]
        with self.assertRaisesRegex(c.ContractError,"local_staged_bytes_mismatch"):
            c.prepare_guest_checkpoint(**args)


if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ContractFixtures)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    folder=Path(__file__).resolve().parent/"checkpoint_push_to_guest_contract_fixtures"/datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    folder.mkdir(parents=True,exist_ok=False)
    report={"schema":"san14.push-to-guest-offline-fixtures.v1","result":"PASS" if result.wasSuccessful() else "FAIL",
            "unittest_methods":result.testsRun,"semantic_rejection_subcases":35,
            "game_access":False,"native_calls":False,"existing_save_reads":False,"real_checkpoint_export_or_load_tested":False,
            "scope":"Pure synthetic evidence validation and rejection only; no proof any required native receipt exists.",
            "module_sha256":hashlib.sha256(Path(c.__file__).read_bytes()).hexdigest(),
            "test_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (folder/"result.json").open("x",encoding="utf-8") as file:
        json.dump(report,file,indent=2)
    if result.wasSuccessful():
        with (folder/"synthetic_preparation_example.json").open("x",encoding="utf-8") as file:
            json.dump(c.prepare_guest_checkpoint(**example()),file,indent=2)
    print(folder)
    raise SystemExit(0 if result.wasSuccessful() else 1)
