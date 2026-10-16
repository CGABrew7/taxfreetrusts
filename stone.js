/* Scroll progress for the family stone. Moss and the packet are drawn in CSS from --p. */
(function () {
  var stage = document.querySelector(".stone-stage");
  if (!stage) return;
  var pin = stage.querySelector(".stone-pin");
  var lead = stage.querySelector(".beat-lead");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce || !pin) {
    stage.setAttribute("data-beat", "5");
    return;
  }

  var head = document.querySelector(".site-head");
  var total = 1;
  var current = -1;
  var raf = 0;
  var idle = 0;
  var watching = false;
  var cuts = [0.16, 0.34, 0.5, 0.64, 0.78, 1.01];

  function headerH() {
    return head ? head.offsetHeight : 72;
  }

  function measure() {
    total = Math.max(1, stage.offsetHeight - pin.offsetHeight);
  }

  function indexFor(p) {
    var i;
    for (i = 0; i < cuts.length; i++) if (p < cuts[i]) return i;
    return cuts.length - 1;
  }

  function apply() {
    raf = 0;
    var start = stage.getBoundingClientRect().top - headerH();
    var p = Math.min(1, Math.max(0, -start / total));
    stage.style.setProperty("--p", p.toFixed(4));
    var beat = indexFor(p);
    if (beat === current) return;
    current = beat;
    stage.setAttribute("data-beat", String(beat));
    if (!lead) return;
    var on = beat === 0;
    lead.classList.toggle("is-on", on);
    if (on) lead.removeAttribute("inert");
    else lead.setAttribute("inert", "");
  }

  function request() {
    if (!raf) raf = window.requestAnimationFrame(apply);
    stage.classList.add("is-live");
    window.clearTimeout(idle);
    idle = window.setTimeout(function () {
      stage.classList.remove("is-live");
    }, 240);
  }

  measure();
  apply();
  if (lead && current === 0) lead.classList.add("is-on");
  stage.classList.add("is-ready");

  function watch(on) {
    if (on === watching) return;
    watching = on;
    if (on) window.addEventListener("scroll", request, { passive: true });
    else window.removeEventListener("scroll", request);
  }

  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      watch(entries[0].isIntersecting);
      if (entries[0].isIntersecting) request();
    });
    io.observe(stage);
  } else {
    watch(true);
  }

  window.addEventListener("resize", function () {
    measure();
    request();
  });
})();
