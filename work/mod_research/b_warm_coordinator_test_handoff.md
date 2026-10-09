# Independent coordinator file/lease verification

The root agent owns `b_warm_coordinator.py`, its typed contract and native helper. This independent test owns only `b_warm_coordinator_test.py` and this handoff. No game process, Steam path or UI was accessed.

`py -3 work/mod_research/b_warm_coordinator_test.py` executes the actual `run_two` function and actual `b_warm_staging` Windows file operations in newly created private directories. `NativePortDouble` is explicit: opening DLL banks, native handover, loading and native completion are substitutes. Its completion dictionary is never presented as native evidence. The separately tested production helper/factory pair remains necessary; these file tests do not execute `Resident` remote calls.

Final result: private `b_warm_coordinator_test_runs/20261009-181530-065915/result.json`, **5/5 PASS**, SHA-256 `d420ff63be9aca94ca65473056e74157cc2948d7feebe3661827e6ef6df6b706`. Eight loaded repository Python sources and 35 generated private files are pinned and independently rehashed. The source test hash is `66931d98f081626b47a0c29cc8f2b920cc6833eae2009f26e096ffe11254001a`.

- Two loads observe the actual staged first/second bytes in order. Handover precedes second replacement; the displaced backup and separate verified-old archive equal the first bytes. Both completion callbacks run, and final room/world permissions remain false.
- A refused handover never creates a staging directory and never changes the first file.
- Drift of the first file after the first retired completion rejects staging and never calls the second loader.
- An actual Windows reader withholding delete sharing prevents replacement. The original bytes remain and no second load starts.
- Failure of the second load calls `abort` while the real file lease remains held. Inside `abort`, a real `CreateFileW` request for write access fails with `ERROR_SHARING_VIOLATION`; after unwinding, it can open. The second file and backup are retained, `finish` is never called, and no Ready result is returned. This checks lease ordering, not native drain after Stop.

Failure retained: run `181517-456683` had 4 passing checks and one test error because the test decoded a Chinese Windows error message using the machine's default GBK rather than the production UTF-8 record encoding. Only the test's explicit UTF-8 read was corrected. The failing directory/log and all staging outcomes remain intact.

## Independent source review findings

The first review identified two integration issues, fixed by the root agent before this final run: post-load file-identity verification must remain within the exception region that aborts while the lease is held; and the chosen production bank must be the factory-pair build's actual output, with helper native source identity tied to the pair's executed same-source wrapper. The revised launcher also verifies all seven described bank code bridges against the approved image.

Reviewed coordinator Python SHA: `a92cd13bf10677a7809633f54b39527a62194af252ad6184f12bed917a16fae9`; typed contract SHA: `76b14219e88d201e9dcd7dc89650f6580f4ca7eb1a1dae70756339c222e0d237`; native helper CPP SHA: `900203532e812899c04adfa17b0bf3217a9141c9266bc52209ded224b8b8274e`. No further narrow-path blocker was found in the reviewed serialized local-controller use. The native helper's internal `Handover` remains scoped to previously approved resident modules and the captured six sources; it is not a general remote authorization service. The pair executes the wrapper linked into its own host, while the helper DLL has separate ABI tests; those are distinct evidence layers.

A successful Stop or released file handle is not native load-drain evidence. Unknown remote calls retain their lifetime and block automatic retry; failed native loads must keep their staged file unchanged until normal process exit or separate verified drain. These tests do not supply that drain permission, full input exclusion, map cover, world equality, or a room-next-period ACK.
