---
module: tpl
updated: 2026-10-16
verified: aae02ca61
anchors:
  tpl/template.go: c53dc538aff2
  tpl/template_info.go: 5be8b49c5e18
  tpl/internal/templatefuncsRegistry.go: a5a9cdc1d312
  tpl/tplimpl/template.go: 0b212298dca7
  tpl/tplimpl/template_funcs.go: 69d44f2a1057
---
Template interfaces (`tpl`) and their implementation (`tpl/tplimpl`): lookup, base/overlay parsing, execution, and the template function namespace registry.

## Invariants
- `ParseInfo.IsZero` is true when `Config.Version == 0`; `DefaultParseInfo` sets `Version` to `TemplateVersion` (`tpl/template_info.go`).
- A base template is parsed only when its `templateInfo.IsZero()` is false, for both text and html in `applyBaseTemplate` (`tpl/tplimpl/template.go`).
- The usage tracker records the base template info only when it is non-zero, in `templateExec.ExecuteWithContext` (`tpl/tplimpl/template.go`).
- Duplicate namespace names and method aliases panic when the func map is built (`tpl/tplimpl/template_funcs.go`).
- `TemplateFuncsNamespace.AddMethodMapping` panics on empty examples or aliases (`tpl/internal/templatefuncsRegistry.go`).

## History
- `tpl/template.go`: Fix server edits of resources included in shortcode/hooks
- `tpl/template.go`: hugolib/commands: Fix stuck server error issues
- Changes together with: `internal/warpc/katex.go`, `internal/warpc/js/renderkatex.bundle.js`, `internal/warpc/js/common.js` (via `tpl/transform/transform.go`)

## Entry point
`tpl/tplimpl/template.go` (`templateExec.ExecuteWithContext`, `templateHandler.applyBaseTemplate`).

## Tests
`tpl/tplimpl/template_funcs_test.go`, `tpl/tplimpl/template_ast_transformers_test.go`, `tpl/tplimpl/tplimpl_integration_test.go`, `hugolib/page_test.go`
- Registering a func namespace: each `tpl/<ns>/init.go` `init()` calls `internal.AddTemplateFuncsNamespace` (tpl/internal/templatefuncsRegistry.go); it is only active if `tpl/tplimpl/template_funcs.go` blank-imports the package; `createFuncMap` panics on duplicate names.
