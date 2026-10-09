const system = window.matchMedia('(prefers-color-scheme: dark)')
let preference = 'light'
try { preference = localStorage.getItem('task-copilot-theme') || 'light' } catch {}

export function applyTheme(value) {
  preference = ['light', 'dark', 'system'].includes(value) ? value : 'light'
  document.documentElement.dataset.theme = preference === 'system' ? (system.matches ? 'dark' : 'light') : preference
  try { localStorage.setItem('task-copilot-theme', preference) } catch {}
}
system.addEventListener('change', () => { if (preference === 'system') applyTheme(preference) })
applyTheme(preference)
