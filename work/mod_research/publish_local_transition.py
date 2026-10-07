"""Package the research controller and verify its delivered import paths.

No game/device/window access. All acknowledgements in these tests are synthetic.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import importlib
import json
import sys
import unittest

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'outputs' / 'san14-link'
NAMES = ('transition_visual_surface', 'transition_input_gate_contract', 'checkpoint_local_transition')

for name in NAMES:
    source = (HERE / (name + '.py')).read_text(encoding='utf8')
    if name == 'checkpoint_local_transition':
        source = source.replace('from pathlib import Path\n', '').replace('import sys\n', '')
        source = source.replace('HERE = Path(__file__).resolve().parent\nsys.path.insert(0, str(HERE.parents[1] / "outputs" / "san14-link"))\n', '')
    target = OUT / (name + '.py')
    if target.exists() and target.read_text(encoding='utf8') != source:
        raise RuntimeError('Existing delivered module differs: ' + name)
    target.write_text(source, encoding='utf8')

sys.path.insert(0, str(OUT))
for name in NAMES:
    module = importlib.import_module(name)
    assert Path(module.__file__).resolve().parent == OUT.resolve()

cases = (
    ('checkpoint_local_transition_test', 'LocalTransitionTests'),
    ('transition_input_gate_contract_test', 'ContractTests'),
    ('transition_visual_surface_test', 'SurfaceTests'),
)
suite = unittest.TestSuite()
for module_name, class_name in cases:
    module = importlib.import_module(module_name)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, class_name)))
result = unittest.TextTestRunner(verbosity=1).run(suite)
report = {
    'schema': 'san14.delivered-local-transition.v1',
    'created': datetime.now().astimezone().isoformat(),
    'result': 'PASS' if result.wasSuccessful() else 'FAIL',
    'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'modules': {name: {'path': str(OUT / (name + '.py')),
        'sha256': hashlib.sha256((OUT / (name + '.py')).read_bytes()).hexdigest()} for name in NAMES},
    'evidence_source': 'SYNTHETIC_FIXTURE', 'real_game_access': False,
    'native_gameplay_enabled': False, 'native_visual_cover_implemented': False,
    'native_input_interception_implemented': False,
}
target = OUT / '本地同步控制器验证.json'
target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(0 if result.wasSuccessful() else 1)
