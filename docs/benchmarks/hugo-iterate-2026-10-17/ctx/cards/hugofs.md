---
module: hugofs
updated: 2026-10-16
verified: aae02ca61
anchors:
  hugofs/glob/glob.go: 8362952e51ac
  hugofs/glob/filename_filter.go: 47831e5d0b5e
  hugofs/files/classifier.go: 153e10c0d155
  hugofs/rootmapping_fs.go: 9508bfd275fd
  hugofs/fs.go: e25634ce165c
  hugofs/hashing_fs.go: 0c127295f75b
  hugofs/hasbytes_fs.go: 427729574cca
  hugofs/walk.go: 904fa7feb782
  hugofs/fileinfo.go: 13761bb9eabf
  hugofs/noop_fs.go: 8d4fbc6cf434
  hugofs/filename_filter_fs.go: d4736cb6bcc9
  hugofs/component_fs.go: f32301ef774d
  hugofs/createcounting_fs.go: 7b883f935714
  hugofs/decorators.go: 0b6f0e1b8f36
  hugofs/openfiles_fs.go: 68d1a401abeb
  hugofs/stacktracer_fs.go: 657629519834
  hugofs/glob.go: 43f2724cf77a
  hugofs/dirsmerger.go: c8838ac84743
---
Decorated filesystem layer over the source directories: root mappings for mounts (`rootmapping_fs.go`), glob and filename filters (`hugofs/glob/`), and component folder resolution (`hugofs/files/`). Owner: Bjørn Erik Pedersen.

## Invariants
- Glob patterns are compiled lowercased and input is lowercased before matching, so filename matching is case-insensitive (`GetGlob`, `globDecorator.Match` in `hugofs/glob/glob.go`).
- Inclusions are tested before exclusions, so a filename matching any inclusion is kept even if an exclusion also matches (`FilenameFilter.doMatch` in `hugofs/glob/filename_filter.go`).
- A filter with exclusions only accepts everything not excluded; a filter with inclusions (or an inclusion func) rejects anything unmatched (last line of `doMatch`).
- Each ancestor directory of an inclusion is added to `dirInclusions`, consulted only for directories, so directory walks descend toward included files (`NewFilenameFilter`).
- `NewFilenameFilter(nil, nil)` returns a nil filter; a nil `*FilenameFilter` matches everything, and `Append` on nil returns the argument (`hugofs/glob/filename_filter.go`).
- Nested filters added with `Append` are ANDed in `FilenameFilter.Match`.
- The glob cache is keyed by the raw pattern on lookup but by the slash-normalized pattern on store, so patterns containing backslashes never hit the cache (`globCache.GetGlob`). Compile errors are cached too.
- `files.ResolveComponentFolder` matches by string prefix, not path segment, so `contentfoo/x` resolves to `content`, and the first match in sorted `ComponentFolders` wins (`hugofs/files/classifier.go`).

## History
- `hugofs/rootmapping_fs.go`: Fix same resource file published more than once

## Tests
Entry: `hugofs/rootmapping_fs_test.go`, `hugofs/filename_filter_fs_test.go`, `hugolib/filesystems/basefs_test.go`, `hugolib/mount_filters_test.go`.
