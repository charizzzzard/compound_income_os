const env = import.meta.env

export const siteConfig = {
  productName: 'Compound Income OS',
  tagline: 'A calmer way to run a long-term portfolio.',
  ctas: {
    sampleReport: {
      label: 'Read a sample monthly report',
      href: env.VITE_SAMPLE_REPORT_URL || null,
      fallbackAnchor: '/workflow#sample-report',
      pendingPill: 'Sample available on request - pending',
    },
    earlyAccess: {
      label: 'Request private preview',
      headerLabel: 'Get early access',
      shortLabel: 'Get access',
      href: env.VITE_EARLY_ACCESS_URL || null,
      pendingPill: 'Private preview - request pending',
    },
    githubAccess: {
      label: 'View on GitHub',
      href: env.VITE_GITHUB_URL || null,
      fallbackAnchor: '#workflow',
      pendingTooltip: 'Repository link pending',
    },
    setupService: {
      label: 'Request setup',
      href: env.VITE_SETUP_SERVICE_URL || null,
      pendingPill: 'Private preview - request pending',
    },
    workflowAnchor: {
      label: 'See the workflow',
      href: '/workflow',
    },
  },
  routes: {
    home: '/',
    workflow: '/workflow',
    evidence: '/evidence',
    portfolio: '/portfolio',
    dashboard: '/dashboard',
    manifestoPending: '#manifesto-teaser',
  },
  demoReadinessPayloadPath: '/demo/readiness_payload.sample.json',
  links: {
    github: env.VITE_GITHUB_URL || null,
    sponsors: env.VITE_SPONSORS_URL || null,
    privacy: env.VITE_PRIVACY_URL || null,
    imprint: env.VITE_IMPRINT_URL || null,
  },
  disclaimerShort:
    'Compound Income OS is a local research-support tool. It is not financial, tax, or legal guidance, never connects to a brokerage, and never places transactions. All values shown on this page are synthetic demo values.',
  disclaimer:
    'Compound Income OS is a local research-support tool. It does not provide financial, tax, or legal guidance, does not guarantee any return, and does not connect to brokerages. All decisions, risks, and outcomes remain solely with the user. Past data does not predict future results. Illustrative figures shown throughout this page are synthetic demo values for design purposes only.',
}
