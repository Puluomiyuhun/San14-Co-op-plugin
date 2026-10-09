# First-failure evidence for the next controlled A save

`a_save_diagnostic_start.py` is an explicit successor of the frozen
`a_save_runtime_start.py`. It retains the one-process once claim, one Submit,
complete original-save backup, exact artifact verification, Stop and separately
checked source restoration. It adds no save/load/advance retry.

Before target mutation it requires the bounded `ASaveCoveredGateFirstFailure`
DATA export. Its finalization reads that data using `a_save_failure_diagnostic.py`
and saves `first-failure-diagnostic.json`. The process handle has only query,
read and synchronize rights. The reader does not use a debugger, write memory,
inject input, create a remote thread or call any target function. Failure to
read diagnostic evidence is recorded separately and cannot skip cleanup or
replace the original error. Uncertain cleanup calls now also retain their
structured `RemoteCallUnknown.record` in the final result.

The reader binds PID/creation time, image path/hash, exact loaded DLL path/base
and file hash before and after two memory reads. It verifies PE headers and a
readable/writable non-executable image DATA range. A loader-updated ImageBase
is accepted only when the entire header equals the exact disk header with that
one field set to the actual module base; arbitrary header differences reject.

The 84-byte export uses the producer's publish-last `stage`. Equal nonzero
samples give a first-failure observation. A zero stage is `NOT_PUBLISHED`,
including partly filled payloads; it does not prove there has been no failure.
Different samples are `UNSTABLE`. Neither outcome grants restoration or marks
a save accepted. Stage 4 identifies the layout category, not the exact failed
predicate or the historical cause of the previous game failure.

## Verification

`py -3 work/mod_research/a_save_failure_diagnostic_test.py` builds a small DLL
from the actual C++ declaration, launches an owned Python child to load and
publish its DATA, and reads it with actual Windows RPM. Ten checks pass in
private run `a_save_failure_diagnostic_test_runs/20261009-135136-315886`:
native structure size/offset, unpublished/published data, process birth,
module base, DLL and EXE identities, unknown layout, changing publication,
and incomplete reads. The child exits normally. It is not the game or a
game-like save simulation; it tests only the new diagnostic transport.

Earlier attempts are retained: the first test runner failed to decode compiler
output using its locale default; the next found the real Windows loader's
ImageBase header update. The test now preserves compiler output with explicit
decoding, and the reader checks the exact relocated-header variant. Production
validation was not replaced by a blanket header exemption.

The successor launcher was syntax checked and its changes against the frozen
launcher reviewed. It has **not run in the game**. Its build argument still
expects the tested inner `abi` directory, with `production`, `abi_executed`,
source pins and `schema.json`, rather than an outer builder wrapper. Select the
latest fully composed production and publisher builds in `docs/HANDOFF.md`.
The new diagnostic reader cannot find this export in the old failed Runtime;
it must not be used as a reason to reinstall or replay that old process.

No game, Steam save, UI or network listener was accessed by this development.
The previous process's normal exit remains unconfirmed. The next live gate is
still a fresh-process verified new save **and** verified source restoration.
