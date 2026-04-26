const env = import.meta.env

export const siteConfig = {
  productName: 'Compound Income OS',
  tagline: 'A local operating system for long-term investing.',
  ctas: {
    earlyAccess: {
      label: 'Join Early Access',
      shortLabel: 'Join',
      href: env.VITE_EARLY_ACCESS_URL || 'mailto:early-access@example.invalid?subject=Compound%20Income%20OS%20Early%20Access',
    },
    githubAccess: {
      label: 'Request GitHub Access',
      href: env.VITE_GITHUB_ACCESS_URL || 'mailto:early-access@example.invalid?subject=Compound%20Income%20OS%20GitHub%20Access',
    },
    setupService: {
      label: 'Request Setup Service',
      href: env.VITE_SETUP_SERVICE_URL || 'mailto:early-access@example.invalid?subject=Compound%20Income%20OS%20Setup%20Service',
    },
  },
  links: {
    github: env.VITE_GITHUB_URL || 'TBD',
    sponsors: env.VITE_SPONSORS_URL || 'TBD',
    privacy: env.VITE_PRIVACY_URL || 'TBD',
    imprint: env.VITE_IMPRINT_URL || 'TBD',
  },
  disclaimer:
    'Compound Income OS is a research and decision-support tool. It does not provide investment, tax, or legal advice, does not guarantee any return, and does not execute orders or connect to brokerages. All decisions, risks, and outcomes remain solely with the user. Past data does not predict future results. Illustrative figures shown throughout this page are synthetic demo values for design purposes only.',
}
