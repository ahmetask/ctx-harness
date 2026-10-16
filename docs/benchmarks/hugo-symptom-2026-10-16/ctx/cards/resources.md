---
module: resources
updated: 2026-10-16
verified: aae02ca61
anchors:
  resources/resource/resourcetypes.go: 6b5e7f74e977
  resources/resource/resource_helpers.go: 97ca7df8efe5
  resources/resource/resources.go: c1392a31f0dc
  resources/resource/dates.go: b2c4666fe69c
  resources/resource/params.go: b7b14bfe7411
  resources/images/exif/exif.go: 755b08d93212
  resources/transform.go: b5600e45b1b6
  resources/resource.go: 3193ede168c4
  resources/resource_spec.go: 46285811375c
  resources/resource_cache.go: 43c2ef5d65a0
  resources/image.go: 1fe8f34e816b
  resources/errorResource.go: f84308d65078
  resources/resource_metadata.go: 91b7c66e94eb
  resources/image_cache.go: 5b83af8953c8
  resources/post_publish.go: aceb793530fd
  resources/docs.go: 0a88812c2cce
  resources/page/page.go: d59c213f1770
  resources/page/site.go: a28734f060ea
  resources/page/permalinks.go: 39809e58e5be
  resources/page/page_nop.go: ea2a9c3a4bb0
  resources/page/pagination.go: a3b291d76419
  resources/page/page_markup.go: f5f3886ddb58
  resources/page/page_paths.go: 75e7e5e5cf85
  resources/page/pagegroup.go: 3b697ecc6b03
  resources/page/page_lazy_contentprovider.go: 1258ee674323
  resources/page/taxonomy.go: 85583292907e
  resources/page/page_marshaljson.autogen.go: cece9909f49e
  resources/page/pages_sort.go: 8d06e787a127
  resources/page/weighted.go: 2c382ea1652c
  resources/page/pages_related.go: 2c143840b387
  resources/page/page_matcher.go: 6acad378d71d
  resources/page/pages.go: 4eb23c29e8c8
  resources/page/page_outputformat.go: 23af3e51e68a
  resources/page/pages_cache.go: 267dd9a9dc3a
  resources/page/pages_sort_search.go: 65e257b05308
  resources/page/page_author.go: 1f37a6bd1166
  resources/page/pages_language_merge.go: 60d2d36802ee
  resources/page/page_data.go: 70f547633dc1
  resources/page/pages_prev_next.go: 1404dbb7042b
  resources/page/page_kinds.go: f210425b1e36
  resources/page/page_wrappers.autogen.go: 9f2389e90b59
  resources/page/zero_file.autogen.go: 9f2389e90b59
  resources/kinds/kinds.go: b7a1ed438c42
  resources/postpub/postpub.go: 3cc38cd4da2a
  resources/postpub/fields.go: e95c8f7bd6a8
  resources/internal/key.go: 9195a65e8c58
  resources/internal/resourcepaths.go: d7066b5789f1
  resources/page/page_generate/generate_page_wrappers.go: 98b4c52c5697
  resources/images/auto_orient.go: 9b55028172ea
  resources/images/image.go: 3d48874b2523
  resources/images/filters.go: 7e02e383fd35
  resources/images/color.go: 8a94093fc989
  resources/images/config.go: e67944230444
  resources/images/text.go: 1b9dac11ed89
  resources/images/image_resource.go: 0f9fe8921612
  resources/images/resampling.go: e66c8bd0eb17
  resources/images/process.go: 2be721bb1dd8
  resources/images/smartcrop.go: 53a971eb4fce
  resources/images/dither.go: 3c8b2b1141dd
  resources/images/opacity.go: a1155f52ae18
  resources/images/overlay.go: 3258c60f5e28
  resources/images/padding.go: 02b626a83608
  resources/page/pagemeta/page_frontmatter.go: 5189ac743f01
  resources/page/pagemeta/pagemeta.go: fd5c484d675c
  resources/resource_transformers/tocss/dartsass/client.go: c19675029951
  resources/resource_transformers/tocss/dartsass/transform.go: 82f98cd3188f
  resources/resource_factories/create/create.go: ee6b158a8c89
  resources/resource_factories/create/remote.go: dc99c2f699d2
  resources/resource_transformers/tocss/scss/tocss.go: 1b75d85ae431
  resources/resource_transformers/babel/babel.go: eda2241a97dd
  resources/resource_transformers/cssjs/tailwindcss.go: 3ab840318cb1
  resources/resource_transformers/cssjs/postcss.go: 68e6d1b2e226
  resources/resource_transformers/cssjs/inline_imports.go: 17d01d451876
  resources/resource_transformers/js/build.go: fe73feb301cb
  resources/resource_transformers/js/transform.go: 7f9282b2e867
  resources/resource_transformers/tocss/sass/helpers.go: 41373a824db7
  resources/resource_factories/bundler/bundler.go: 1a258dd287a9
  resources/resource_transformers/integrity/integrity.go: b46ad02e9bdd
  resources/jsconfig/jsconfig.go: b388572c8c81
  resources/resource_transformers/minifier/minify.go: 7557597aa1d7
  resources/resource_transformers/templates/execute_as_template.go: 344f3d8e8bec
  resources/resource_transformers/tocss/scss/client.go: ff367d551198
  resources/resource_transformers/tocss/scss/client_extended.go: 1e579d63fecf
  resources/images/webp/webp.go: 4e289fbb0cc3
  resources/images/webp/webp_notavailable.go: aaa5a658020c
  resources/resource_transformers/tocss/scss/client_notavailable.go: 8095129196cd
  resources/page/siteidentities/identities.go: ae3bb820d1fe
  resources/resource_transformers/htesting/testhelpers.go: 7dab4d902770
---
Owns the lazily transformed, publishable resource objects (`resourceAdapter` in `resources/transform.go`), their chains (images, JS, CSS, bundling) and the per-site resource cache.

## Invariants
- Transformations run at most once per resource object: `resourceAdapter.initTransform` guards them with `transformationsInit.Do`.
- Publishing runs at most once per resource: `resourceAdapter.publish` guards it with `publishOnce.publisherInit`. `cloneTo` allocates a fresh `publishOnce`, so a clone publishes independently.
- In publish mode, `initTransform` sets `publishOnce = nil` so the transformation writes straight to the destination instead of publishing a second copy.
- `Permalink`, `RelPermalink`, `ReadSeekCloser` and `ResourceType` call `init`, so reading any of them triggers pending transformations lazily.
- Image-only methods (`getImageOps`) panic on non-image resources; SVG gets a dedicated message pointing to `.MediaType.SubType`.
- Cached file lookups in `ResourceCache.getFromFile` hold the cache's read lock for the duration of the read.

## History
- `resources/resource_cache.go`: Fix same resource file published more than once (the reason for `publishOnce`).
- `resources/transform.go`: Fix one more resource change eviction logic issue.
- `resources/resource.go`: js: Fix js.Batch for multihost setups.
- Changes together with `hugolib/page.go`, `hugolib/page__common.go` and `hugolib/page__new.go` (3 commits each, via `resources/page/page.go`).

## Tests
`resources/transform_test.go`, `resources/image_test.go`, `resources/resource_spec_test.go`, `resources/testhelpers_test.go`, `hugolib/resource_chain_test.go`, `hugolib/rebuild_test.go`, `hugolib/pagebundler_test.go`, `tpl/resources/resources_integration_test.go`, `resources/resource_transformers/tocss/scss/scss_integration_test.go`, `resources/resource_transformers/tocss/dartsass/dartsass_integration_test.go`
