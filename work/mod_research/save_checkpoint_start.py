"""Retirement shim for the historical standard-slot prototype; no game access.

There was no live launcher for this profile before this shim. The old DLL and
fixture evidence are retained for research only. 412520 is replace-top, not push.
"""
from pathlib import Path
import argparse,json
def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group()
    g.add_argument('--execute',action='store_true');g.add_argument('--dry',action='store_true');g.add_argument('--precheck',action='store_true');args=p.parse_args()
    print(json.dumps({'result':'RETIRED_UNSAFE_STATE_ENTRY','game_access':False,'readonly_retirement_status':True,
                      'reason':'The historical standard-slot DLL also uses412520/type2, which replaces UserStrategy and can advance the game. All hook/native execution is blocked, including on an empty standard slot.',
                      'retirement':str(Path(__file__).resolve().parent/'private_checkpoint_save_RETIRED.json')}))
    if args.execute or args.dry:raise SystemExit(2)
if __name__=='__main__':main()
