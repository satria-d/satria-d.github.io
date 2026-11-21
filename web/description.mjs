const allowed = new Set(['p', 'div', 'ul', 'ol', 'li', 'strong', 'b', 'em', 'i', 'br']);
const discard = new Set(['script', 'style', 'template', 'iframe', 'object', 'embed', 'svg', 'math', 'noscript', 'form', 'input', 'button', 'select', 'textarea', 'link', 'meta', 'img', 'video', 'audio', 'source', 'picture']);

// Parse in an inert template, then build fresh nodes. Source attributes, links,
// scripts and resource-loading elements never enter the displayed document.
export function descriptionContent(value, doc = document, depth = 0) {
  const template = doc.createElement('template');
  let source = String(value ?? '');
  for (let pass = 0; pass < 3; pass++) {
    template.innerHTML = source;
    const decoded = template.content.textContent;
    if (template.content.childElementCount || decoded === source
      || !/(?:<\/?[a-z]|&(?:lt|#0*60|#x0*3c);)/i.test(decoded)) break;
    source = decoded;
  }
  const result = doc.createDocumentFragment();
  const copy = (node, parent) => {
    if (node.nodeType === 3) {
      if (depth < 2 && /(?:<\/?(?:strong|p|div|ul|ol|li|br|b|em|i|h[1-6]|script|style)\b|&(?:lt|#0*60|#x0*3c);)/i.test(node.data)) {
        parent.append(descriptionContent(node.data, doc, depth + 1));
      } else parent.append(doc.createTextNode(node.data));
      return;
    }
    if (node.nodeType !== 1) return;
    const tag = node.localName.toLowerCase();
    if (discard.has(tag)) return;
    const heading = /^h[1-6]$/.test(tag);
    const target = allowed.has(tag) || heading ? doc.createElement(heading ? 'h4' : tag) : parent;
    if (target !== parent) parent.append(target);
    for (const child of node.childNodes) copy(child, target);
  };
  for (const node of template.content.childNodes) copy(node, result);
  return result;
}
