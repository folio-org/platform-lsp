# Platform-lsp

Github repository for storing Eureka files required for installation.

# Repository structure

  - ### install-applications.json
    This file contains all available applications for latest release.

  - ### management-modules.json
    List of eureka management modules applicable for latest release

  - ### backend-modules.json
    List of backend modules, which are part of applications, but not present in [Platform complete](https://github.com/folio-org/platform-complete) repository.

  - ### frontend-modules.json
    List of the eureka specific UI modules and plugins.

  - ### package.json
    An NPM [package.json](https://docs.npmjs.com/cli/v10/configuring-npm/package-json) that specifies the version of UI components.

  - ### stripes.config.js
    Template for tenant configuration file. [Info](https://github.com/folio-org/stripes-sample-platform)

  - ### stripes.modules.js
    File which contain modules, which will be included in the UI bundle.

  - ### yarn.locl
    File with all dependencies. [yarn.lock](https://classic.yarnpkg.com/lang/en/docs/yarn-lock/)


