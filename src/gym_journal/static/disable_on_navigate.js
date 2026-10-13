/**
 * Disable the link or submit button that starts a same-origin navigation.
 * Cancelled submits (confirm, timer) stay active. Back restores the control.
 */
(function () {
  function isNavigableLink(link, event) {
    if (event.button !== 0) return false;
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

  function markPending(control) {
    if (!control || control.dataset.navPending === "true") return;
    if ("disabled" in control && control.disabled) return;

    control.dataset.navPending = "true";
    control.setAttribute("aria-disabled", "true");
    if (control instanceof HTMLButtonElement || control instanceof HTMLInputElement) {
      control.disabled = true;
      control.dataset.navDisabled = "true";
    }
  }

  function clearPending() {
    document.querySelectorAll("[data-nav-pending]").forEach((control) => {
      delete control.dataset.navPending;
      control.removeAttribute("aria-disabled");
      if (control.dataset.navDisabled === "true") {
        control.disabled = false;
        delete control.dataset.navDisabled;
      }
    });
  }

  function whenNavigationContinues(event, mark) {
    if (event.defaultPrevented) return;
    window.setTimeout(() => {
      if (event.defaultPrevented) return;
      mark();
    }, 0);
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (!link) return;
    if (link.dataset.navPending === "true") {
      event.preventDefault();
      return;
    }
    if (!isNavigableLink(link, event)) return;

    whenNavigationContinues(event, () => markPending(link));
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;

    const submitter = event.submitter;
    if (submitter?.dataset.navPending === "true") {
      event.preventDefault();
      return;
    }

    whenNavigationContinues(event, () => {
      if (submitter) {
        markPending(submitter);
        return;
      }
      form
        .querySelectorAll("button:not([type='button']):not([type='reset']), input[type='submit']")
        .forEach(markPending);
    });
  });

  window.addEventListener("pageshow", clearPending);
})();
