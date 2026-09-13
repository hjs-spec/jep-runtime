# Release 0.2.0

Rename the executable from `jep` to `jep-runtime` so installing or uninstalling this package cannot overwrite the current API CLI. Python imports and local-runtime archive bytes remain unchanged. Upgrade from 0.1 first, then force-reinstall `jep-cli` if both previously shared an environment.
