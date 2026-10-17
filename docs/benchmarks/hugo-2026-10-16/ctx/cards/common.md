---
module: common
updated: 2026-10-15
verified: aae02ca
anchors:
  common/hashing/hashing.go: 5eb424cc0726
  common/maps/params.go: d94c6007f27e
  common/maps/maps.go: c47d1d0dbdba
  common/maps/cache.go: f4f5095fc060
  common/maps/scratch.go: a2fcd75e9ee5
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
  common/herrors/file_error.go: b38e436f0e17
  common/herrors/errors.go: 3cf69fb3cc7b
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
  common/loggers/handlersmisc.go: 9795b89f9cca
  common/loggers/handlerterminal.go: db1bad858896
  common/loggers/handlerdefault.go: c003f2d52d41
  common/loggers/loggerglobal.go: d30aad1a25c1
  common/hexec/exec.go: acaea9ee6a2a
  common/hugo/hugo.go: ee0495606e59
  common/hugo/version.go: 54c58e45e754
  common/hugo/vars_extended.go: ec9ff517c31c
  common/hugo/vars_regular.go: 45964549db41
  common/hugo/vars_withdeploy.go: d99ffe74198a
  common/hugo/vars_withdeploy_off.go: 8ae49f585d5b
  common/hugo/version_current.go: a4287dbe925a
  common/types/css/csstypes.go: a3d80c857376
  common/urls/baseURL.go: 20663fc29559
  common/urls/ref.go: 0c1cc725d184
  common/types/hstring/stringtypes.go: bf04fdb036a5
  common/predicate/predicate.go: b10adf878c15
  common/constants/constants.go: 4a7cf051d3ed
  common/para/para.go: ac48691b51c9
  common/rungroup/rungroup.go: 931822da143b
  common/hcontext/context.go: 17af919f0a8a
  common/tasks/tasks.go: cce09e296d69
---
Shared leaf utilities (hashing, `maps.Params`, types, collections, paths, loggers, herrors, hugio, hexec, hugo version vars) imported across Hugo; no site-build logic of its own.

## Invariants
- `PrepareParams` lower-cases every key and converts nested `map[string]any`/`map[string]string` to `Params`; `ToParamsAndPrepare` runs it and returns an empty `Params` for nil input.
- `getNested` lower-cases each index before lookup, so `Params.GetNested` is case-insensitive; `LookupEqualFold` provides the same for plain maps.
- The `_merge` key is a processing instruction: `Params.merge` skips it when copying, and `CleanConfigStringMapString` strips it from `map[string]string` without mutating the input.
- A `_merge` value on the destination map takes precedence over the strategy passed to `MergeParamsWithStrategy`; `none` and `shallow` suppress adding new keys (`Params.merge`).
- `SetParams` overwrites scalar values from `src` but recurses only when both sides are `Params`.
- `HashString`/`HashUint64` are identity hashes, not change detectors: they panic on unhashable input, and `toHashable` substitutes `Key()` or `GetIdentity()` for identity types before hashing.
- `Cache` (`common/maps/cache.go`) guards its map with an RWMutex; a nil `*Cache` returns zero values from `Get`.

## Tests
`cache/dynacache/dynacache_test.go`, `cache/filecache/filecache_test.go`, `codegen/methods_test.go`, `common/herrors/file_error_test.go`, `common/loggers/handlerterminal_test.go`, `common/loggers/logger_test.go`, `common/predicate/predicate_test.go`, `config/commonConfig_test.go`, `config/defaultConfigProvider_test.go`, `config/namespace_test.go`, `deploy/deploy_test.go`, `helpers/testhelpers_test.go`, `hugofs/walk_test.go`, `hugolib/alias_test.go`, `hugolib/cascade_test.go`, `hugolib/config_test.go`, `hugolib/doctree/nodeshiftree_test.go`, `hugolib/hugo_modules_test.go`, `hugolib/hugo_sites_build_errors_test.go`, `hugolib/hugo_sites_build_test.go`, `hugolib/mount_filters_test.go`, `hugolib/page_test.go`, `hugolib/pagebundler_test.go`, `hugolib/rebuild_test.go`, `hugolib/renderstring_test.go`, `hugolib/resource_chain_test.go`, `hugolib/site_output_test.go`, `hugolib/testhelpers_test.go`, `internal/js/esbuild/batch_integration_test.go`, `langs/i18n/i18n_test.go`, `markup/asciidocext/convert_test.go`, `markup/goldmark/convert_test.go`, `markup/org/convert_test.go`, `markup/pandoc/convert_test.go`, `markup/rst/convert_test.go`, `markup/tableofcontents/tableofcontents_test.go`, `media/mediaType_test.go`, `modules/client_test.go`, `modules/config_test.go`, `resources/image_test.go`, `resources/images/filters_test.go`, `resources/page/page_markup_test.go`, `resources/page/page_matcher_test.go`, `resources/page/pagemeta/page_frontmatter_test.go`, `resources/page/pages_related_test.go`, `resources/page/testhelpers_test.go`, `resources/resource_factories/bundler/bundler_test.go`, `resources/resource_spec_test.go`, `resources/resource_transformers/cssjs/inline_imports_test.go`, `resources/resource_transformers/js/js_integration_test.go`, `resources/testhelpers_test.go`, `resources/transform_test.go`, `tpl/collections/collections_test.go`, `tpl/collections/index_test.go`, `tpl/collections/merge_test.go`, `tpl/collections/querify_test.go`, `tpl/collections/sort_test.go`, `tpl/collections/where_test.go`, `tpl/compare/compare_test.go`, `tpl/data/data_test.go`, `tpl/data/resources_test.go`, `tpl/internal/go_templates/texttemplate/hugo_template_test.go`, `tpl/path/path_test.go`, `tpl/time/time_test.go`, `tpl/transform/unmarshal_test.go`
