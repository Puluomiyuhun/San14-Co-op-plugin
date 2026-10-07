"""Build an evidence-preserving read-only restore verifier for the new pilot."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'verify_reward_execution_restore.py').read_text(encoding='utf-8')
s=s.replace('from run_reward_execution_pilot import','from run_second_force_reward import').replace('reward-execution','second-force-reward')
s=s.replace("'checkpoint34_unchanged':True,'original_update_restored':True,",
            "'checkpoint34_unchanged':True,'original_update_restored':True,\n                'global_rng_before':before['global_rng'],'global_rng_restored':restored['global_rng'],\n                'known_rng_equal':before['global_rng']==restored['global_rng'] and before['world_rng_fields_hex']==restored['world_rng_fields_hex'],\n                'rng_state_rewritten':False,")
s=s.replace('NATIVE_REWARD_EXECUTION_AND_RESTORE_PASS','NATIVE_SECOND_FORCE_REWARD_EXECUTION_AND_RESTORE_PASS')
(ROOT/'verify_second_force_reward_restore.py').write_text(s,encoding='utf-8')
print('Prepared second-force restore verifier')
