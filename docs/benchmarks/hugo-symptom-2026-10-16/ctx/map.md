# Repo map  <!-- generated @ aae02ca61; keep under 60 lines -->

Stack: go (852), javascript (21), shell (8). Manifests: .github/workflows/image.yml, .github/workflows/stale.yml, .github/workflows/test.yml, Dockerfile, docs/go.mod, go.mod, internal/warpc/js/package.json.
Entry points: docs/_vendor/github.com/gohugoio/gohugoioTheme/assets/index.js, internal/warpc/gen/main.go, livereload/gen/main.go, main.go, scripts/fork_go_templates/main.go.
Verified commands: `go vet ./...` · `cd docs && go build ./...` · `go build ./...`.

## Modules (most central first)

| module | purpose | key files | depends on |
|---|---|---|---|
| common | Shared utilities: hashing, concurrent maps/caches, scratch, types, paths, loggers | hashing.go, cache.go, scratch.go | hugofs, config, identity, compare |
| resources | Resource model (images, transformers, pages' resources), resource cache and Resource interfaces | resourcetypes.go, resource_helpers.go, resources.go | common, tpl, hugofs, config +18 more |
| tpl | Template funcs namespaces, registry and template execution (tplimpl) | templatefuncsRegistry.go, template.go, template_info.go | common, resources, hugofs, config +13 more |
| hugofs | Layered virtual filesystem, globbing, filename filters and file classification | glob.go, filename_filter.go, classifier.go | common, config, media |
| config | Site/config loading, providers, default values, security and namespace configs | commonConfig.go, configProvider.go, namespace.go | common, resources, hugofs, hugolib +15 more |
| hugolib | Core site build: sites, pages, content/file trees, rendering pipeline | basefs.go, nodeshifttree.go, paths.go | common, resources, tpl, hugofs +21 more |
| markup | Markdown/asciidoc/org converters, highlighting, TOC and render hooks | converter.go, tableofcontents.go, hooks.go | common, tpl, config, identity +3 more |
| identity | Dependency identity graph used for incremental rebuild invalidation | finder.go, identity.go, predicate_identity.go | common, hugofs, compare |
| deps | Dependency container wiring shared services (fs, templates, logging) per site | deps.go | common, resources, tpl, hugofs +9 more |
| helpers | Misc content, path, URL and general helper functions | content.go, general.go, path.go | common, hugofs, config, hugolib +5 more |
| commands | CLI (cobra) commands: build, server, new, config; builder and file watching | hugobuilder.go, commandeer.go, server.go | common, resources, tpl, hugofs +15 more |
| compare | Comparison helpers (Eqer/ProbablyEqer) for template and value equality | compare.go, compare_strings.go | - |

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
- Module cards: `.ctx/cards/<module-with-dashes>.md` (open only for the module you touch)
- Gotchas learned from past tasks: `.ctx/learned.md`
