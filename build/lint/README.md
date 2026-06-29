# YAML and Lua lint entrypoint

This directory contains the lightweight lint entrypoint used by local commands.

## Dependencies

Current stage:

- `yamllint`
- `luacheck`

Example install on macOS:

```bash
brew install yamllint luacheck
```

## Usage

From the repository root:

```bash
bash build/lint/run.sh yaml-lint
bash build/lint/run.sh lua-lint
bash build/lint/run.sh all
make -C build lint-yaml
make -C build lint-lua
make -C build lint
make -C build smoke
```

## Notes

- The current implementation enables YAML linting and Lua linting.
- The first stage checks `src/schema/*.schema.yaml`, `src/config/*.yaml`,
  `src/no_lua_schema/*.yaml`, and `src/recipes/*.yaml` files.
- `*.schema.yaml` files are preprocessed before linting so the `pin_cand_filter`
  tab-separated list does not break generic YAML parsing.
- `lua-lint` runs `luacheck` with a repository-local configuration derived from
  the librime-lua globals currently used by this repository.
- `lua-format-check` is reserved for a later stage.
- `smoke` mirrors the current CI smoke invocation and runs
  `bash ./build/smoke/run.sh med_ice` through Make.
- GitHub Actions are intentionally not changed in this stage.
