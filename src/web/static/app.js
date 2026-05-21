(function () {
  "use strict";

  var _DEBOUNCE = 150;

  function asciToPt(s) {
    if (!s) return s;
    var rules = [
      [/\buidos\b/g, "uídos"],
      [/\buidas\b/g, "uídas"],
      [/\buido\b(?!s|\w)/g, "uído"],
      [/\buida\b(?!s|\w)/g, "uída"],
      [/ografico/g, "ográfico"],
      [/onomica/g, "onômica"],
      [/logico\b/g, "lógico"],
      [/\bizacao\b/g, "ização"],
      [/\batorio\b/g, "atório"],
      [/\baveis\b/g, "áveis"],
      [/\bivel\b/g, "ível"],
      [/\barios\b/g, "ários"],
      [/\bario\b/g, "ário"],
      [/\bacoes\b/g, "ações"],
      [/\bcoes\b/g, "ções"],
      [/\bico\b/g, "ico"],
      [/\beis\b/g, "éis"],
      [/\besao\b/g, "esão"],
      [/\bsao\b/g, "são"],
      [/\bacao\b/g, "ação"],
      [/\boes\b/g, "ões"],
    ];
    var out = s;
    for (var i = 0; i < rules.length; i++) {
      out = out.replace(rules[i][0], rules[i][1]);
    }
    return out;
  }

  function applyAsciPt(el) {
    var targets = el.querySelectorAll("[data-asci-pt]");
    if (el.hasAttribute && el.hasAttribute("data-asci-pt")) {
      el.textContent = asciToPt(el.textContent);
    }
    for (var i = 0; i < targets.length; i++) {
      targets[i].textContent = asciToPt(targets[i].textContent);
    }
  }

  function initSteppers(root) {
    var els = root.querySelectorAll("[data-stepper]");
    for (var i = 0; i < els.length; i++) {
      (function (wrap) {
        var input = wrap.querySelector("input[name=value]");
        var btnMinus = wrap.querySelector("[data-stepper-minus]");
        var btnPlus = wrap.querySelector("[data-stepper-plus]");
        if (!input) return;
        var step = parseFloat(wrap.getAttribute("data-step") || "1");
        var allowZero = wrap.getAttribute("data-allow-zero") === "true";
        var floor = allowZero ? 0 : step;

        function clamp(v) {
          if (!allowZero && v < floor) return floor;
          if (allowZero && v < 0) return 0;
          return v;
        }

        if (btnMinus) {
          btnMinus.addEventListener("click", function (e) {
            e.preventDefault();
            var cur = parseFloat(input.value) || 0;
            input.value = clamp(cur - step).toFixed(step < 1 ? 1 : 0);
            input.dispatchEvent(new Event("input", { bubbles: true }));
          });
        }
        if (btnPlus) {
          btnPlus.addEventListener("click", function (e) {
            e.preventDefault();
            var cur = parseFloat(input.value) || 0;
            input.value = clamp(cur + step).toFixed(step < 1 ? 1 : 0);
            input.dispatchEvent(new Event("input", { bubbles: true }));
          });
        }
      })(els[i]);
    }
  }

  function initJornada(root) {
    var els = root.querySelectorAll("[data-jornada]");
    for (var i = 0; i < els.length; i++) {
      (function (wrap) {
        var input = wrap.querySelector("input[name=value]");
        var btnDec = wrap.querySelector("[data-jornada-dec]");
        var btnHm = wrap.querySelector("[data-jornada-hm]");
        var label = wrap.querySelector("[data-jornada-label]");
        var mode = "decimal";

        function decimalToHm(d) {
          var h = Math.floor(d);
          var m = Math.round((d - h) * 60);
          if (m === 60) { h++; m = 0; }
          return h + ":" + (m < 10 ? "0" : "") + m;
        }

        function hmToDecimal(s) {
          var parts = s.split(":");
          if (parts.length !== 2) return parseFloat(s) || 0;
          return parseInt(parts[0], 10) + parseInt(parts[1], 10) / 60;
        }

        if (btnDec) {
          btnDec.addEventListener("click", function (e) {
            e.preventDefault();
            if (mode === "decimal") return;
            mode = "decimal";
            if (label) label.textContent = "Decimal";
            btnDec.classList.add("chip-active");
            if (btnHm) btnHm.classList.remove("chip-active");
            var val = hmToDecimal(input.value);
            input.value = val.toFixed(1);
            input.placeholder = "0.0";
          });
        }
        if (btnHm) {
          btnHm.addEventListener("click", function (e) {
            e.preventDefault();
            if (mode === "hhmm") return;
            mode = "hhmm";
            if (label) label.textContent = "HH:MM";
            btnHm.classList.add("chip-active");
            if (btnDec) btnDec.classList.remove("chip-active");
            var val = parseFloat(input.value) || 0;
            input.value = decimalToHm(val);
            input.placeholder = "0:00";
          });
        }
      })(els[i]);
    }
  }

  function initPaginate(root) {
    var els = root.querySelectorAll("[data-paginate]");
    for (var i = 0; i < els.length; i++) {
      (function (wrap) {
        var items = JSON.parse(wrap.getAttribute("data-items") || "[]");
        var pageSize = parseInt(wrap.getAttribute("data-page-size") || "5", 10);
        var form = wrap.closest("form");
        var listEl = wrap.querySelector("[data-paginate-list]");
        var pageIndicator = wrap.querySelector("[data-paginate-info]");
        var btnPrev = wrap.querySelector("[data-paginate-prev]");
        var btnNext = wrap.querySelector("[data-paginate-next]");
        var totalPages = Math.ceil(items.length / pageSize) || 1;
        var currentPage = 0;

        function renderPage() {
          if (!listEl) return;
          var start = currentPage * pageSize;
          var end = Math.min(start + pageSize, items.length);
          var html = "";
          for (var j = start; j < end; j++) {
            var idx = j + 1;
            html += '<li class="mb-1"><button type="submit" name="value" value="' + idx + '" class="btn w-full text-left min-h-[48px]">' + idx + ". " + items[j] + "</button></li>";
          }
          listEl.innerHTML = html;
          if (pageIndicator) {
            pageIndicator.textContent = (currentPage + 1) + "/" + totalPages;
          }
          if (btnPrev) btnPrev.disabled = currentPage <= 0;
          if (btnNext) btnNext.disabled = currentPage >= totalPages - 1;
          applyAsciPt(listEl);
        }

        if (btnPrev) {
          btnPrev.addEventListener("click", function (e) {
            e.preventDefault();
            if (currentPage > 0) { currentPage--; renderPage(); }
          });
        }
        if (btnNext) {
          btnNext.addEventListener("click", function (e) {
            e.preventDefault();
            if (currentPage < totalPages - 1) { currentPage++; renderPage(); }
          });
        }

        renderPage();
      })(els[i]);
    }
  }

  function initThemeToggle() {
    var btns = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function () {
        var html = document.documentElement;
        var current = html.getAttribute("data-theme") || "";
        var next = current === "neo-brutalist" ? "" : "neo-brutalist";
        html.setAttribute("data-theme", next);
        localStorage.setItem("orca-theme", next);
        updateThemeIcon();
      });
    }
    updateThemeIcon();
  }

  function updateThemeIcon() {
    var current = document.documentElement.getAttribute("data-theme") || "";
    var btns = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].textContent = current === "neo-brutalist" ? "░" : "▓";
      btns[i].setAttribute("aria-label", current === "neo-brutalist" ? "Modo Escuro" : "Modo Claro");
    }
  }

  function initDashboard() {
    var btns = document.querySelectorAll("[data-dashboard-toggle]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function () {
        var db = document.getElementById("dashboard");
        if (db) db.classList.toggle("dashboard-expanded");
        this.textContent = db && db.classList.contains("dashboard-expanded") ? "▾" : "▸";
      });
    }
  }

  function initAll(root) {
    root = root || document;
    initSteppers(root);
    initJornada(root);
    initPaginate(root);
    applyAsciPt(root);
  }

  function onHtmxAfterSwap(e) {
    initAll(e.detail.elt || e.target);
    var newStep = (e.detail.elt || e.target).querySelector("[id^=step-]") || (e.detail.elt || e.target);
    if (newStep && newStep.focus) {
      try { newStep.focus({ preventScroll: false }); } catch (_) {}
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var saved = localStorage.getItem("orca-theme") || "";
    if (saved) document.documentElement.setAttribute("data-theme", saved);
    initThemeToggle();
    initDashboard();
    initAll(document);
  });

  document.addEventListener("htmx:afterSwap", onHtmxAfterSwap);
  document.addEventListener("htmx:oobAfterSwap", onHtmxAfterSwap);

  window.ORCA = { asciToPt: asciToPt, initAll: initAll };
})();
