---
module: tpl
updated: 2026-10-15
verified: aae02ca
anchors:
  tpl/internal/templatefuncsRegistry.go: a5a9cdc1d312
  tpl/template.go: c53dc538aff2
  tpl/template_info.go: 5be8b49c5e18
  tpl/internal/go_templates/texttemplate/parse/node.go: cc937e1ef950
  tpl/internal/go_templates/texttemplate/parse/parse.go: 6e68170e2ad0
  tpl/internal/go_templates/texttemplate/parse/lex.go: ed5f3ad78d09
  tpl/internal/go_templates/cfg/cfg.go: b7a034ec5202
  tpl/internal/go_templates/texttemplate/exec.go: fcc611264e57
  tpl/internal/go_templates/texttemplate/funcs.go: 3261d6eac005
  tpl/internal/go_templates/texttemplate/template.go: 82e3765068c9
  tpl/internal/go_templates/texttemplate/hugo_template.go: 70f1e581f823
  tpl/internal/go_templates/texttemplate/helper.go: 714a9db430ce
  tpl/internal/go_templates/texttemplate/option.go: 56ca735e27f8
  tpl/internal/go_templates/texttemplate/doc.go: 78657a38137b
  tpl/internal/go_templates/fmtsort/sort.go: c4361cfafc1b
  tpl/css/css.go: 7d410b37f0f4
  tpl/js/js.go: 6514091b9909
  tpl/js/init.go: 8f69e16ef1ef
  tpl/internal/go_templates/htmltemplate/escape.go: acc05c91e7d2
  tpl/internal/go_templates/htmltemplate/template.go: c9a7b2dcf33e
  tpl/internal/go_templates/htmltemplate/transition.go: c230e81633f3
  tpl/compare/compare.go: 35c52d0e8e66
  tpl/internal/go_templates/htmltemplate/context.go: c3c84b4a711c
  tpl/internal/go_templates/htmltemplate/url.go: 3f9884d304c9
  tpl/internal/go_templates/htmltemplate/css.go: e67e2050e6c4
  tpl/internal/go_templates/htmltemplate/js.go: 532a45a2a031
  tpl/internal/go_templates/htmltemplate/html.go: 2adccfbb43a3
  tpl/internal/go_templates/htmltemplate/content.go: 5ad27567ce96
  tpl/internal/go_templates/htmltemplate/error.go: 8684516a3bf6
  tpl/internal/go_templates/htmltemplate/hugo_template.go: e1a71edde1ca
  tpl/compare/init.go: d663530ca7bd
  tpl/internal/go_templates/htmltemplate/attr.go: 5c9ce13c4e70
  tpl/internal/go_templates/htmltemplate/doc.go: 22f2b97cdf47
  tpl/tplimpl/template.go: 0b212298dca7
  tpl/math/math.go: 9dbcc020eee2
  tpl/internal/go_templates/testenv/testenv.go: d39c8a14bfc5
  tpl/strings/strings.go: 32ea2e29035d
  tpl/collections/collections.go: f7f3bf7b8c75
  tpl/resources/resources.go: 6a66f6eefac1
  tpl/tplimpl/template_ast_transformers.go: 398944d638b6
  tpl/partials/partials.go: 8d55bec92763
  tpl/debug/debug.go: 2720d0abce9b
  tpl/transform/transform.go: 0f815cc89682
  tpl/urls/urls.go: 646573f7dd8f
  tpl/fmt/fmt.go: 4dcd432c9028
  tpl/collections/where.go: 93df3127bae5
  tpl/lang/lang.go: 8304ec69132c
  tpl/tplimpl/shortcodes.go: ce85849db809
  tpl/collections/reflect_helpers.go: ce9f04cd1ef6
  tpl/data/data.go: ebf86f78c254
  tpl/path/path.go: 54b3c7bd5939
  tpl/tplimpl/template_funcs.go: 69d44f2a1057
  tpl/os/os.go: 8060a905b316
  tpl/safe/safe.go: edc89385a7f4
  tpl/collections/sort.go: 985e4b9c80c6
  tpl/crypto/crypto.go: 670a82d7d551
  tpl/diagrams/goat.go: 02bb3d816651
  tpl/time/time.go: 7719ce13fa63
  tpl/tplimpl/template_errors.go: 2009871211e4
  tpl/cast/cast.go: 7c4af3973032
  tpl/encoding/encoding.go: 1565ec9a44aa
  tpl/internal/go_templates/testenv/exec.go: 13da8767f175
  tpl/templates/templates.go: 584e7d79b0fc
  tpl/collections/apply.go: 59703fcc30b3
  tpl/hash/hash.go: f2ea7be51541
  tpl/inflect/inflect.go: b75120479d11
  tpl/openapi/openapi3/openapi3.go: bbb94645006d
  tpl/collections/index.go: 1d72660aa7f9
  tpl/collections/merge.go: 2a604ace5029
  tpl/collections/querify.go: c0c7da39ccf8
  tpl/data/resources.go: 74cd4ca0b7d5
  tpl/images/images.go: b48f76c377c8
  tpl/reflect/reflect.go: 28ab1a6358da
  tpl/strings/regexp.go: c394e4d860fc
  tpl/tplimpl/templateProvider.go: 8704ab4859d1
  tpl/transform/remarshal.go: eb0b6f4687e6
  tpl/transform/unmarshal.go: f295df0b991c
  tpl/cast/docshelper.go: c0291961af97
  tpl/internal/go_templates/testenv/testenv_windows.go: f0e0c0976b8b
  tpl/internal/resourcehelpers/helpers.go: 598040acb6ba
  tpl/strings/truncate.go: 997114d5f77b
  tpl/cast/init.go: 5157d46ab8c8
  tpl/collections/append.go: c7c1d2abda00
  tpl/collections/complement.go: e831386a5fd6
  tpl/collections/init.go: 23d8fa04b5a9
  tpl/collections/symdiff.go: b72a7c58f736
  tpl/crypto/init.go: 9c2d9e212d6e
  tpl/data/init.go: eb4e2d7f59fd
  tpl/debug/init.go: 6954ea5a96eb
  tpl/diagrams/diagrams.go: 45afc7cabc1f
  tpl/diagrams/init.go: fe3aa3f4745b
  tpl/encoding/init.go: d1456cebd20b
  tpl/fmt/init.go: 012bebc80bd6
  tpl/hugo/init.go: 000f73110981
  tpl/images/init.go: efad65308e7a
  tpl/inflect/init.go: 02405e9f91b4
  tpl/internal/go_templates/testenv/noopt.go: 549b90a3edf4
  tpl/internal/go_templates/testenv/opt.go: d51d7dfcfdc3
  tpl/internal/go_templates/testenv/testenv_notunix.go: 59fcb9ed6c52
  tpl/internal/go_templates/testenv/testenv_notwin.go: 227b629d8a4d
  tpl/internal/go_templates/testenv/testenv_unix.go: c5943a4fdb61
  tpl/lang/init.go: dcd80fbf7132
  tpl/math/init.go: 64bd26dc4cba
  tpl/math/round.go: 987257774e91
  tpl/openapi/openapi3/init.go: 05afee0b33df
  tpl/os/init.go: 3849370928f4
  tpl/page/init.go: ad67da73a9d1
  tpl/partials/init.go: cac4f106052f
  tpl/path/init.go: 75c9773e4440
  tpl/reflect/init.go: 4098065a3f88
  tpl/resources/init.go: 8e4ca63df88d
  tpl/safe/init.go: 744ea248668f
  tpl/site/init.go: df0d2b470f61
  tpl/strings/init.go: 52e45d64e330
  tpl/templates/init.go: ab045f27ca0f
  tpl/time/init.go: 24a1ca7fb495
  tpl/transform/init.go: bf9924fbf7ac
  tpl/urls/init.go: a4601d6f8aa0
  tpl/tplimpl/templateFuncster.go: 9494abb53287
---
Template parsing, lookup, execution and the template function namespaces (`tpl/tplimpl` wiring, `tpl/internal` registry).

## Invariants
- Template names are unique per namespace: `templateNamespace.addDeferredTemplate` returns early when the name is already registered.
- Text and HTML templates never resolve each other: `templateNamespace.newTemplateLookup` returns nil when `isText()` differs.
- `templateNamespace.parse`, `addDeferredTemplate` and `Lookup` hold `templateNamespace.mu` for the map access; `templateExec.ExecuteWithContext` takes the read lock on `types.RLocker` templates.
- Execution errors get file context from `templateExec.addFileContext`, using the owner template for deferred templates (`templateState.owner`).
- Usage tracking is opt-in: `templateExec.UnusedTemplates` returns nil unless the tracker is set.
- `TemplateFuncsNamespace.AddMethodMapping` panics on an empty example or alias at registration, and rewrites `§§` to a backtick in examples.
- `textTemplateWrapperWithLock.LookupVariant` and `LookupVariants` panic ("not supported"); callers must not request variants on text templates.
- `templateHandler.extractPartials` registers inline `partials/` templates under `templateHandler.main.mu`.

## Tests
`hugolib/page_test.go`, `langs/i18n/i18n_test.go`, `tpl/collections/apply_test.go`, `tpl/internal/go_templates/fmtsort/sort_test.go`, `tpl/internal/go_templates/htmltemplate/clone_test.go`, `tpl/internal/go_templates/htmltemplate/escape_test.go`, `tpl/internal/go_templates/htmltemplate/example_test.go`, `tpl/internal/go_templates/htmltemplate/examplefiles_test.go`, `tpl/internal/go_templates/htmltemplate/exec_test.go`, `tpl/internal/go_templates/htmltemplate/multi_test.go`, `tpl/internal/go_templates/testenv/testenv_test.go`, `tpl/internal/go_templates/texttemplate/link_test.go`, `tpl/internal/go_templates/texttemplate/multi_test.go`, `tpl/os/os_test.go`, `tpl/tplimpl/template_ast_transformers_test.go`, `tpl/tplimpl/template_funcs_test.go`, `tpl/tplimpl/tplimpl_integration_test.go`, `tpl/transform/remarshal_test.go`, `tpl/transform/transform_test.go`, `tpl/transform/unmarshal_test.go`
