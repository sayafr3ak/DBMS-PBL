/* PCETS front-end behaviour: theme, nav, modals, tabs, toasts, pickers, form helpers */
(function () {
  "use strict";
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------- theme ---------- */
  function setTheme(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem("pcets-theme", t); } catch (e) { /* storage blocked */ }
    $$("[data-theme-icon]").forEach(el => { el.querySelector("use").setAttribute("href", t === "dark" ? "#i-sun" : "#i-moon"); });
  }
  $$("[data-toggle-theme]").forEach(btn => btn.addEventListener("click", () =>
    setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark")));
  setTheme(document.documentElement.dataset.theme || "light");

  /* ---------- mobile nav ---------- */
  $$("[data-toggle-nav]").forEach(btn => btn.addEventListener("click", () => document.body.classList.toggle("nav-open")));
  document.addEventListener("click", e => {
    if (document.body.classList.contains("nav-open") && !e.target.closest(".sidebar") && !e.target.closest("[data-toggle-nav]")) {
      document.body.classList.remove("nav-open");
    }
  });

  /* ---------- global search shortcut ---------- */
  document.addEventListener("keydown", e => {
    if ((e.key === "/" || (e.key === "k" && (e.ctrlKey || e.metaKey))) && !/input|textarea|select/i.test(document.activeElement.tagName)) {
      const s = $("#global-search");
      if (s) { e.preventDefault(); s.focus(); s.select(); }
    }
  });

  /* ---------- modals ---------- */
  function openModal(id) {
    const dlg = document.getElementById(id);
    if (!dlg) return;
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
    const first = dlg.querySelector("input:not([type=hidden]):not([readonly]), select, textarea");
    if (first) setTimeout(() => first.focus(), 60);
  }
  window.pcetsOpenModal = openModal;
  $$("[data-open]").forEach(btn => btn.addEventListener("click", e => {
    e.preventDefault();
    const target = btn.dataset.open;
    const dlg = document.getElementById(target);
    // optional preset values: data-set-<field>="value"
    if (dlg) {
      Object.keys(btn.dataset).filter(k => k.startsWith("set")).forEach(k => {
        const name = k.slice(3).replace(/^[A-Z]/, c => c.toLowerCase()).replace(/[A-Z]/g, c => "_" + c.toLowerCase());
        const field = dlg.querySelector(`[name="${name}"]`);
        if (field) { field.value = btn.dataset[k]; field.dispatchEvent(new Event("change")); }
      });
    }
    openModal(target);
  }));
  $$("dialog.modal").forEach(dlg => {
    dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
    $$("[data-close]", dlg).forEach(b => b.addEventListener("click", () => dlg.close()));
  });
  const autoOpen = document.body.dataset.openModal;
  if (autoOpen) openModal(autoOpen);

  /* ---------- confirm ---------- */
  $$("form[data-confirm]").forEach(f => f.addEventListener("submit", e => {
    if (!confirm(f.dataset.confirm)) e.preventDefault();
  }));

  /* ---------- tabs ---------- */
  const tabLinks = $$(".tabs [data-tab]");
  function showTab(name, push) {
    if (!tabLinks.length) return;
    if (!$(`.tab-panel[data-panel="${name}"]`)) name = tabLinks[0].dataset.tab;
    tabLinks.forEach(a => a.classList.toggle("active", a.dataset.tab === name));
    $$(".tab-panel").forEach(p => p.classList.toggle("active", p.dataset.panel === name));
    if (push) {
      const url = new URL(location.href);
      url.searchParams.set("tab", name);
      history.replaceState(null, "", url);
    }
  }
  tabLinks.forEach(a => a.addEventListener("click", e => { e.preventDefault(); showTab(a.dataset.tab, true); }));
  if (tabLinks.length) showTab(document.body.dataset.tab || new URL(location.href).searchParams.get("tab") || tabLinks[0].dataset.tab);
  $$("[data-goto-tab]").forEach(a => a.addEventListener("click", e => { e.preventDefault(); showTab(a.dataset.gotoTab, true);
    window.scrollTo({ top: 0, behavior: "smooth" }); }));

  /* ---------- toasts ---------- */
  $$(".toast").forEach((t, i) => {
    const kill = () => { t.classList.add("hide"); setTimeout(() => t.remove(), 300); };
    t.querySelector("button")?.addEventListener("click", kill);
    if (!t.classList.contains("sticky")) setTimeout(kill, 5200 + i * 600);
  });

  /* ---------- clickable rows ---------- */
  $$("tr[data-href]").forEach(tr => tr.addEventListener("click", e => {
    if (e.target.closest("a, button, form, input, select")) return;
    location.href = tr.dataset.href;
  }));

  /* ---------- auto-submit filters ---------- */
  $$("[data-autosubmit]").forEach(el => el.addEventListener("change", () => el.form.submit()));

  /* ---------- datetime defaults ---------- */
  function localNow() {
    const d = new Date(); d.setSeconds(0, 0);
    const p = n => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  }
  $$("input[type=datetime-local][data-default-now]").forEach(i => { if (!i.value) i.value = localNow(); i.max = localNow(); });
  $$("input[type=date][data-default-today]").forEach(i => { if (!i.value) i.value = localNow().slice(0, 10); });
  $$("input[type=date][data-max-today]").forEach(i => { i.max = localNow().slice(0, 10); });

  /* ---------- existing / new person toggles ---------- */
  $$("[data-mode-switch]").forEach(group => {
    const name = group.dataset.modeSwitch;
    const update = () => {
      const val = (group.querySelector("input:checked") || {}).value;
      $$(`[data-mode-for="${name}"]`).forEach(panel => {
        const show = panel.dataset.mode === val;
        panel.hidden = !show;
        $$("input, select, textarea", panel).forEach(f => { f.disabled = !show; });
      });
    };
    group.addEventListener("change", update);
    update();
  });

  /* ---------- toggle sections by checkbox ---------- */
  $$("[data-toggles]").forEach(cb => {
    const target = document.getElementById(cb.dataset.toggles);
    const update = () => { if (target) { target.hidden = !cb.checked;
      $$("input, select, textarea", target).forEach(f => f.disabled = !cb.checked); } };
    cb.addEventListener("change", update); update();
  });

  /* ---------- show closure fields when CLOSED selected ---------- */
  $$("[data-status-select]").forEach(sel => {
    const box = document.getElementById(sel.dataset.statusSelect);
    const update = () => { if (!box) return; const on = sel.value === "CLOSED";
      box.hidden = !on; $$("input, select, textarea", box).forEach(f => f.disabled = !on); };
    sel.addEventListener("change", update); update();
  });

  /* ---------- person picker (AJAX search) ---------- */
  $$("[data-person-picker]").forEach(picker => {
    const input = $("input[type=search]", picker);
    const hidden = $("input[type=hidden]", picker);
    const results = $(".picker-results", picker);
    const picked = $(".picked", picker);
    let timer = null, items = [], focus = -1;
    const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    function choose(p) {
      hidden.value = p.id;
      picked.querySelector(".pname").textContent = p.name;
      picked.querySelector(".pmeta").textContent = [p.phone, p.address].filter(Boolean).join(" · ");
      picked.hidden = false; input.hidden = true; results.classList.remove("open");
    }
    picked?.querySelector(".x")?.addEventListener("click", e => {
      e.preventDefault(); hidden.value = ""; picked.hidden = true; input.hidden = false; input.value = ""; input.focus();
    });
    if (hidden.value) { choose({ id: hidden.value, name: picked.dataset.name || ("Person #" + hidden.value), phone: picked.dataset.meta }); }
    function render() {
      if (!items.length) { results.innerHTML = `<button type="button" disabled><span class="meta">No matching person — switch to “New person”.</span></button>`; }
      else {
        results.innerHTML = items.map((p, i) => `<button type="button" data-i="${i}" class="${i === focus ? "focus" : ""}">
          <span class="avatar sm c${(p.id % 6) + 1}">${esc(p.name.split(" ").map(w => w[0]).slice(0, 2).join(""))}</span>
          <span><b>${esc(p.name)}</b><br><span class="meta">${esc([p.phone, p.address].filter(Boolean).join(" · "))}</span></span>
          <span class="meta" style="margin-left:auto">#${p.id}</span></button>`).join("");
      }
      results.classList.add("open");
      $$("button[data-i]", results).forEach(b => b.addEventListener("click", () => choose(items[+b.dataset.i])));
    }
    input?.addEventListener("input", () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) { results.classList.remove("open"); return; }
      timer = setTimeout(async () => {
        try { items = await (await fetch(`/api/persons?q=${encodeURIComponent(q)}`)).json(); focus = -1; render(); }
        catch (e) { items = []; render(); }
      }, 180);
    });
    input?.addEventListener("keydown", e => {
      if (!results.classList.contains("open")) return;
      if (e.key === "ArrowDown") { focus = Math.min(focus + 1, items.length - 1); render(); e.preventDefault(); }
      if (e.key === "ArrowUp") { focus = Math.max(focus - 1, 0); render(); e.preventDefault(); }
      if (e.key === "Enter" && focus >= 0) { choose(items[focus]); e.preventDefault(); }
      if (e.key === "Escape") results.classList.remove("open");
    });
    document.addEventListener("click", e => { if (!picker.contains(e.target)) results.classList.remove("open"); });
  });

  /* ---------- table quick filter ---------- */
  $$("[data-table-filter]").forEach(inp => {
    const table = document.getElementById(inp.dataset.tableFilter);
    inp.addEventListener("input", () => {
      const q = inp.value.toLowerCase();
      $$("tbody tr", table).forEach(tr => { tr.hidden = q && !tr.textContent.toLowerCase().includes(q); });
    });
  });

  /* ---------- animate bars on load ---------- */
  requestAnimationFrame(() => {
    $$("[data-w]").forEach(el => { el.style.width = el.dataset.w; });
    $$("[data-h]").forEach(el => { el.style.height = el.dataset.h; });
  });

  /* ---------- prevent double submit ---------- */
  $$("form").forEach(f => f.addEventListener("submit", e => {
    if (e.defaultPrevented) return;
    const btn = f.querySelector("button[type=submit]:not([data-keep])");
    if (btn) setTimeout(() => { btn.disabled = true; btn.dataset.label = btn.innerHTML; btn.innerHTML = "Saving…"; }, 0);
  }));
})();
