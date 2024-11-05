const modules = require("./stripes.modules");

module.exports = {
  okapi: {
    // application gateway
    'url': '${kongUrl}',
    'uiUrl': '${tenantUrl}',
    // authentication details: url, secret, clientId
    'authnUrl': '${keycloakUrl}',
  },
  config: {
    isEureka: true,
    hasAllPerms: ${hasAllPerms},
    logCategories: 'core,path,action,xhr',
    useSecureTokens: true,
    idleSessionWarningSeconds: 60,
    logPrefix: '--',
    maxUnpagedResourceCount: 2000,
    showPerms: false,
    aboutInstallDate: ${aboutInstallDate},
    aboutInstallMessage: ${aboutInstallMsg},
    tenantOptions: ${tenantOptions}
  },
  modules, // Populated by stripes.modules.js
  branding: {
    logo: {
      src: './logo.png',
      alt: '${tenant_name}'
    },
    favicon: {
      src: './favicon.png'
    },
  }
};
