(function () {
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var els = document.querySelectorAll(".watch");
  if (reduce || !("IntersectionObserver" in window)) {
    for (var i = 0; i < els.length; i++) els[i].classList.add("in-view", "ticking");
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      en.target.classList.add("in-view", "ticking");
      io.unobserve(en.target);
    });
  }, { threshold: 0.28 });
  for (var j = 0; j < els.length; j++) io.observe(els[j]);
})();
