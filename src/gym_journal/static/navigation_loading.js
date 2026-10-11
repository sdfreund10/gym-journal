/**
 * Full-page loading overlay for same-origin navigations and form posts.
 */
(function () {
  const overlay = document.getElementById("nav-loading");
  if (!overlay) return;

  function isOptedOut(node) {
    return Boolean(node?.closest("[data-no-nav-loading]"));
  }

  function showLoading() {
    overlay.hidden = false;
    overlay.classList.remove("hidden");
    overlay.setAttribute("aria-hidden", "false");
  }

  function isNavigableLink(link, event) {
    if (isOptedOut(link)) return false;
    if (event.defaultPrevented || event.button !== 0) return false;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
    if (link.target && link.target.toLowerCase() === "_blank") return false;

    const href = link.getAttribute("href");
    if (!href || href === "#" || href.startsWith("#")) return false;

    try {
      const url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return false;
      return url.protocol === "http:" || url.protocol === "https:";
    } catch {
      return false;
    }
  }

  document.addEventListener(
    "click",
    (event) => {
      const link = event.target.closest("a[href]");
      if (!link || !isNavigableLink(link, event)) return;
      showLoading();
    },
    true,
  );

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || isOptedOut(form)) return;

    queueMicrotask(() => {
      if (event.defaultPrevented) return;
      showLoading();
    });
  });
})();
