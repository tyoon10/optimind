(function () {
  "use strict";

  // Plain JS + React.createElement — the Hermes plugin SDK exposes React at
  // runtime and there is no build step for plugin bundles.
  const SDK = window.__HERMES_PLUGIN_SDK__;
  const { React } = SDK;
  const { useEffect, useState, useCallback } = SDK.hooks;
  const { Card, CardContent, CardHeader, CardTitle, Badge, Button } = SDK.components;
  const e = React.createElement;

  const API = "/api/plugins/optimind";

  // Status is never colour alone: every state carries a glyph and a word.
  const STATUS = {
    matched: { glyph: "✓", label: "Matched", tone: "ok", why: "Both records agree" },
    journal_only: { glyph: "◑", label: "Journal only", tone: "info", why: "The journal has it, the structured log lost it — a write defect, not a behavior gap" },
    structured_only: { glyph: "◐", label: "Structured only", tone: "info", why: "The structured log has it, the audit log never recorded it" },
    mixed: { glyph: "◒", label: "Mixed", tone: "info", why: "Divergence in both directions" },
    needs_input: { glyph: "!", label: "Needs you", tone: "warn", why: "The journal line is incomplete — no rerun can fix it" },
    blackout: { glyph: "—", label: "No entry", tone: "muted", why: "No turn occurred and nothing was captured" },
    no_data: { glyph: "—", label: "No facts", tone: "muted", why: "Turns occurred but produced no structured fact" },
    in_progress: { glyph: "●", label: "Today", tone: "muted", why: "Still in progress — never counted as a miss" },
  };

  function statusOf(s) {
    return STATUS[s] || { glyph: "?", label: s, tone: "muted", why: "" };
  }

  function useJson(path, deps) {
    const [state, setState] = useState({ loading: true, data: null, error: null });
    const load = useCallback(function () {
      let live = true;
      setState(function (s) { return Object.assign({}, s, { loading: true }); });
      const get = SDK.fetchJSON
        ? SDK.fetchJSON(API + path)
        : fetch(API + path).then(function (r) {
            return r.json().then(function (j) {
              if (!r.ok) throw new Error((j.detail && j.detail.error) || r.status);
              return j;
            });
          });
      get
        .then(function (data) { if (live) setState({ loading: false, data: data, error: null }); })
        .catch(function (err) { if (live) setState({ loading: false, data: null, error: String(err.message || err) }); });
      return function () { live = false; };
    }, deps || []);
    useEffect(load, [load]);
    return state;
  }

  function Metric(props) {
    return e("div", { className: "optimind__metric" },
      e("strong", { className: "optimind__metric-value", style: props.tone ? { color: "var(--optimind-" + props.tone + ")" } : null },
        String(props.value)),
      e("span", { className: "optimind__muted" }, props.label),
    );
  }

  function DayCell(props) {
    const d = props.day;
    const s = statusOf(d.status);
    return e("button", {
      className: "optimind__cell optimind__cell--" + s.tone + (props.selected ? " is-selected" : ""),
      title: d.date + " — " + s.label + ". " + s.why,
      onClick: function () { props.onSelect(props.selected ? null : d.date); },
    },
      e("span", { className: "optimind__glyph" }, s.glyph),
      e("span", null, d.date.slice(8)),
    );
  }

  function DayDetail(props) {
    const state = useJson("/day/" + props.date, [props.date]);
    if (state.loading) return e("p", { className: "optimind__muted" }, "Loading " + props.date + "…");
    if (state.error) return e("p", { className: "optimind__warn" }, state.error);
    const d = state.data;
    const s = statusOf(d.status.status);

    return e("div", { className: "optimind__detail" },
      e("div", { className: "optimind__row" },
        e("strong", null, d.date),
        e(Badge, { variant: "outline" }, s.glyph + " " + s.label),
        e("span", { className: "optimind__muted" }, d.user_turns + " user turn(s)"),
      ),
      e("p", { className: "optimind__muted optimind__small" }, s.why),

      d.status.journal_only && d.status.journal_only.length
        ? e("p", { className: "optimind__info optimind__small" },
            "Lost from the structured log: " + d.status.journal_only.join(", "))
        : null,
      d.status.needs_input && d.status.needs_input.length
        ? e("p", { className: "optimind__warn optimind__small" },
            "Incomplete in the journal, needs you: " + d.status.needs_input.join(", "))
        : null,

      e("div", { className: "optimind__section" }, "Dashboard mirror lines"),
      d.facts.length
        ? e("pre", { className: "optimind__evidence" },
            d.facts.map(function (f) { return "[" + f.field + "] " + f.value; }).join("\n"))
        : e("p", { className: "optimind__muted optimind__small" }, "None on this day."),

      e("div", { className: "optimind__section" }, "Structured record"),
      Object.keys(d.log).length
        ? e("pre", { className: "optimind__evidence" }, JSON.stringify(d.log, null, 2))
        : e("p", { className: "optimind__muted optimind__small" }, "Empty."),
    );
  }

  function Coverage(props) {
    const state = useJson("/coverage?days=" + props.days, [props.days]);
    if (state.loading) return e("p", { className: "optimind__muted" }, "Loading coverage…");
    if (state.error) return e("p", { className: "optimind__warn" }, state.error);
    const data = state.data;

    return e("table", { className: "optimind__table" },
      e("thead", null, e("tr", null,
        e("th", null, "Field"),
        e("th", null, "Recorded"),
        e("th", null, "Journal only"),
      )),
      e("tbody", null, data.fields.map(function (f) {
        return e("tr", { key: f.field },
          e("td", { className: "optimind__mono" }, f.field),
          e("td", null, f.captured + " / " + data.closed_days),
          e("td", { className: f.journal_only ? "optimind__info" : "optimind__muted" },
            f.journal_only ? f.journal_only + " lost" : "—"),
        );
      })),
    );
  }

  function OptiMindTab() {
    const [days, setDays] = useState(14);
    const [selected, setSelected] = useState(null);
    const health = useJson("/health", []);
    const integrity = useJson("/integrity?days=" + days, [days]);

    if (health.data && health.data.ok === false) {
      return e(Card, null,
        e(CardHeader, null, e(CardTitle, { className: "text-sm" }, "OptiMind — journal not reachable")),
        e(CardContent, null,
          e("p", { className: "optimind__warn" }, health.data.error),
          e("p", { className: "optimind__muted optimind__small" },
            "Set OPTIMIND_JOURNAL_PATH to the optimind-journal checkout and restart the dashboard."),
        ),
      );
    }

    const data = integrity.data;

    return e("div", { className: "optimind" },
      e(Card, null,
        e(CardHeader, null, e(CardTitle, { className: "text-sm" }, "Record integrity")),
        e(CardContent, null,
          e("div", { className: "optimind__toolbar" },
            [7, 14, 30, 90].map(function (n) {
              return e(Button, {
                key: n, size: "sm",
                variant: days === n ? "default" : "outline",
                onClick: function () { setDays(n); },
              }, n + "d");
            }),
          ),

          integrity.loading ? e("p", { className: "optimind__muted" }, "Loading…") : null,
          integrity.error ? e("p", { className: "optimind__warn" }, integrity.error) : null,

          data ? e("div", { className: "optimind__metrics" },
            e(Metric, { value: data.matched + "/" + data.closed_days, label: "closed days consistent", tone: "ok" }),
            e(Metric, { value: data.closed_mismatches, label: "lost writes", tone: data.closed_mismatches ? "info" : "muted" }),
            e(Metric, { value: data.needs_input_days, label: "need your input", tone: data.needs_input_days ? "warn" : "muted" }),
          ) : null,

          data ? e("div", { className: "optimind__strip" },
            data.days.map(function (d) {
              return e(DayCell, { key: d.date, day: d, selected: selected === d.date, onSelect: setSelected });
            }),
          ) : null,

          data ? e("p", { className: "optimind__muted optimind__small" },
            "✓ matched · ◑ journal only (a lost write, not a missed habit) · ! needs you · — no entry · ● today"
          ) : null,

          data && data.closed_mismatches
            ? e("p", { className: "optimind__info optimind__small" },
                "Repair: python3 scripts/reconcile_daily_logs.py --start <d> --end <d>")
            : null,
        ),
      ),

      selected ? e(Card, null,
        e(CardHeader, null, e(CardTitle, { className: "text-sm" }, "Day detail")),
        e(CardContent, null, e(DayDetail, { date: selected })),
      ) : null,

      e(Card, null,
        e(CardHeader, null, e(CardTitle, { className: "text-sm" }, "Capture coverage")),
        e(CardContent, null,
          e("p", { className: "optimind__muted optimind__small" },
            "Fields recorded per closed day. A field can look uncaptured purely because its write was lost — that column is kept separate."),
          e(Coverage, { days: days }),
        ),
      ),

      e("p", { className: "optimind__muted optimind__small" },
        "Read-only. Capture and repair live in the OptiMind web app, which works from a phone."),
    );
  }

  window.__HERMES_PLUGINS__.register("optimind", OptiMindTab);
})();
