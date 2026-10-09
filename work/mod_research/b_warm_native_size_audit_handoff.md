# Warm load: actual precommit native-size mismatch

This audits the first real two-file diagnostic failure, archived outside the
repository in `../mod_research/b_warm_pair_diagnostic_runs/20261009-212018-163311`.
The root agent captured only the installed, owned bank DLL's `.data` after
requesting normal game exit and before the user completed that exit. This audit never opens a game process, accesses
Steam, calls an export, installs a hook or authorizes a retry.

## Confirmed cause

`SessionError=7` is `checkpoint_forward_native_session::Error::Request`.
`b_warm_profile_request.cpp::CommitGameBefore` reached
`fresh_complete_native_reads`, then `native_storage_read::Verify` rejected at
`native_size_before`. The exact evidence is:

- Input/local file: 274920 bytes, SHA
  `afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95`.
- Local hash matched the accepted profile; native FileExists returned true.
- Native GetFileSize returned **274880**, rather than 274920.
- `existsCalls=1`, `sizeCalls=1`, `readCalls=0`;
  `sizes=[274880,0,0]`, `readReturns=[0,0]`.
- Evidence `matched=false`, `osError=0`, `exceptionCode=0`;
  both native hashes remain zero because FileRead had not begun.

The normal rejection precedes durable request intent and pending-slot CAS.
The native load/identity worker therefore never started. Native Menu creation
did occur; the retained six warm hooks were not retired by this failure.
The root's separate Stop/exit evidence owns cleanup conclusions.

The approved DLL contains the immutable stage string. Two aligned complete
152-byte `native_storage_read::Evidence` structures reference that string and
have identical bytes. Their dump offsets are `0x3ec8` and `0x61f0`, corresponding
to module RVAs `0x4aec8` and `0x4d1f0`; the stage pointers themselves are eight
bytes later. This is matching full structured evidence plus the DLL string and
accepted input hash, not searching for a coincidental integer.

Earlier hypotheses about malformed path or an uninitialized Lease are not
supported: the archived config contains the correct backslash-delimited CC03
path, and execution had passed Verify's input and initial context checks.
No Lease address was decoded and its exact handle value is not claimed.

The discrepancy is consistent with stale native metadata after an external
file replacement. It does **not** by itself establish why the native view is
different: cache, storage namespace/path and publication semantics still need
to be distinguished. Do not weaken the size check or pad/truncate the archive.

## Minimal next repair target

The staging-to-native-storage publication boundary is the concrete gap. Before
requesting a load, establish that the same validated native storage interface
observes the new file's size and full bytes; an OS file hash alone is insufficient.
Any successor must preserve the existing backup, previous-bank retirement and
no-reader boundary. If a native write/refresh mechanism is needed, its exact
ABI and observable result require separate evidence; none was called here.
The two-bank path needs this for every replacement, not only initial startup.

Do not retry the terminal process lifetime, synthesize a successful read receipt
or bypass original native FileRead validation. A useful next regression is an
explicit storage view retaining the old size while disk already has the new
file, with rejection before load; then test the actual supported publication
mechanism before another live attempt. No additional broad fixture framework
is required to explain this captured failure.

## Reproduction and hashes

From the repository, the following command only reads local archived inputs
and exclusively creates the specified result file (choose a new output name
if it already exists):

```powershell
py -3 work/mod_research/b_warm_native_size_audit.py --archive ../mod_research/b_warm_pair_diagnostic_runs/20261009-212018-163311 --output ../mod_research/b_warm_pair_diagnostic_runs/20261009-212018-163311/native-size-audit.json
```

The first execution passed: `CONFIRMED_NATIVE_SIZE_MISMATCH_BEFORE_READ`, two
identical structures. No frozen predecessor was edited.

- Script SHA:
  `ca6f3f8e39d9467c514f6666253736737ed89ac8455827bc800ecc2c6a61fa70`.
- Private result SHA:
  `3b3f7f9a8d8ebb4d023ba2154a241dcf8f7e4990bc2ff2fc191e40a9af3c92eb`.
- Approved bank DLL SHA:
  `e9766e073b4a4b63d230c1f7e788d477c4f5ebb7e660a2ed3dcc5b7c8342bf05`.
- Captured `.data` SHA:
  `166bd00ae336ac24b427d197a44be06d2554bd5e719ecfb891c15c01920aeb12`.

The result pins the metadata, config, local archive, DLL, dump, layout header,
Verify implementation, request implementation, profile codec and audit script.
Only this source and explanatory handoff are suitable for Git; the dump and
raw private result remain local. Default invocation only prints help.
