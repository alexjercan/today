import type {
  WidgetContext,
  WidgetFrontend,
  WidgetPresentation,
} from "@dashboardd/widget-sdk";
import {
  applyUpdate,
  baseStyles,
  formatDate,
  header,
  initialState,
  sendCommand,
  setStatus,
} from "./shared.js";

const styles = `${baseStyles}
article { justify-content:space-between; gap:5px; }
header .date { display:none; }
.current { flex:1 1 auto; display:flex; align-items:center; justify-content:center; min-height:0; }
.value { border:0; background:transparent; color:var(--dashboardd-color-text-bright); font-size:25px; font-weight:700; }
.weight-form { display:grid; grid-template-columns:1fr auto; }
.history { display:none; min-height:0; flex:1 1 auto; }
.history .row { grid-template-columns:1fr auto; }
.change { color:var(--dashboardd-color-secondary); font-size:13px; }
:host([data-presentation=focus]) header .date { display:block; }
:host([data-presentation=focus]) .current { flex:0 0 auto; justify-content:flex-start; }
:host([data-presentation=focus]) .value { font-size:30px; }
:host([data-presentation=focus]) .history { display:block; }
`;

export function mount(
  container: HTMLElement,
  context: WidgetContext,
): WidgetFrontend {
  const shadow = container.attachShadow({ mode: "open" });
  const state = initialState();
  let editing = false;
  const render = (): void => {
    if (state.destroyed) return;
    const article = document.createElement("article");
    article.append(header("Weight", state.snapshot));
    const current = document.createElement("div");
    current.className = "current";
    const weight = state.snapshot?.today.weight;
    if (weight === null || weight === undefined || editing) {
      current.append(weightForm(context, state, render, weight, () => (editing = false)));
    } else {
      const value = document.createElement("button");
      value.type = "button";
      value.className = "value";
      value.textContent = `${weight} kg`;
      value.title = "Edit today's weight";
      value.disabled = state.pending !== null;
      value.addEventListener("click", () => {
        editing = true;
        render();
      });
      current.append(value);
    }
    article.append(current);

    const history = document.createElement("div");
    history.className = "history rows";
    const entries = state.snapshot?.weight_history ?? [];
    if (entries.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "No recent weight";
      history.append(empty);
    }
    for (const entry of [...entries].reverse()) {
      const row = document.createElement("div");
      row.className = "row";
      const day = document.createElement("span");
      day.textContent = formatDate(entry.date, { weekday: "short", month: "short", day: "numeric" });
      const value = document.createElement("span");
      value.className = "metric";
      value.textContent = `${entry.value} kg`;
      row.append(day, value);
      history.append(row);
    }
    if (entries.length >= 2) {
      const change = entries.at(-1)!.value - entries[0].value;
      const summary = document.createElement("div");
      summary.className = "change";
      summary.textContent = `${change > 0 ? "+" : ""}${change.toFixed(1)} kg over ${entries.length} entries`;
      history.prepend(summary);
    }
    article.append(history);
    shadow.replaceChildren(styleElement(), article);
    setStatus(shadow, state);
  };
  render();
  return {
    update(payload: unknown): void {
      if (applyUpdate(state, payload)) {
        if (state.pending === null && state.error === null) editing = false;
        render();
      }
    },
    setPresentation(presentation: WidgetPresentation): void {
      shadow.host.setAttribute("data-presentation", presentation);
    },
    destroy(): void {
      state.destroyed = true;
      shadow.replaceChildren();
    },
  };
}

function weightForm(
  context: WidgetContext,
  state: ReturnType<typeof initialState>,
  render: () => void,
  current: number | null | undefined,
  finish: () => void,
): HTMLFormElement {
  const form = document.createElement("form");
  form.className = "weight-form";
  const input = document.createElement("input");
  input.type = "number";
  input.step = "0.1";
  input.min = "0";
  input.inputMode = "decimal";
  input.placeholder = "Weight kg";
  input.setAttribute("aria-label", "Today's weight in kilograms");
  if (current !== null && current !== undefined) input.value = String(current);
  input.disabled = state.pending !== null || state.snapshot === null;
  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Save";
  button.disabled = input.disabled;
  form.append(input, button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const today = state.snapshot?.today;
    if (!today || !input.value.trim()) return;
    sendCommand(
      context,
      state,
      "weight.set",
      { date: today.date, revision: today.revision, value: input.value },
      render,
    );
    finish();
  });
  return form;
}

function styleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = styles;
  return style;
}
