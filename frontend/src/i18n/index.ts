import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import ar from './ar'
import en from './en'
import fr from './fr'

export type AppLang = 'en' | 'fr' | 'ar'

function savedLang(): AppLang {
  try {
    const raw = localStorage.getItem('vva-settings')
    const lang = raw ? (JSON.parse(raw) as { state?: { lang?: string } }).state?.lang : undefined
    return lang === 'fr' || lang === 'ar' ? lang : 'en'
  } catch {
    return 'en'
  }
}

export function applyDocumentLang(lang: AppLang, title?: string): void {
  document.documentElement.lang = lang
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
  if (title) document.title = title
}

const initial = savedLang()

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, fr: { translation: fr }, ar: { translation: ar } },
  lng: initial,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

applyDocumentLang(initial)

export default i18n
