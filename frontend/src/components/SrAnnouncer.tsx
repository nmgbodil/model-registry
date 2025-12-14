/**
 * Screen Reader Announcer Component
 * Provides a live region for dynamic announcements to screen readers
 */
export function SrAnnouncer() {
  return (
    <div
      id="sr-announcer"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    />
  );
}
