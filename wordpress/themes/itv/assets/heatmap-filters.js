// Heat-map filters ([itv_heatmaps]): show one question at a time and sort its
// groups by a concern. Only hides, shows and reorders rows that are already on
// the page; without this script every table is visible.
(function () {
  document.querySelectorAll('.itv-heatmaps').forEach(function (root) {
    var form = root.querySelector('.itv-heatmap-filters');
    var question = form.querySelector('[data-filter="question"]');
    var concern = form.querySelector('[data-filter="concern"]');
    var status = form.querySelector('[data-filter="status"]');
    var sections = root.querySelectorAll('.itv-heatmap-section');

    function apply() {
      var shown;
      sections.forEach(function (s) {
        var on = s.getAttribute('data-question') === question.value;
        s.hidden = !on;
        if (on) { shown = s; }
      });
      if (!shown) { return; }
      var body = shown.querySelector('tbody');
      var rows = Array.prototype.slice.call(body.rows);
      var code = concern.value;
      rows.sort(function (a, b) {
        if (!code) { return a.getAttribute('data-order') - b.getAttribute('data-order'); }
        var pa = +(a.querySelector('td[data-concern="' + code + '"]') || {}).dataset.pct;
        var pb = +(b.querySelector('td[data-concern="' + code + '"]') || {}).dataset.pct;
        return (pb - pa) || (a.getAttribute('data-order') - b.getAttribute('data-order'));
      });
      rows.forEach(function (r) { body.appendChild(r); });
      shown.querySelectorAll('[data-concern]').forEach(function (cell) {
        cell.classList.toggle('itv-heat--focus', !!code && cell.getAttribute('data-concern') === code);
      });
      status.textContent = question.options[question.selectedIndex].text + (code
        ? ', sorted by ' + concern.options[concern.selectedIndex].text + ', highest share first' : '');
    }

    form.hidden = false;
    question.addEventListener('change', apply);
    concern.addEventListener('change', apply);
    apply();
  });
})();
