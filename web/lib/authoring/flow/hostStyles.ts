/** ADR-560 D4 — the artifact's styles, scoped into the parent-mounted editor.
 *
 * A flow document carries its whole visual identity in its own <head>: the
 * versioned kernel style element, the layout skin, and any design-system CSS
 * the projection resolved. The editor host reproduces that identity inside
 * the app page by SCOPING every rule under the host element — same emitters,
 * one more consumer, no second declaration of any style.
 *
 * `html`/`:root`/`body` selectors re-target the host (which also receives the
 * artifact root's data-* tokens, so `html[data-font="serif"] …` keeps
 * working as `.yarnnn-flow-host[data-font="serif"] …`).
 */

export const FLOW_HOST_CLASS = 'yarnnn-flow-host';

function scopeSelector(sel: string): string {
  return sel
    .split(',')
    .map((part) => {
      const s = part.trim();
      if (!s) return s;
      const rootish = /^(html|:root|body)(?![\w-])/i.exec(s);
      if (rootish) {
        return `.${FLOW_HOST_CLASS}${s.slice(rootish[1].length)}`;
      }
      return `.${FLOW_HOST_CLASS} ${s}`;
    })
    .join(', ');
}

function scopeRules(rules: CSSRuleList, out: string[]): void {
  for (const rule of Array.from(rules)) {
    if (rule instanceof CSSStyleRule) {
      out.push(`${scopeSelector(rule.selectorText)} { ${rule.style.cssText} }`);
    } else if (rule instanceof CSSMediaRule) {
      const inner: string[] = [];
      scopeRules(rule.cssRules, inner);
      out.push(`@media ${rule.conditionText} { ${inner.join('\n')} }`);
    } else if (rule instanceof CSSSupportsRule) {
      const inner: string[] = [];
      scopeRules(rule.cssRules, inner);
      out.push(`@supports ${rule.conditionText} { ${inner.join('\n')} }`);
    } else {
      // @keyframes, @font-face, @property … — global by nature; pass through.
      out.push(rule.cssText);
    }
  }
}

/** Scope one stylesheet's text under the host class. Uses CSSOM (a detached
 *  <style> in the live document) so selectors parse exactly as the browser
 *  reads them — never a regex over CSS. */
export function scopeCss(cssText: string): string {
  const probe = document.createElement('style');
  probe.media = 'not all'; // parsed, never applied
  probe.textContent = cssText;
  document.head.appendChild(probe);
  try {
    const out: string[] = [];
    if (probe.sheet) scopeRules(probe.sheet.cssRules, out);
    return out.join('\n');
  } catch {
    return cssText; // an unparseable sheet is better applied than dropped
  } finally {
    probe.remove();
  }
}

/** Extract the resolved artifact's <head> styles + root token attrs. */
export function hostStylesFrom(resolvedHtml: string): {
  css: string;
  rootAttrs: Record<string, string>;
} {
  const doc = new DOMParser().parseFromString(resolvedHtml, 'text/html');
  const css = Array.from(doc.querySelectorAll('head style'))
    .map((s) => s.textContent ?? '')
    .join('\n');
  const rootAttrs: Record<string, string> = {};
  const root = doc.documentElement;
  for (const name of root.getAttributeNames()) {
    if (name.startsWith('data-')) rootAttrs[name] = root.getAttribute(name) ?? '';
  }
  return { css: scopeCss(css), rootAttrs };
}
