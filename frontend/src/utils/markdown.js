/**
 * Shared markdown renderer for report surfaces.
 *
 * Replaces the two hand-rolled regex renderers that were duplicated in
 * Step4Report.vue and Step5Interaction.vue. Adds what those could not do —
 * tables (the most useful format for a story department), links, nested
 * structures — and sanitizes the output, since report content is LLM-generated
 * and was previously injected into v-html unsanitized.
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({
  gfm: true,       // tables, strikethrough
  breaks: true,    // report prose relies on single newlines
})

export function renderMarkdown(text) {
  if (!text) return ''
  const html = marked.parse(String(text))
  return DOMPurify.sanitize(html, {
    // Reports never legitimately embed scripts/forms/media
    FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'input', 'object', 'embed'],
    FORBID_ATTR: ['onerror', 'onclick', 'onload'],
  })
}
