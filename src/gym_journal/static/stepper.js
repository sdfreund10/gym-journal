/**
 * Stepper controls with press-and-hold acceleration.
 */
(function () {
  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function initStepper(root) {
    const display = root.querySelector("[data-stepper-display]");
    const input = root.querySelector("[data-stepper-input]");
    const dec = root.querySelector("[data-stepper-dec]");
    const inc = root.querySelector("[data-stepper-inc]");
    if (!display || !input || !dec || !inc) return;

    const step = Number(root.dataset.step || 1);
    const min = Number(root.dataset.min || 0);
    const max = Number(root.dataset.max || 999);
    let value = Number(root.dataset.value || input.value || min);
    let timer = null;

    function setValue(next) {
      value = clamp(next, min, max);
      display.textContent = String(value);
      input.value = String(value);
      root.dataset.value = String(value);
    }

    function clearTimer() {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    }

    function bump(dir) {
      setValue(value + dir * step);
    }

    function hold(dir) {
      let delay = 400;
      const run = () => {
        bump(dir);
        delay = Math.max(45, delay * 0.72);
        timer = setTimeout(run, delay);
      };
      bump(dir);
      timer = setTimeout(run, delay);
    }

    dec.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      hold(-1);
    });
    inc.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      hold(1);
    });

    [dec, inc].forEach((btn) => {
      ["pointerup", "pointerleave", "pointercancel"].forEach((evt) => {
        btn.addEventListener(evt, clearTimer);
      });
    });

    const lastWeightBtn = root.querySelector("[data-last-weight]");
    if (lastWeightBtn) {
      lastWeightBtn.addEventListener("click", () => {
        const last = lastWeightBtn.dataset.lastWeight;
        if (last) setValue(Number(last));
      });
    }

    setValue(value);
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-stepper]").forEach(initStepper);
  });
})();
