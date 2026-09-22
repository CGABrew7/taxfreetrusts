/* Single source for Stripe Payment Links. Pages only reference plan keys. */
var PLANS = {
  will: {name: "Will", price: 79, url: "https://buy.stripe.com/bJe4gzaPYa999he7se73G02"},
  living: {name: "Living trust", price: 349, url: "https://buy.stripe.com/bJeeVdf6e955dxu13Q73G01"},
  counsel: {name: "Counsel desk", price: 790, url: "https://buy.stripe.com/8x23cv5vE0yz0KIbIu73G00"}
};

function bindPayLink(el, key) {
  var plan = PLANS[key];
  if (!el || !plan) return;
  el.href = plan.url;
  el.target = "_blank";
  el.rel = "noopener noreferrer";
  el.textContent = "Pay $" + plan.price;
  el.setAttribute("aria-label", "Pay $" + plan.price + " for " + plan.name);
}

function bindPayLinks(root) {
  (root || document).querySelectorAll("[data-pay]").forEach(function (el) {
    bindPayLink(el, el.getAttribute("data-pay"));
  });
}

bindPayLinks();
