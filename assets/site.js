/* РЕКС — интерактив: меню, формы, калькуляторы, кнопка «наверх» */
(function () {
  'use strict';

  // мобильное меню
  var burger = document.getElementById('burger');
  var mob = document.getElementById('mob');
  if (burger && mob) {
    burger.addEventListener('click', function () {
      var open = mob.classList.toggle('open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.style.overflow = open ? 'hidden' : '';
    });
    mob.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        mob.classList.remove('open');
        document.body.style.overflow = '';
      }
    });
  }

  // выпадающая группа «Помощь»: мышью открывается на hover (CSS), клавиатурой — по Enter/Space
  var drop = document.querySelector('.navdrop');
  if (drop) {
    var dropBtn = drop.querySelector('.navdrop__btn');
    var setDrop = function (open) {
      drop.classList.toggle('open', open);
      if (dropBtn) dropBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    if (dropBtn) {
      dropBtn.addEventListener('click', function (e) {
        e.preventDefault();
        setDrop(!drop.classList.contains('open'));
      });
    }
    document.addEventListener('click', function (e) {
      if (!drop.contains(e.target)) setDrop(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && drop.classList.contains('open')) {
        setDrop(false);
        if (dropBtn) dropBtn.focus();
      }
    });
  }

  // кнопка наверх
  var up = document.getElementById('up');
  if (up) {
    window.addEventListener('scroll', function () {
      up.classList.toggle('on', window.scrollY > 700);
    }, { passive: true });
    up.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // формы: собираем mailto
  var LM = 'info@rex.moscow';
  document.querySelectorAll('#leadForm').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var g = function (n) { var el = form.querySelector('[name="' + n + '"]'); return el ? el.value.trim() : ''; };
      if (!g('name') || !g('phone')) {
        var first = form.querySelector('[name="name"]');
        if (first && !first.value.trim()) { first.focus(); first.style.borderColor = '#ff4d1c'; return; }
        var ph = form.querySelector('[name="phone"]');
        if (ph) { ph.focus(); ph.style.borderColor = '#ff4d1c'; }
        return;
      }
      var body = 'Имя: ' + g('name') + '\nТелефон: ' + g('phone') +
        (g('email') ? '\nE-mail: ' + g('email') : '') +
        (g('msg') ? '\nЗадача: ' + g('msg') : '') +
        '\n\nОтправлено с ' + location.href;
      var ok = form.querySelector('#leadOk');
      if (ok) { ok.classList.add('on'); }
      window.location.href = 'mailto:' + LM + '?subject=' + encodeURIComponent('Заявка с сайта РЕКС') +
        '&body=' + encodeURIComponent(body);
    });
  });

  // калькулятор: живой пересчёт, подстановка значений в формулу, упаковки и стоимость
  var esc = function (s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  };
  var fmt = function (v) {
    if (!isFinite(v)) v = 0;
    if (Math.abs(v) >= 100) return Math.round(v).toLocaleString('ru-RU');
    return v.toFixed(1).replace('.', ',');
  };
  var calc = document.getElementById('calc');
  if (calc) {
    var btn = document.getElementById('calcBtn');
    var out = document.getElementById('calcOut');
    var packsEl = document.getElementById('calcPacks');
    var costEl = document.getElementById('calcCost');
    var fEl = document.getElementById('calcFormula');
    var formula = calc.getAttribute('data-formula') || '';
    var unit = calc.getAttribute('data-unit') || '';
    var pack = parseFloat(calc.getAttribute('data-pack') || '') || 0;
    var price = parseFloat(calc.getAttribute('data-price') || '') || 0;
    var rhs = formula.indexOf('=') !== -1 ? formula.split('=').pop().trim() : formula;
    var run = function () {
      var scope = {};
      var keys = [];
      calc.querySelectorAll('[data-calc]').forEach(function (inp) {
        var k = inp.getAttribute('data-calc');
        var v = parseFloat(String(inp.value).replace(',', '.'));
        scope[k] = isNaN(v) ? 0 : v;
        keys.push(k);
      });
      keys.sort(function (a, b) { return b.length - a.length; });
      var expr = rhs.replace(/×/g, '*').replace(/÷/g, '/').replace(/\^/g, '**');
      keys.forEach(function (k) { expr = expr.split(k).join('(' + scope[k] + ')'); });
      var val = 0;
      try { val = Function('"use strict";return (' + expr + ')')(); } catch (e) { val = 0; }
      if (!isFinite(val)) val = 0;
      out.textContent = fmt(val);
      var sub = rhs;
      keys.forEach(function (k) { sub = sub.split(k).join(fmt(scope[k])); });
      fEl.innerHTML = esc(sub) + ' = <em>' + fmt(val) + ' ' + esc(unit) + '</em>';
      if (packsEl && pack > 0) {
        var packs = Math.ceil(val / pack);
        packsEl.textContent = packs.toLocaleString('ru-RU') + ' шт';
        if (costEl && price > 0) {
          costEl.textContent = Math.round(packs * price).toLocaleString('ru-RU') + ' ₽';
        }
      }
    };
    if (btn) { btn.addEventListener('click', run); }
    calc.querySelectorAll('[data-calc]').forEach(function (inp) {
      inp.addEventListener('input', run);
      inp.addEventListener('change', run);
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); run(); } });
    });
    run();
  }

  // цели Яндекс.Метрики (работают, только если счётчик включён в config.py)
  var goal = function (name) {
    var id = window.__ymId || 0;
    if (!id || !window.ym) return;
    try { window.ym(id, 'reachGoal', name); } catch (e) {}
  };
  document.querySelectorAll('a[href^="tel:"]').forEach(function (a) {
    a.addEventListener('click', function () { goal('phone'); });
  });
  document.querySelectorAll('a[href^="mailto:"]').forEach(function (a) {
    a.addEventListener('click', function () { goal('email'); });
  });
  document.querySelectorAll('#leadForm').forEach(function (form) {
    form.addEventListener('submit', function () { goal('lead'); });
  });
  document.querySelectorAll('a[href*="vyezd-menedzhera"]').forEach(function (a) {
    a.addEventListener('click', function () { goal('visit'); });
  });

  // плавный переход к якорям внутри страницы
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href').slice(1);
      if (!id) return;
      var el = document.getElementById(id);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
})();
