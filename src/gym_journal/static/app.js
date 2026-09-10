/**
 * Client-side search, muscle filter, chip toggles, and delete confirm.
 */
(function () {
  const FILTER_CHIP_ACTIVE = ["bg-primary", "text-primary-foreground"];
  const FILTER_CHIP_INACTIVE = ["bg-card"];
  const CATEGORY_CHIP_ACTIVE = ["bg-primary", "text-primary-foreground"];
  const CATEGORY_CHIP_INACTIVE = ["bg-card"];
  const MUSCLE_CHIP_ACTIVE = ["bg-accent", "text-accent-foreground"];
  const MUSCLE_CHIP_INACTIVE = ["bg-card"];

  function setClasses(el, active, activeClasses, inactiveClasses) {
    activeClasses.forEach((cls) => el.classList.toggle(cls, active));
    inactiveClasses.forEach((cls) => el.classList.toggle(cls, !active));
  }

  function initSearch(container) {
    const input = container.querySelector("[data-search-input]");
    const listId = container.dataset.searchList;
    const list = document.getElementById(listId);
    if (!input || !list) return;

    const items = Array.from(list.querySelectorAll("[data-search-item]"));
    const emptyStates = Array.from(list.querySelectorAll("[data-search-empty]"));

    function filter() {
      const query = input.value.trim().toLowerCase();
      let visible = 0;

      items.forEach((item) => {
        const text = item.dataset.searchText || "";
        const muscles = item.dataset.muscles || "";
        const muscleFilter = list.dataset.activeMuscle || "";
        const matchesSearch = !query || text.includes(query);
        const matchesMuscle = !muscleFilter || muscles.split(" ").includes(muscleFilter);
        const show = matchesSearch && matchesMuscle;
        item.hidden = !show;
        if (show) visible += 1;
      });

      emptyStates.forEach((emptyState) => {
        emptyState.hidden = visible > 0;
      });
    }

    input.addEventListener("input", filter);
    list.addEventListener("muscle-filter", filter);
    filter();
  }

  function initMuscleFilter(container) {
    const listId = container.closest("main")?.querySelector("[data-search-list]")?.dataset.searchList;
    const list = listId ? document.getElementById(listId) : null;
    if (!list) return;

    container.querySelectorAll("[data-filter-chip]").forEach((chip) => {
      chip.addEventListener("click", () => {
        container.querySelectorAll("[data-filter-chip]").forEach((el) => {
          setClasses(el, false, FILTER_CHIP_ACTIVE, FILTER_CHIP_INACTIVE);
        });
        setClasses(chip, true, FILTER_CHIP_ACTIVE, FILTER_CHIP_INACTIVE);
        list.dataset.activeMuscle = chip.dataset.muscle || "";
        list.dispatchEvent(new CustomEvent("muscle-filter"));
      });
    });
  }

  function initChipGroups() {
    document.querySelectorAll("[data-chip-group='category']").forEach((group) => {
      const syncGroup = () => {
        group.querySelectorAll("[data-chip-select]").forEach((el) => {
          setClasses(
            el,
            Boolean(el.querySelector("input")?.checked),
            CATEGORY_CHIP_ACTIVE,
            CATEGORY_CHIP_INACTIVE,
          );
        });
      };

      group.querySelectorAll("input[type='radio']").forEach((input) => {
        input.addEventListener("change", syncGroup);
      });
      syncGroup();
    });

    document.querySelectorAll("[data-chip-group='muscles']").forEach((group) => {
      group.querySelectorAll("[data-chip-select]").forEach((label) => {
        const input = label.querySelector("input");
        if (!input) return;

        const sync = () => {
          setClasses(label, input.checked, MUSCLE_CHIP_ACTIVE, MUSCLE_CHIP_INACTIVE);
        };

        input.addEventListener("change", sync);
        sync();
      });
    });
  }

  function initToggles() {
    document.querySelectorAll("[data-toggle]").forEach((trigger) => {
      trigger.addEventListener("click", () => {
        const targetId = trigger.dataset.toggle;
        const target = document.getElementById(targetId);
        if (!target) return;
        const isHidden = target.hasAttribute("hidden");
        if (isHidden) {
          target.removeAttribute("hidden");
        } else {
          target.setAttribute("hidden", "");
        }
      });
    });
  }

  function initToasts() {
    const stack = document.getElementById("toast-stack");
    if (!stack) return;
    window.setTimeout(() => {
      stack.classList.add("opacity-0");
      window.setTimeout(() => stack.remove(), 300);
    }, 3200);
  }

  function initDeleteConfirm() {
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
      form.addEventListener("submit", (event) => {
        if (!window.confirm(form.dataset.confirm)) {
          event.preventDefault();
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-search-list]").forEach(initSearch);
    document.querySelectorAll("[data-muscle-filter]").forEach(initMuscleFilter);
    initChipGroups();
    initToggles();
    initToasts();
    initDeleteConfirm();
  });
})();
