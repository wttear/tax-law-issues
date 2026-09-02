(() => {
  "use strict";

  const search = document.querySelector("#issue-search");
  const lawFilter = document.querySelector("#law-filter");
  const status = document.querySelector("#filter-status");
  const rows = Array.from(document.querySelectorAll(".issue-row"));

  if (!search || !lawFilter || !status || rows.length === 0) return;

  const normalize = (value) =>
    String(value || "")
      .trim()
      .toLocaleLowerCase("ko-KR")
      .replace(/\s+/g, " ");

  const update = () => {
    const query = normalize(search.value);
    const law = lawFilter.value;
    let visible = 0;

    rows.forEach((row) => {
      const matchesLaw = law === "all" || row.dataset.law === law;
      const matchesQuery = !query || normalize(row.dataset.search).includes(query);
      const show = matchesLaw && matchesQuery;
      row.hidden = !show;
      row.setAttribute("aria-hidden", String(!show));
      if (show) visible += 1;
    });

    document.querySelectorAll("[data-law-section]").forEach((section) => {
      const sectionRows = section.querySelectorAll(".issue-row:not([hidden])");
      section.hidden = sectionRows.length === 0;
    });

    const lawLabel =
      law === "all"
        ? "다섯 법률"
        : lawFilter.options[lawFilter.selectedIndex]?.textContent || law;
    status.textContent = `${lawLabel} · ${visible}개 쟁점 표시`;
  };

  search.addEventListener("input", update);
  lawFilter.addEventListener("change", update);
  update();
})();
