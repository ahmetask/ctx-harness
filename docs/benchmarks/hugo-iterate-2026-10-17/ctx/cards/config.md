---
module: config
updated: 2026-10-16
verified: aae02ca61
anchors:
  config/commonConfig.go: dfe7f04ec5f1
  config/configProvider.go: e48ce6e81864
  config/namespace.go: eefc8eb0b1fb
  config/defaultConfigProvider.go: fa1e8095bd59
  config/configLoader.go: 68a4da5e4381
  config/env.go: ccdd12c4c48f
  config/security/securityConfig.go: 00a21a11a2ea
  config/security/whitelist.go: 795ce38a855b
  config/allconfig/allconfig.go: af11a715cab9
  config/allconfig/alldecoders.go: 932545200be1
  config/allconfig/configlanguage.go: ed29b7e944bd
  config/allconfig/load.go: 6e20e759bc6f
  config/allconfig/docshelper.go: 385f204a2c67
  config/privacy/privacyConfig.go: 21b830da8a40
  config/services/servicesConfig.go: 266625599588
  config/testconfig/testconfig.go: 8d890f2bd5db
---
Owns loading and decoding of the site configuration (`Provider`, `AllProvider`) and the typed config sections (security, privacy, services, markup/build/server decoders).

## Invariants
- `LoadConfig` (`config/allconfig/load.go`) defers `configs.transientErr()` until after module config files are merged; the errors it carries (e.g. `unknown output format %q for kind %q` in `allconfig.go`) only surface once merging completes.
- `LoadConfig` re-reads the config from scratch when module config files were merged (`l.ModulesConfigFiles`), so module-supplied keys are part of the final `Configs`.
- `applyDefaultConfig` (`load.go`) sets defaults via `SetDefaults`, so user-provided keys always win over the default table.
- `DecodeNamespace` (`namespace.go`) hashes the source before defaults are applied; `SourceHash` is therefore stable when new options are added.
- `applyConfigAliases` (`load.go`) maps legacy keys onto new ones: `indexes`→`taxonomies`, `logI18nWarnings`→`printI18nWarnings`, `logPathWarnings`→`printPathWarnings`, `ignoreErrors`→`ignoreLogs`.
- OS env overrides with the `HUGO` prefix are applied by `applyOsEnvOverrides`; `envStringToVal` splits `disablekinds`/`disablelanguages` on commas, or on whitespace when no comma is present.
- `HUGO_NUMWORKERMULTIPLIER` and `HUGO_MEMORYLIMIT` (GiB) are read directly with `os.Getenv` in `config/env.go`, not through the provider.
- `DecodeConfig` (`config/security/securityConfig.go`) starts from `DefaultConfig`; the `Check*` methods (`CheckAllowedExec`, `CheckAllowedGetEnv`, `CheckAllowedHTTPURL`, `CheckAllowedHTTPMethod`) return `*AccessDeniedError`, which `IsAccessDenied` detects.
- `IsValidConfigFilename` (`configLoader.go`) gates config files by extension; a missing config yields the `ErrNoConfigFile` sentinel in `load.go`.

## History
- `config/allconfig/allconfig.go` and `alldecoders.go` change together (3 commits each, with `allconfig_integration_test.go`).
- `config/commonConfig.go` co-changes with `resources/page/pagination.go` (2 commits).
- `config/allconfig/load.go` co-changes with `commands/hugobuilder.go` (2 commits).
- `config: Throw error when output format is not defined` (eb1dbe070) added the unknown-output-format check now in `allconfig.go`.

## Entry point and tests
Entry point: `allconfig.LoadConfig(ConfigSourceDescriptor)` in `config/allconfig/load.go`.
Tests: `config/allconfig/allconfig_integration_test.go`, `config/security/securityConfig_test.go`, `config/privacy/privacyConfig_test.go`, `config/services/servicesConfig_test.go`, `hugolib/config_test.go`, `modules/config_test.go`.
