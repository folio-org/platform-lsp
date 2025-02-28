# Platform-lsp

## TODO purpose of repo
Equivalent of platform complete for the Eureka.
## branching strategy
## taggins strategy
## brief examples

Github repository for storing Eureka files required for installation.

# Repository structure

  - ### install-applications.json
    This file contains specific versions of appications for specific release.

  - ### management-modules.json
    List of eureka management modules, sidecars that are applicable for specific release

  - ### backend-modules.json
    List of backend modules, which are part of applications, but not present in [Platform complete](https://github.com/folio-org/platform-complete) repository. Safe to ignore.

  - ### frontend-modules.json
    List of the eureka specific UI modules and plugins. Safe to ignore.

  - ### package.json
    An NPM [package.json](https://docs.npmjs.com/cli/v10/configuring-npm/package-json) that specifies the version of UI components.

  - ### stripes.config.js
    Template for tenant configuration file. [Info](https://github.com/folio-org/stripes-sample-platform)

  - ### stripes.modules.js
    File which contain modules, which will be included in the UI bundle.

  - ### yarn.lock
    File with UI dependencies. [yarn.lock](https://classic.yarnpkg.com/lang/en/docs/yarn-lock/)
    
