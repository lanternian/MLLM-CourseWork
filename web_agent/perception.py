from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .models import ElementInfo


COLLECT_ELEMENTS_SCRIPT = """
() => {
  document.querySelectorAll('[data-web-agent-id]').forEach((node) => {
    node.removeAttribute('data-web-agent-id');
  });

  const selector = [
    'a', 'button', 'input', 'textarea', 'select', 'summary',
    '[role="button"]', '[role="link"]', '[role="textbox"]',
    '[contenteditable="true"]', '[onclick]'
  ].join(',');
  const nodes = Array.from(document.querySelectorAll(selector));
  const visible = nodes.filter((node) => {
    const rect = node.getBoundingClientRect();
    const style = window.getComputedStyle(node);
    const cssVisible = typeof node.checkVisibility !== 'function' ||
      node.checkVisibility({
        checkOpacity: true,
        checkVisibilityCSS: true
      });
    return rect.width > 2 && rect.height > 2 &&
      rect.bottom >= 0 && rect.right >= 0 &&
      rect.top <= window.innerHeight && rect.left <= window.innerWidth &&
      node.getClientRects().length > 0 && cssVisible &&
      style.visibility !== 'hidden' && style.display !== 'none' &&
      Number(style.opacity || 1) > 0;
  }).slice(0, 120);

  return visible.map((node, index) => {
    const rect = node.getBoundingClientRect();
    const elementId = `e${index}`;
    node.setAttribute('data-web-agent-id', elementId);
    const text = (node.innerText || node.textContent || '')
      .replace(/\\s+/g, ' ').trim().slice(0, 160);
    return {
      element_id: elementId,
      tag: node.tagName.toLowerCase(),
      role: node.getAttribute('role') || '',
      input_type: node.getAttribute('type') || '',
      text,
      aria_label: node.getAttribute('aria-label') || '',
      placeholder: node.getAttribute('placeholder') || '',
      href: node.href || '',
      value: 'value' in node ? String(node.value || '').slice(0, 160) : '',
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height
    };
  });
}
"""


def annotate_screenshot(
    screenshot_path: Path,
    output_path: Path,
    elements: list[ElementInfo],
) -> None:
    with Image.open(screenshot_path).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        for element in elements:
            left = max(0, int(element.x))
            top = max(0, int(element.y))
            right = min(image.width - 1, int(element.x + element.width))
            bottom = min(image.height - 1, int(element.y + element.height))
            if right <= left or bottom <= top:
                continue
            color = (220, 30, 30)
            draw.rectangle((left, top, right, bottom), outline=color, width=2)
            label_box = draw.textbbox((left, top), element.element_id)
            label_width = label_box[2] - label_box[0] + 6
            label_height = label_box[3] - label_box[1] + 4
            label_top = max(0, top - label_height)
            draw.rectangle(
                (left, label_top, left + label_width, label_top + label_height),
                fill=color,
            )
            draw.text((left + 3, label_top + 1), element.element_id, fill="white")
        image.save(output_path, quality=90)
