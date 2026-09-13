/**
 * Count-up stopwatch for timed exercise duration entry.
 */
(function () {
  const MIN_DEFAULT = 5;
  const MAX_DEFAULT = 900;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function formatElapsed(totalSeconds) {
    const seconds = Math.max(0, Math.floor(totalSeconds));
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins + ":" + String(secs).padStart(2, "0");
  }

  function initDurationTimer(root) {
    const display = root.querySelector("[data-timer-display]");
    const input = root.querySelector("[data-timer-input]");
    const timerPanel = root.querySelector("[data-timer-panel]");
    const manualPanel = root.querySelector("[data-manual-panel]");
    const modeButtons = root.querySelectorAll("[data-timer-mode]");
    const startBtn = root.querySelector("[data-timer-start]");
    const stopBtn = root.querySelector("[data-timer-stop]");
    const continueBtn = root.querySelector("[data-timer-continue]");
    const submitBtn = root.querySelector("[data-timer-submit]");
    const manualSubmitBtn = root.querySelector("[data-manual-submit]");
    const form = root.closest("form");
    const stepperRoot = root.querySelector("[data-stepper]");

    if (!display || !input || !startBtn || !stopBtn || !continueBtn || !submitBtn) {
      return;
    }

    const min = Number(root.dataset.min || MIN_DEFAULT);
    const max = Number(root.dataset.max || MAX_DEFAULT);

    let mode = "timer";
    let state = "idle";
    let elapsedMs = 0;
    let startedAt = null;
    let rafId = null;

    function setInputSeconds(seconds) {
      input.value = String(clamp(Math.floor(seconds), 0, max));
    }

    function renderDisplay() {
      const seconds = elapsedMs / 1000;
      display.textContent = formatElapsed(seconds);
      setInputSeconds(seconds);
    }

    function writeStepper(seconds) {
      const value = clamp(seconds, min, max);
      if (stepperRoot) {
        stepperRoot.dispatchEvent(
          new CustomEvent("stepper:set", { detail: value })
        );
      } else {
        input.value = String(value);
      }
    }

    function setModeButtonStyles() {
      modeButtons.forEach((btn) => {
        const selected = btn.dataset.timerMode === mode;
        btn.classList.toggle("bg-primary", selected);
        btn.classList.toggle("text-primary-foreground", selected);
        btn.classList.toggle("bg-secondary", !selected);
        btn.classList.toggle("text-secondary-foreground", !selected);
        btn.setAttribute("aria-pressed", selected ? "true" : "false");
        btn.disabled = state === "running" && btn.dataset.timerMode === "manual";
      });
    }

    function setDockVisibility() {
      const timerMode = mode === "timer";
      setHidden(startBtn, !(timerMode && state === "idle"));
      setHidden(stopBtn, !(timerMode && state === "running"));
      setHidden(continueBtn, !(timerMode && state === "stopped"));
      setHidden(submitBtn, !(timerMode && state === "stopped"));
      if (manualSubmitBtn) {
        setHidden(manualSubmitBtn, timerMode);
      }

      const canSubmit =
        timerMode && state === "stopped" && Math.floor(elapsedMs / 1000) >= min;
      submitBtn.disabled = !canSubmit;
    }

    function setHidden(el, isHidden) {
      if (!el) return;
      // Prefer Tailwind `hidden` over the HTML attribute: utilities like
      // `flex` otherwise win over the browser's default [hidden] rule.
      el.classList.toggle("hidden", isHidden);
      el.hidden = isHidden;
    }

    function setPanelVisibility() {
      if (timerPanel) {
        setHidden(timerPanel, mode !== "timer");
      }
      if (manualPanel) {
        setHidden(manualPanel, mode !== "manual");
      }
    }

    function applyUi() {
      root.dataset.mode = mode;
      root.dataset.state = state;
      setModeButtonStyles();
      setPanelVisibility();
      setDockVisibility();
      if (mode === "timer") {
        renderDisplay();
      }
    }

    function stopTicker() {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    }

    function tick() {
      if (state !== "running" || startedAt === null) return;
      const now = performance.now();
      elapsedMs = Math.min(max * 1000, now - startedAt);
      renderDisplay();
      if (elapsedMs >= max * 1000) {
        stopTimer();
        return;
      }
      rafId = requestAnimationFrame(tick);
    }

    function startTimer() {
      if (mode !== "timer") return;
      if (state === "idle") {
        elapsedMs = 0;
      }
      startedAt = performance.now() - elapsedMs;
      state = "running";
      stopTicker();
      applyUi();
      rafId = requestAnimationFrame(tick);
    }

    function stopTimer() {
      if (state !== "running") return;
      stopTicker();
      if (startedAt !== null) {
        elapsedMs = Math.min(max * 1000, performance.now() - startedAt);
      }
      startedAt = null;
      state = "stopped";
      applyUi();
    }

    function setMode(nextMode) {
      if (nextMode === mode || state === "running") return;

      if (nextMode === "manual") {
        const seconds = Math.floor(elapsedMs / 1000);
        if (seconds >= min) {
          writeStepper(seconds);
        } else {
          writeStepper(Number(stepperRoot?.dataset.value || min));
        }
        mode = "manual";
      } else {
        // Preserve stopped elapsed; idle stays at 0:00.
        mode = "timer";
      }
      applyUi();
    }

    startBtn.addEventListener("click", startTimer);
    stopBtn.addEventListener("click", stopTimer);
    continueBtn.addEventListener("click", startTimer);

    modeButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        setMode(btn.dataset.timerMode);
      });
    });

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && state === "running" && startedAt !== null) {
        elapsedMs = Math.min(max * 1000, performance.now() - startedAt);
        renderDisplay();
        if (elapsedMs >= max * 1000) {
          stopTimer();
        }
      }
    });

    if (form) {
      form.addEventListener("submit", (event) => {
        if (mode === "timer") {
          const seconds = Math.floor(elapsedMs / 1000);
          if (state !== "stopped" || seconds < min) {
            event.preventDefault();
            return;
          }
          setInputSeconds(clamp(seconds, min, max));
        } else {
          const seconds = Number(input.value || 0);
          input.value = String(clamp(seconds, min, max));
        }
      });
    }

    elapsedMs = 0;
    applyUi();
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-duration-timer]").forEach(initDurationTimer);
  });
})();
