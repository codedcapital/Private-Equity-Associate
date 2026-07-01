// Design system tokens — single source of truth for the new Overview page
// Phase 1 & 2 of the frontend roadmap

export const colors = {
  background: '#0a0a0a',
  surface: '#141414',
  surfaceHover: '#1a1a1a',
  border: '#1f1f1f',
  borderHover: '#2a2a2a',
  textPrimary: '#e5e5e5',
  textSecondary: '#737373',
  textMuted: '#525252',
  accent: '#c7a84b',
  accentMuted: '#c7a84b33',
  positive: '#4ade80b3',
  warning: '#fbbf24b3',
  negative: '#f87171b3',
  unknown: '#525252',
} as const;

export const typography = {
  mono: '"JetBrains Mono", "SF Mono", monospace',
  sans: '"Inter", "Geist", system-ui, sans-serif',
  serif: '"Tiempos Text", "Chronicle", "Georgia", serif',
} as const;

export const spacing = {
  sectionGap: '48px',
  contentGap: '24px',
  textGap: '12px',
  padding: '32px',
} as const;

// Derived semantic colors for evidence status chips
export const evidenceStatusColors: Record<string, { bg: string; text: string; border: string }> = {
  VERIFIED: { bg: 'rgba(74,222,128,0.12)', text: '#4ade80b3', border: 'rgba(74,222,128,0.25)' },
  NEEDS_VALIDATION: { bg: 'rgba(251,191,36,0.12)', text: '#fbbf24b3', border: 'rgba(251,191,36,0.25)' },
  CONFLICTING: { bg: 'rgba(248,113,113,0.12)', text: '#f87171b3', border: 'rgba(248,113,113,0.25)' },
  UNKNOWN: { bg: 'rgba(82,82,82,0.12)', text: '#525252', border: 'rgba(82,82,82,0.25)' },
};

// Recommendation colors
export const recommendationColors: Record<string, { bg: string; text: string; border: string }> = {
  PROCEED: { bg: 'rgba(74,222,128,0.12)', text: '#4ade80b3', border: 'rgba(74,222,128,0.25)' },
  CONDITIONAL: { bg: 'rgba(251,191,36,0.12)', text: '#fbbf24b3', border: 'rgba(251,191,36,0.25)' },
  DECLINE: { bg: 'rgba(248,113,113,0.12)', text: '#f87171b3', border: 'rgba(248,113,113,0.25)' },
  HOLD: { bg: 'rgba(82,82,82,0.12)', text: '#525252', border: 'rgba(82,82,82,0.25)' },
};
