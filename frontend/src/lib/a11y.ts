/**
 * Accessibility utilities for WCAG 2.1 AA compliance
 */

/**
 * Announces a message to screen readers using a live region
 * @param message - The message to announce
 * @param priority - 'polite' (default) or 'assertive'
 */
export function announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
  const announcer = document.getElementById('sr-announcer');
  if (announcer) {
    announcer.setAttribute('aria-live', priority);
    announcer.textContent = '';
    // Use setTimeout to ensure the change is picked up by screen readers
    setTimeout(() => {
      announcer.textContent = message;
    }, 100);
  }
}

/**
 * Focus an element programmatically with scroll behavior
 * @param element - The element to focus
 * @param scrollIntoView - Whether to scroll the element into view
 */
export function focusElement(element: HTMLElement | null, scrollIntoView = true) {
  if (element) {
    if (scrollIntoView) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    element.focus({ preventScroll: !scrollIntoView });
  }
}

/**
 * Generates unique IDs for accessibility attributes
 * @param prefix - Prefix for the ID
 * @returns A unique ID string
 */
let idCounter = 0;
export function generateA11yId(prefix: string): string {
  return `${prefix}-${++idCounter}`;
}
