/* Content stays visible without JavaScript or when reduced motion is preferred. */
(() => {
  "use strict";

  if (!("IntersectionObserver" in window)) return;
  const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (motionPreference.matches) return;

  const items = document.querySelectorAll("[data-reveal]");
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.remove("reveal-pending");
      observer.unobserve(entry.target);
    }
  }, { threshold: 0, rootMargin: "0px 0px -24px 0px" });

  for (const item of items) {
    // Preserve content already on screen, including restored scroll positions.
    const rect = item.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) continue;
    item.classList.add("reveal-pending");
    observer.observe(item);
  }

  // Keyboard navigation should never focus an invisible paper link.
  document.addEventListener("focusin", event => {
    const item = event.target.closest(".reveal-pending");
    if (!item) return;
    item.classList.remove("reveal-pending");
    observer.unobserve(item);
  });

  motionPreference.addEventListener("change", event => {
    if (!event.matches) return;
    observer.disconnect();
    for (const item of items) item.classList.remove("reveal-pending");
  });
})();
