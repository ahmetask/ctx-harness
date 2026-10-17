---
module: common
updated: 2026-10-16
verified: aae02ca61
anchors:
  common/hashing/hashing.go: 5eb424cc0726
  common/maps/cache.go: f4f5095fc060
  common/maps/scratch.go: a2fcd75e9ee5
  common/maps/maps.go: c47d1d0dbdba
  common/maps/params.go: d94c6007f27e
  common/types/types.go: 6fec0c57b4ce
  common/types/evictingqueue.go: 57b4386baa0f
  common/types/closer.go: cdfe11cae25c
  common/types/convert.go: 9bbb74eb8b47
  common/terminal/colors.go: d2ed42f28976
  common/paths/pathparser.go: 66e9f474b347
  common/paths/path.go: 3f80808d5fab
  common/paths/url.go: affe44734680
  common/htime/time.go: 4719f39125d6
  common/text/position.go: aa91445e3300
  common/text/transform.go: 54d7350ba678
  common/herrors/errors.go: 3cf69fb3cc7b
  common/herrors/file_error.go: b38e436f0e17
  common/herrors/error_locator.go: 8f9170322cc3
  common/herrors/line_number_extractors.go: cdd5ffafef56
  common/hreflect/helpers.go: 8991dfea3270
  common/collections/stack.go: f24be9f88dba
  common/collections/slice.go: 230d7fbe244a
  common/collections/append.go: 25d0f92c91a3
  common/collections/collections.go: 4b888d718239
  common/collections/order.go: 74a204a53365
  common/hugio/readers.go: 63376ba3f8be
  common/hugio/writers.go: 21a136be679d
  common/hugio/hasBytesWriter.go: e33418735615
  common/hugio/copy.go: 605194ed2e48
  common/math/math.go: af721fab5941
  common/hstrings/strings.go: 3f016794ccc5
  common/loggers/logger.go: c9500a678302
  common/loggers/handlerterminal.go: db1bad858896
  common/loggers/handlersmisc.go: 9795b89f9cca
  common/loggers/handlerdefault.go: c003f2d52d41
  common/loggers/loggerglobal.go: d30aad1a25c1
  common/hexec/exec.go: acaea9ee6a2a
  common/hugo/hugo.go: ee0495606e59
  common/hugo/version_current.go: a4287dbe925a
  common/hugo/version.go: 54c58e45e754
  common/hugo/vars_withdeploy.go: d99ffe74198a
  common/hugo/vars_withdeploy_off.go: 8ae49f585d5b
  common/hugo/vars_extended.go: ec9ff517c31c
  common/hugo/vars_regular.go: 45964549db41
  common/types/css/csstypes.go: a3d80c857376
  common/urls/baseURL.go: 20663fc29559
  common/urls/ref.go: 0c1cc725d184
  common/types/hstring/stringtypes.go: bf04fdb036a5
  common/constants/constants.go: 4a7cf051d3ed
  common/predicate/predicate.go: b10adf878c15
  common/para/para.go: ac48691b51c9
  common/rungroup/rungroup.go: 931822da143b
  common/hcontext/context.go: 17af919f0a8a
  common/tasks/tasks.go: cce09e296d69
---
Shared Go utilities (hashing, generic maps and caches, Scratch, error and logger helpers, paths and URLs, hugio) imported across Hugo packages; no dependency on the packages that use it.

## Invariants
- `hashing.HashUint64` / `HashString` panic when hashstructure fails. Values pass through `toHashable`, which uses `Key()` or `IdentityProvider.GetIdentity()` because hashstructure only sees exported fields. Output is for identity, not change detection (full content of e.g. Page is not hashed).
- `hashing.XXHashFromReader` uses a pooled hasher with a 48 KiB buffer (`xxhashReadFrom`), reset on return to the pool.
- `maps.Cache.InitAndGet` runs `init` once under the write lock using a double-checked `hasBeenInitialized` flag. `Cache.Reset` and `Cache.Drain` clear that flag.
- `maps.Cache.GetOrCreate` calls `create` while holding the write lock.
- `maps.Cache.Get` on a nil `*Cache` returns zero and false.
- `maps.Scratch.Add`: the first value is stored as-is. Later values append when the stored value is a slice or array (`collections.Append`), otherwise they are summed with `math.DoArithmetic`.
- `maps.Scratch.Values` returns the raw backing map without copying. Per its doc comment it is only safe on locally scoped Scratch instances, not `.Page.Scratch`.
- `maps.StoreProvider.Store` documents that the Scratch it returns is not reset on server rebuilds.

## History
- `common/maps/cache.go`: Fix concurrent map read and map write in short page lookups
- `common/types/types.go`: Improve Katex error handling and fix handling of large expressions
- `common/types/evictingqueue.go`: Fix panic on server rebuilds when using both base templates and template.Defer
- `common/herrors/errors.go`: common/herrors: Fix the deferred error message cleaner regexp
- Changes together with: `resources/image.go` (3 commits, via `hashing.go`), `markup/goldmark/render_hooks.go` (2 commits, via `stringtypes.go`), `markup/goldmark/blockquotes/blockquotes.go` (2 commits, via `stringtypes.go`)

## Tests
Package-local: `common/hashing/hashing_test.go`, `common/maps/maps_test.go`, `common/maps/scratch_test.go`, `common/maps/params_test.go`, `common/herrors/file_error_test.go`, `common/loggers/logger_test.go`, `common/loggers/handlerterminal_test.go`, `common/predicate/predicate_test.go`. Most consumers are exercised through `hugolib/*_test.go` and `resources/*_test.go`.
