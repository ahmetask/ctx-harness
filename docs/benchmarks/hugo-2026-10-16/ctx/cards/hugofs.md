---
module: hugofs
updated: 2026-10-15
verified: aae02ca
anchors:
  hugofs/glob/glob.go: 8362952e51ac
  hugofs/glob/filename_filter.go: 47831e5d0b5e
  hugofs/files/classifier.go: 153e10c0d155
  hugofs/rootmapping_fs.go: 9508bfd275fd
  hugofs/fileinfo.go: 13761bb9eabf
  hugofs/noop_fs.go: 8d4fbc6cf434
  hugofs/filename_filter_fs.go: d4736cb6bcc9
  hugofs/fs.go: e25634ce165c
  hugofs/component_fs.go: f32301ef774d
  hugofs/hashing_fs.go: 0c127295f75b
  hugofs/createcounting_fs.go: 7b883f935714
  hugofs/decorators.go: 0b6f0e1b8f36
  hugofs/hasbytes_fs.go: 427729574cca
  hugofs/openfiles_fs.go: 68d1a401abeb
  hugofs/stacktracer_fs.go: 657629519834
  hugofs/walk.go: 904fa7feb782
  hugofs/glob.go: 43f2724cf77a
  hugofs/dirsmerger.go: c8838ac84743
---
Owns the virtual filesystem layer: the afero-based FS decorators, root-mapped mounts, filename include/exclude filtering, glob walking and component-folder classification.

## Invariants
- Inclusions are checked before exclusions in `FilenameFilter.doMatch`: a path matching an inclusion is kept even if an exclusion also matches.
- With no inclusions and no `shouldInclude` func, `FilenameFilter.doMatch` returns true for any path not excluded; a filter with inclusions returns false for anything unmatched.
- `NewFilenameFilter` adds every parent directory of an inclusion to `dirInclusions`; these are consulted only when `isDir` is true and inclusions exist, so directory walks can descend into included paths.
- `NewFilenameFilter` returns `nil, nil` when both lists are nil, and a nil `*FilenameFilter` matches everything.
- `FilenameFilter.Match` ANDs the chained filters added via `Append`; every nested filter must accept the path.
- `Glob` in `hugofs/glob.go` lowercases the pattern and skips directories deeper than the pattern's slash count unless the pattern contains `**`.
- `ResolveComponentFolder` matches component names by raw string prefix (no path-boundary check) against the sorted `ComponentFolders` list.

## Tests
`cache/filecache/filecache_test.go`, `common/paths/pathparser_test.go`, `create/content_test.go`, `deploy/deploy_test.go`, `helpers/testhelpers_test.go`, `hugofs/filename_filter_fs_test.go`, `hugofs/rootmapping_fs_test.go`, `hugolib/content_factory_test.go`, `hugolib/filesystems/basefs_test.go`, `hugolib/hugo_modules_test.go`, `hugolib/hugo_sites_build_test.go`, `hugolib/mount_filters_test.go`, `hugolib/pagebundler_test.go`, `hugolib/template_test.go`, `hugolib/testhelpers_test.go`, `internal/js/esbuild/resolve_test.go`, `modules/client_test.go`, `resources/page/testhelpers_test.go`, `resources/resource_transformers/cssjs/postcss_integration_test.go`, `resources/testhelpers_test.go`, `resources/transform_test.go`, `source/content_directory_test.go`, `tpl/data/resources_test.go`
