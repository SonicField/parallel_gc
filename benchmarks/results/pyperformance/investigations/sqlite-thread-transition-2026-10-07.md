# `sqlite_synth` first-thread transition investigation

## Result

The shared GIL and free-threaded `sqlite_synth` regression is primarily caused by the process creating its first thread, not by cyclic collection.

Both parallel collectors create helper threads when `gc.enable_parallel()` initializes the pool. On glibc, the first `pthread_create()` changes `__libc_single_threaded` from 1 to 0. The flag does not return to 1 after the threads exit. Code in libc and dependent libraries can therefore switch permanently from never-threaded fast paths to thread-safe paths.

One unrelated Python thread, created and joined without ever enabling parallel GC, reproduced nearly the entire regression in both builds.

## Relationship to the full ABBA result

The complete rigorous campaigns reported `sqlite_synth` 38.1% slower in the GIL build and 10.4% slower in the free-threaded build. Both halves of both ABBA sequences reproduced the result.

Those campaigns did not record a collection count. This diagnostic tested whether collection work caused the difference.

## Method

The diagnostic used the same parallel-aware-PGO binaries as the complete campaigns:

| Build | Executable SHA-256 |
|---|---|
| GIL | `58ab3f1160542d3ecf804202d3d586234759a33424659364525e66b0dedaa47c` |
| FT | `ff5b3b4570fec2e6b7c0f1b202f41a933b3163718ac24d7052e247612c5715f8` |

Each diagnostic process executed the unmodified `bench_sqlite()` function from pyperformance revision `ccc0aeb7ad46d65b6dcd4160e0fdda4d885852dd`. Every invocation used 131,072 loops. Each fresh process ran one warmup followed by five measured invocations. The table reports the mean of the five measurements, averaged across three fresh processes.

The modes were:

| Mode | Preparation before importing and running the benchmark |
|---|---|
| Never threaded | Keep parallel GC disabled and create no thread. |
| One unrelated thread | Start and join one `threading.Thread`; never enable parallel GC. |
| Thread, then parallel GC | Start and join one unrelated thread, then enable parallel GC. |
| Parallel GC | Enable parallel GC directly. |
| Enable, then disable | Enable and disable parallel GC before running the workload. |
| Parallel GC, automatic GC off | Enable parallel GC and call `gc.disable()` before running the workload. |

A `gc.callbacks` observer and differences in `gc.get_stats()` measured collection activity. Parallel collector statistics were read before and after each workload.

## Fixed-loop timings

| Build | Mode | Mean time | Range of per-process means | Change from never threaded |
|---|---|---:|---:|---:|
| GIL | Never threaded | 0.1846 s | 0.1841-0.1852 s | reference |
| GIL | One unrelated thread | 0.2565 s | 0.2554-0.2571 s | 38.9% slower |
| GIL | Thread, then parallel GC | 0.2596 s | 0.2569-0.2617 s | 40.7% slower |
| GIL | Parallel GC | 0.2594 s | 0.2591-0.2596 s | 40.5% slower |
| FT | Never threaded | 0.1722 s | 0.1706-0.1752 s | reference |
| FT | One unrelated thread | 0.1918 s | 0.1886-0.1936 s | 11.4% slower |
| FT | Thread, then parallel GC | 0.1940 s | 0.1911-0.1987 s | 12.6% slower |
| FT | Parallel GC | 0.1952 s | 0.1923-0.1968 s | 13.3% slower |

After the process was already threaded, enabling parallel GC added 1.24% to the GIL diagnostic mean and 1.15% to the FT diagnostic mean. These small differences were not measured with a randomized ABBA design and must not be treated as established effect sizes.

Creating and joining 15 unrelated threads produced the same result as one unrelated thread. Disabling automatic cyclic GC did not remove the enabled-mode slowdown. Enabling and then disabling parallel GC retained the slowdown even though the FT pool had been destroyed and its workers had exited.

No measured benchmark invocation triggered a cyclic collection. GIL parallel statistics remained at zero attempted and zero successful collections. FT phase timings did not change across the workload.

## Direct glibc observation

A temporary C extension read `__libc_single_threaded` from `<sys/single_threaded.h>` in fresh processes.

| Build | Startup | After `gc.enable_parallel()` | After `gc.disable_parallel()` |
|---|---:|---:|---:|
| GIL | 1 | 0 | 0 |
| FT with the GIL kept disabled | 1 | 0 | 0 |

Creating and joining one unrelated Python thread produced the same 1-to-0 transition. The FT probe used `PYTHON_GIL=0` so loading the diagnostic extension did not enable the GIL.

## Conclusions

The evidence rejects these explanations for `sqlite_synth`:

- parallel graph traversal;
- collection entry or stop-the-world coordination;
- adaptive worker selection;
- finalization or deallocation inside cyclic collection;
- automatic collection frequency.

The common trigger is the one-way transition from a never-threaded process to a process that has created a thread. Parallel GC currently causes that transition at activation time because it creates the persistent pool immediately.

This is a real cost for an application that enables parallel GC before any other thread exists, even if its workload never needs parallel collection. It is not an incremental collector cost in an application that has already created threads. A rigorous control that alternates an already-threaded process with and without the pool is required before assigning a precise value to the remaining approximately 1% diagnostic difference.

The lower-level library operation responsible for the lost time has not been measured. glibc's single-thread optimization commonly removes synchronization from allocation and other libc paths, and `sqlite_synth` performs substantial C-library and SQLite work, but this diagnostic does not identify the hot instruction. Assembly or `perf` evidence is required before making that narrower claim.

## Design implication

Immediate pool creation makes `gc.enable_parallel()` itself perform the irreversible first-thread transition. Deferring pool creation until the first collection selected for parallel execution could preserve never-threaded fast paths for workloads that remain on the serial path. That alternative would move thread-creation latency and thread-creation failure into a collection, so it is a design trade-off rather than an automatic repair. No implementation change is authorized by this result.
