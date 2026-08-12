/** ADR-560 — executable stripping for HTML the model carries OPAQUELY.
 *
 * The flow editor mounts in the PARENT document (ADR-560 D4), so any markup
 * the schema round-trips verbatim (preservation islands, figure leads) must be
 * inert before it is ever attached to a live DOM. Same contract as the
 * projection's `stripExecutable` + `sanitizeInner` (ADR-446 D2): drop
 * script/iframe/object/embed, `on*` handlers, and `javascript:` URLs.
 *
 * This is NOT the paste policy — the schema is the paste policy (ADR-560 D2):
 * unknown structure parses to the preservation node, and executable content
 * cannot enter the model because it is stripped here at capture time.
 */

const EXECUTABLE_SEL = "script, iframe, object, embed, link[rel='import']";

/** Strip executable content from a detached element, in place. */
export function stripExecutableEl(el: Element): void {
  for (const bad of Array.from(el.querySelectorAll(EXECUTABLE_SEL))) bad.remove();
  const all = [el, ...Array.from(el.querySelectorAll('*'))];
  for (const node of all) {
    for (const name of node.getAttributeNames()) {
      if (name.toLowerCase().startsWith('on')) node.removeAttribute(name);
      else if (
        (name === 'href' || name === 'src' || name === 'xlink:href') &&
        /^\s*javascript:/i.test(node.getAttribute(name) ?? '')
      ) {
        node.removeAttribute(name);
      }
    }
  }
}

/** Capture an element's outerHTML with executables stripped — the ONE way
 *  opaque markup enters a model attribute. */
export function captureInertHtml(el: Element): string {
  const clone = el.cloneNode(true) as Element;
  stripExecutableEl(clone);
  return clone.outerHTML;
}
