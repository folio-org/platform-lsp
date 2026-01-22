const apps = require("./stripes.modules");
const extra = require("./stripes.extra");
const { merge } = require('lodash');

module.exports = {
  okapi: {
    'url': '${kongUrl}',
    'uiUrl': '${tenantUrl}',
    'authnUrl': '${keycloakUrl}',
  },
  config: {
    isEureka: true,
    hasAllPerms: ${hasAllPerms},
    idleSessionWarningSeconds: 60,
    tenantOptions: ${tenantOptions},
    aboutInstallDate: ${aboutInstallDate},
    aboutInstallMessage: ${aboutInstallMsg},
    isSingleTenant: ${isSingleTenant},
    enableEcsRequests: ${enableEcsRequests},
    rtr: {
      idleSessionTTL: '1h',
      idleModalTTL: '30s',
    },
    logCategories: 'core,path,action,xhr',
    logPrefix: '--',
    maxUnpagedResourceCount: 2000,
    showPerms: false,
    preserveConsole: true,
    useSecureTokens: true,
  },
  modules: merge({}, apps, plugins, extra),
  branding: {
    logo: {
      src: './tenant-assets/opentown-libraries-logo.png',
      alt: 'Opentown Libraries',
    },
    favicon: {
      src: './tenant-assets/folio-favicon.png',
    },
  }
};
