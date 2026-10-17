# Repo map  <!-- generated @ aae02ca61; keep under 60 lines -->

Stack: go (852), javascript (21), shell (8). Manifests: .github/workflows/image.yml, .github/workflows/stale.yml, .github/workflows/test.yml, Dockerfile, docs/go.mod, go.mod, internal/warpc/js/package.json.
Entry points: docs/_vendor/github.com/gohugoio/gohugoioTheme/assets/index.js, internal/warpc/gen/main.go, livereload/gen/main.go, main.go, scripts/fork_go_templates/main.go.
Verified commands: `go vet ./...` · `cd docs && go build ./...` · `go build ./...`.

## Modules (most central first)

| module | purpose | key files | depends on |
|---|---|---|---|
| common | Shared utilities: hashing, maps/caches, types, paths, loggers | hashing.go, cache.go, scratch.go | hugofs, config, identity, compare |
| resources | Resource abstraction (images, pages, transformers like SCSS/postcss) and resource cache | resourcetypes.go, resource_helpers.go, resources.go | common, tpl, hugofs, config +18 more |
| tpl | Go template engine wrapper and template function namespaces (tplimpl) | templatefuncsRegistry.go, template.go, template_info.go | common, resources, hugofs, config +13 more |
| hugofs | Afero-based virtual filesystems, globbing, file metadata/filters | glob.go, filename_filter.go, classifier.go | common, config, media |
| config | Site/config loading, providers and config namespaces | commonConfig.go, configProvider.go, namespace.go | common, resources, hugofs, hugolib +15 more |
| hugolib | Core site build: pages, content tree, rendering pipeline, integration tests | basefs.go, nodeshifttree.go, paths.go | common, resources, tpl, hugofs +21 more |
| markup | Content converters (goldmark, asciidoc, org), render hooks, TOC, highlighting | converter.go, tableofcontents.go, hooks.go | common, tpl, config, identity +3 more |
| identity | Dependency identities for incremental rebuild/cache invalidation | finder.go, identity.go, predicate_identity.go | common, hugofs, compare |
| deps | Dependency container wiring services shared across a site build | deps.go | common, resources, tpl, hugofs +9 more |
| helpers | Misc helpers: content, paths, URLs, general utils | content.go, general.go, path.go | common, hugofs, config, hugolib +5 more |
| commands | CLI (cobra) commands: build, server, new, etc.; main entry via main.go | hugobuilder.go, commandeer.go, server.go | common, resources, tpl, hugofs +15 more |
| compare | Comparison/equality helpers used by template funcs | compare.go, compare_strings.go | - |

## Change together (from git history)
- internal/warpc/katex.go <-> tpl/transform/transform.go (4 commits)
- hugolib/page__per_output.go <-> markup/goldmark/convert.go (4 commits, no import link)
- hugolib/page__per_output.go <-> markup/goldmark/codeblocks/render.go (4 commits, no import link)
- hugolib/page__per_output.go <-> markup/converter/hooks/hooks.go (4 commits)
- deps/deps.go <-> hugolib/integrationtest_builder.go (4 commits)

## Fragile files (fix/revert history)
- tpl/tplimpl/tplimpl_integration_test.go: Fix panic on server rebuilds when using both base templates and template.Defer
- resources/resource_transformers/tocss/scss/scss_integration_test.go: Fix Sass imports on the form index.{scss,sass}
- resources/page/pagemeta/page_frontmatter.go: Fix it so publishDate rolls up to section, taxonomy, or term pages
- releaser/releaser.go: Revert "Adjust Circleci workflow to make the Docker images build"

## Finding things
- Ask the index first: `ctxh q find|rdeps|impact|cochange|tests|owner|module <arg>`
- Gotchas learned from past tasks: `.ctx/learned.md`
