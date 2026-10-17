---
module: config
updated: 2026-10-15
verified: aae02ca
anchors:
  config/commonConfig.go: dfe7f04ec5f1
  config/defaultConfigProvider.go: fa1e8095bd59
  config/configLoader.go: 68a4da5e4381
  config/env.go: ccdd12c4c48f
  config/configProvider.go: e48ce6e81864
  config/namespace.go: eefc8eb0b1fb
  config/security/securityConfig.go: 00a21a11a2ea
  config/security/whitelist.go: 795ce38a855b
  config/allconfig/configlanguage.go: ed29b7e944bd
  config/allconfig/allconfig.go: af11a715cab9
  config/allconfig/load.go: 6e20e759bc6f
  config/allconfig/alldecoders.go: 932545200be1
  config/allconfig/docshelper.go: 385f204a2c67
  config/privacy/privacyConfig.go: 21b830da8a40
  config/services/servicesConfig.go: 266625599588
  config/testconfig/testconfig.go: 8d890f2bd5db
---
Owns loading, merging and typed decoding of Hugo site configuration: the `Provider` store, config file discovery, legacy key aliasing and the per-namespace config structs.

## Invariants
- Keys are case-insensitive: `defaultConfigProvider.Get`, `Set` and `IsSet` lowercase the key before lookup.
- `defaultConfigProvider.Set` merges into an existing nested `maps.Params` via `maps.SetParams` instead of replacing it; a non-map value replaces the key.
- `defaultConfigProvider.SetDefaults` only writes root keys that are absent.
- `LoadConfigFromDir` merges `_default` first and then the environment directory, so the environment wins; files named other than `hugo`/`config` are keyed by their name (`params.*`, `menus.*`) and `*.<lang>` files are placed under `languages.<lang>`.
- `IsValidConfigFilename` accepts only `toml`, `yaml`, `yml` and `json` extensions.
- `RenameKeys` (via `keyAliases`) rewrites the legacy `menu` key to `menus`, including under `languages/*`, on every load path (`readConfig`, `loadConfigFromFile`, `LoadConfigFromDir`).
- `DecodeBuildConfig` normalises `build.useResourceCache` to `never`, `always` or `fallback`; any other value becomes `fallback`. `BuildConfig.UseResourceCache` treats `fallback` as true only for feature-not-available errors.
- `DecodeNamespace` computes `ConfigNamespace.SourceHash` from the raw input before defaults are applied, so adding new defaulted options does not change the hash.

## Entry point
`config.FromFile` and `config.LoadConfigFromDir` in `config/configLoader.go`; the store is `config.NewFrom` in `config/defaultConfigProvider.go`.

## Tests
`config/allconfig/allconfig_integration_test.go`, `config/security/securityConfig_test.go`, `config/privacy/privacyConfig_test.go`, `config/services/servicesConfig_test.go`, `modules/config_test.go`, `hugolib/config_test.go`, `markup/markup_config/config_test.go`, `minifiers/config_test.go`, `deploy/deployconfig/deployConfig_test.go`, `hugolib/site_test.go`.
