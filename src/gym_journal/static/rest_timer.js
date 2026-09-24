/**
 * Count-up rest stopwatch anchored to the last set's logged_at.
 */
(function () {
  function formatElapsed(totalSeconds) {
    const seconds = Math.max(0, Math.floor(totalSeconds));
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hours > 0) {
      return (
        hours +
        ":" +
        String(mins).padStart(2, "0") +
        ":" +
        String(secs).padStart(2, "0")
      );
    }
    return mins + ":" + String(secs).padStart(2, "0");
  }

  function initRestTimer(root) {
    const display = root.querySelector("[data-rest-display]");
    const sinceRaw = root.dataset.restSince;
    if (!display || !sinceRaw) return;

    const sinceMs = Date.parse(sinceRaw);
    if (Number.isNaN(sinceMs)) return;

    function render() {
      const elapsedSeconds = (Date.now() - sinceMs) / 1000;
      display.textContent = formatElapsed(elapsedSeconds);
    }

    render();
    window.setInterval(render, 1000);
  }

  document.querySelectorAll("[data-rest-timer]").forEach(initRestTimer);
})();
