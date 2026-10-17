# Repo map  <!-- generated @ aae02ca; keep under 60 lines -->

Stack: go (852), javascript (21), shell (8). Manifests: .github/workflows/image.yml, .github/workflows/stale.yml, .github/workflows/test.yml, Dockerfile, docs/go.mod, go.mod, internal/warpc/js/package.json.
Entry points: docs/_vendor/github.com/gohugoio/gohugoioTheme/assets/index.js, internal/warpc/gen/main.go, livereload/gen/main.go, main.go, scripts/fork_go_templates/main.go.
Verified commands: `go vet ./...` · `cd docs && go build ./...` · `go build ./...`.

## Modules (most central first)

| module | purpose | key files | depends on |
|---|---|---|---|
| common | shared utilities: hashing, maps/params, types, paths, loggers | hashing.go, params.go, maps.go | hugofs, config, identity, compare |
| resources | Hugo Pipes and resource handling: images, transforms, page resources | resourcetypes.go, resources.go, dates.go | common, tpl, hugofs, config +18 more |
| tpl | Go template engine wrapper and the template function registry | templatefuncsRegistry.go, template.go, template_info.go | common, resources, hugofs, config +13 more |
| hugofs | virtual filesystem layer: overlay/union mounts, glob and filename filters | glob.go, filename_filter.go, classifier.go | common, config, media |
| config | site configuration loading, defaults and config provider | commonConfig.go, defaultConfigProvider.go, configLoader.go | common, resources, hugofs, hugolib +15 more |
| hugolib | core site build: sites, pages, content tree, rendering pipeline | basefs.go, nodeshifttree.go, support.go | common, resources, tpl, hugofs +21 more |
| markup | content converters (Goldmark, AsciiDoc, etc.), render hooks, TOC | converter.go, tableofcontents.go, hooks.go | common, tpl, config, identity +3 more |
| identity | identity tracking for dependency invalidation on rebuilds | identity.go, finder.go, predicate_identity.go | common, hugofs, compare |
| deps | dependency container wiring shared services for a site build | deps.go | common, resources, tpl, hugofs +9 more |
| helpers | misc helpers: paths, URLs, content processing | path.go, general.go, content.go | common, hugofs, config, hugolib +5 more |
| commands | CLI (cobra) commands: build, server, new, etc. | server.go, hugobuilder.go, commandeer.go | common, resources, tpl, hugofs +15 more |
| compare | comparison helpers for template funcs (eq, lt, default) | compare.go, compare_strings.go | - |

## Finding things
- Ask the index first: `ctxh q find|rdeps|impact|cochange|tests|owner|module <arg>`
- Module cards: `.ctx/cards/<module-with-dashes>.md` (open only for the module you touch)
- Gotchas learned from past tasks: `.ctx/learned.md`
