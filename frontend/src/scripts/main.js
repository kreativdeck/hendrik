const header = document.querySelector("[data-header]");
const nav = document.querySelector("[data-site-nav]");
const toggle = document.querySelector("[data-nav-toggle]");

document.querySelectorAll("[data-current-year]").forEach((element) => {
  element.textContent = new Date().getFullYear();
});

if (header && nav && toggle) {
  const grid = header.querySelector("[data-header-grid]");
  const brand = header.querySelector("[data-header-brand]");
  const contact = header.querySelector("[data-header-contact]");
  const list = header.querySelector("[data-header-list]");
  const groups = [...header.querySelectorAll("[data-submenu-toggle]")].map((button) => ({
    button,
    submenu: document.getElementById(button.getAttribute("aria-controls")),
    item: button.closest("li"),
  }));
  const slideUpAfter = Number(header.dataset.slideUpAfter || 300);
  let panelOpen = false;
  let compact = false;
  let lastScrollY = window.scrollY;
  let fitFrame = 0;
  let scrollFrame = 0;
  let closeOnFit = false;
  let pointerTarget = null;

  const showHeader = () => header.classList.remove("is-hidden");

  const closeSubmenus = (except = null) => {
    groups.forEach((group) => {
      if (group === except) return;
      if (group.submenu.contains(document.activeElement)) group.button.focus();
      group.button.setAttribute("aria-expanded", "false");
      group.submenu.inert = true;
      group.submenu.hidden = true;
    });
  };

  const setPanelOpen = (open, returnFocus = false) => {
    panelOpen = open && compact;
    if (!panelOpen) {
      if (returnFocus || nav.contains(document.activeElement)) toggle.focus();
      closeSubmenus();
    }
    nav.classList.toggle("is-open", panelOpen);
    toggle.setAttribute("aria-expanded", String(panelOpen));
    toggle.setAttribute("aria-label", panelOpen ? "Menü schließen" : "Menü öffnen");
    nav.inert = compact && !panelOpen;
    document.body.classList.toggle("has-open-navigation", panelOpen);
    showHeader();
    if (panelOpen) nav.querySelector("button, a[href]")?.focus();
  };

  groups.forEach((group) => {
    group.submenu.inert = true;
    group.submenu.hidden = true;
    group.button.addEventListener("click", () => {
      const open = group.button.getAttribute("aria-expanded") !== "true";
      closeSubmenus(group);
      group.button.setAttribute("aria-expanded", String(open));
      group.submenu.inert = !open;
      group.submenu.hidden = !open;
      showHeader();
    });
    group.item.addEventListener("pointerleave", (event) => {
      if (event.pointerType === "mouse" && !compact) closeSubmenus();
    });
    group.item.addEventListener("focusout", (event) => {
      if (!group.item.contains(event.relatedTarget)) {
        // Keep mobile rows stable until the pointer click is delivered.
        // Hiding an earlier submenu on mousedown moves the next button away.
        if (compact && pointerTarget && header.contains(pointerTarget)) return;
        group.button.setAttribute("aria-expanded", "false");
        group.submenu.inert = true;
        group.submenu.hidden = true;
      }
    });
  });

  toggle.addEventListener("click", () => setPanelOpen(!panelOpen));
  nav.querySelectorAll("a[href]").forEach((link) => {
    link.addEventListener("click", () => {
      if (panelOpen) setPanelOpen(false);
      else closeSubmenus();
    });
  });

  document.addEventListener("pointerdown", (event) => {
    pointerTarget = event.target;
    if (!header.contains(event.target)) {
      closeSubmenus();
      if (panelOpen) setPanelOpen(false);
    } else if (!event.target.closest("[data-header-list] > li")) {
      closeSubmenus();
    }
  });

  // Touch synthesizes mouse focus after pointerup; clear only after click.
  document.addEventListener("click", () => { pointerTarget = null; });
  document.addEventListener("keydown", () => { pointerTarget = null; });
  document.addEventListener("pointercancel", () => { pointerTarget = null; });

  header.addEventListener("focusin", showHeader);
  header.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      const openGroup = groups.find((group) => group.button.getAttribute("aria-expanded") === "true");
      if (openGroup) {
        event.preventDefault();
        closeSubmenus();
        openGroup.button.focus();
      } else if (panelOpen) {
        event.preventDefault();
        setPanelOpen(false, true);
      }
    }
    if (event.key === "Tab" && panelOpen) {
      const focusable = [...header.querySelectorAll("a[href], button:not([disabled])")]
        .filter((element) => !element.closest("[inert]") && element.getClientRects().length > 0);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  // Measure the actual desktop content, including symmetrical outer columns.
  // Removing the compact state for this synchronous read never paints it.
  const fitNavigation = () => {
    fitFrame = 0;
    const activeElement = document.activeElement;
    const navHadFocus = nav.contains(activeElement);
    const toggleHadFocus = activeElement === toggle;
    const contactHadFocus = activeElement === contact;
    const mobileContactHadFocus = activeElement.matches("[data-mobile-contact]");
    // Übergänge während der Messung aus, sonst fährt das Menü bei jeder Messung kurz ein und aus.
    const wasAnimated = header.classList.contains("is-animated");
    header.classList.remove("is-animated", "is-compact");
    const gap = parseFloat(getComputedStyle(grid).columnGap) || 0;
    const sideWidth = Math.max(brand.getBoundingClientRect().width, contact.getBoundingClientRect().width);
    const needed = list.getBoundingClientRect().width + sideWidth * 2 + gap * 2;
    const nextCompact = needed > grid.getBoundingClientRect().width;
    const modeChanged = nextCompact !== compact;
    compact = nextCompact;
    header.classList.toggle("is-compact", compact);
    nav.getBoundingClientRect();
    if (wasAnimated) header.classList.add("is-animated");
    nav.inert = compact && !panelOpen;
    const shouldClose = modeChanged || closeOnFit;
    closeOnFit = false;
    if (shouldClose) {
      setPanelOpen(false);
      closeSubmenus();
    }
    if (compact && (toggleHadFocus || contactHadFocus || (navHadFocus && shouldClose))) {
      toggle.focus({ preventScroll: true });
    } else if (!compact && mobileContactHadFocus) {
      contact.focus({ preventScroll: true });
    } else if (!compact && toggleHadFocus) {
      (nav.querySelector("button, a[href]") || brand).focus({ preventScroll: true });
    } else if (header.contains(activeElement) && activeElement.getClientRects().length > 0) {
      activeElement.focus({ preventScroll: true });
    }
    header.style.setProperty("--header-height", `${header.getBoundingClientRect().height}px`);
  };

  const queueFit = () => {
    if (!fitFrame) fitFrame = requestAnimationFrame(fitNavigation);
  };

  header.classList.add("is-ready");
  fitNavigation();
  // Übergänge erst nach der ersten Messung, damit das Menü beim Laden nicht einfährt.
  requestAnimationFrame(() => requestAnimationFrame(() => header.classList.add("is-animated")));
  const resizeObserver = new ResizeObserver(queueFit);
  [grid, brand, contact, list].forEach((element) => resizeObserver.observe(element));
  window.addEventListener("resize", () => {
    closeOnFit = true;
    queueFit();
  }, { passive: true });
  document.fonts.ready.then(queueFit);

  window.addEventListener("scroll", () => {
    if (scrollFrame) return;
    scrollFrame = requestAnimationFrame(() => {
      const scrollY = Math.max(0, window.scrollY);
      const hasOpenSubmenu = groups.some((group) => group.button.getAttribute("aria-expanded") === "true");
      const mustShow = panelOpen || hasOpenSubmenu || header.contains(document.activeElement);
      if (mustShow || scrollY <= slideUpAfter || scrollY < lastScrollY) {
        showHeader();
      } else if (scrollY > lastScrollY) {
        header.classList.add("is-hidden");
      }
      lastScrollY = scrollY;
      scrollFrame = 0;
    });
  }, { passive: true });
}

const galleryDialog = document.querySelector("[data-gallery-dialog]");
const galleryData = document.getElementById("gallery-data");

if (galleryDialog && galleryData && typeof galleryDialog.showModal === "function") {
  const galleries = JSON.parse(galleryData.textContent);
  const heading = galleryDialog.querySelector("#lightbox-heading");
  const image = galleryDialog.querySelector("[data-gallery-image]");
  const error = galleryDialog.querySelector("[data-gallery-error]");
  const caption = galleryDialog.querySelector("[data-gallery-caption]");
  let images = [];
  let index = 0;

  const show = (next) => {
    index = (next + images.length) % images.length;
    const current = images[index];
    error.hidden = true;
    image.hidden = false;
    image.src = current.src;
    image.alt = current.alt;
    if (current.width && current.height) {
      image.width = current.width;
      image.height = current.height;
    }
    caption.textContent = `${index + 1} / ${images.length}`;
    new Image().src = images[(index + 1) % images.length].src;
  };

  const open = (key, start = 0) => {
    const gallery = galleries[key];
    if (!gallery || !gallery.images.length) return;
    images = gallery.images;
    heading.textContent = gallery.label;
    show(start);
    if (!galleryDialog.open) galleryDialog.showModal();
  };

  image.addEventListener("error", () => {
    image.hidden = true;
    error.hidden = false;
  });

  document.querySelector("[data-gallery-fallback]")?.setAttribute("hidden", "");
  document.querySelectorAll("[data-gallery-trigger]").forEach((trigger) => {
    trigger.disabled = false;
    trigger.addEventListener("click", () => open(trigger.dataset.galleryTrigger, Number(trigger.dataset.galleryIndex || 0)));
  });

  galleryDialog.querySelector("[data-gallery-close]").addEventListener("click", () => galleryDialog.close());
  galleryDialog.querySelector("[data-gallery-prev]").addEventListener("click", () => show(index - 1));
  galleryDialog.querySelector("[data-gallery-next]").addEventListener("click", () => show(index + 1));
  galleryDialog.addEventListener("click", (event) => {
    if (event.target === galleryDialog) galleryDialog.close();
  });
  galleryDialog.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") show(index - 1);
    if (event.key === "ArrowRight") show(index + 1);
  });
  galleryDialog.addEventListener("close", () => {
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
  });

  const openFromHash = () => {
    const key = location.hash.slice(1);
    if (galleries[key]) open(key);
    else if (galleryDialog.open) galleryDialog.close();
  };

  window.addEventListener("hashchange", openFromHash);
  openFromHash();
}
