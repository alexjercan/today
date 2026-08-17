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
  removeButton,
  sendCommand,
  setStatus,
  taskCheckbox,
  type DatedTasks,
} from "./shared.js";

const styles = `${baseStyles}
.normal { min-height:0; flex:1 1 auto; display:flex; flex-direction:column; gap:7px; }
.normal .rows { flex:1 1 auto; }
.normal .row { grid-template-columns:auto 1fr; }
.when { color:var(--dashboardd-color-secondary); font-size:12px; white-space:nowrap; }
.upcoming-form { display:grid; grid-template-columns:125px minmax(90px, 1fr) auto; }
.focus { display:none; min-height:0; flex:1 1 auto; grid-template-columns:minmax(280px, .9fr) minmax(300px, 1.1fr); gap:14px; }
:host([data-presentation=focus]) .normal { display:none; }
:host([data-presentation=focus]) .focus { display:grid; }
.calendar { min-width:0; }
.month-header { display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:8px; margin-bottom:8px; }
.month-title { text-align:center; color:var(--dashboardd-color-text-bright); font-size:14px; }
.weekdays, .days { display:grid; grid-template-columns:repeat(7, 1fr); gap:4px; }
.weekdays span { color:var(--dashboardd-color-text-muted); font-size:10px; text-align:center; }
.day { position:relative; min-width:0; min-height:38px; padding:4px; border-color:color-mix(in srgb, var(--dashboardd-color-border) 40%, transparent); }
.day.outside { visibility:hidden; }
.day.selected { border-color:var(--dashboardd-color-accent); color:var(--dashboardd-color-text-bright); }
.day:disabled { cursor:not-allowed; opacity:.35; }
.count { position:absolute; right:3px; bottom:2px; min-width:14px; color:var(--dashboardd-color-accent); font-size:9px; }
.selected-day { min-height:0; display:flex; flex-direction:column; gap:8px; }
.selected-day h3 { margin:0; color:var(--dashboardd-color-text-bright); font-size:14px; }
.selected-day .rows { flex:1 1 auto; }
.selected-day .row { grid-template-columns:1fr auto; }
`;

export function mount(
  container: HTMLElement,
  context: WidgetContext,
): WidgetFrontend {
  const shadow = container.attachShadow({ mode: "open" });
  const state = initialState();
  let selected = tomorrowIso();
  let month = selected.slice(0, 7);

  const render = (): void => {
    if (state.destroyed) return;
    const article = document.createElement("article");
    article.append(header("Upcoming", state.snapshot));
    article.append(normalView(context, state, render, selected));
    article.append(
      focusView(context, state, render, selected, month, (value) => {
        selected = value;
        month = value.slice(0, 7);
        render();
      }, (value) => {
        month = value;
        render();
      }),
    );
    shadow.replaceChildren(styleElement(), article);
    setStatus(shadow, state);
  };

  render();
  return {
    update(payload: unknown): void {
      if (applyUpdate(state, payload)) render();
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

function normalView(
  context: WidgetContext,
  state: ReturnType<typeof initialState>,
  render: () => void,
  selected: string,
): HTMLElement {
  const normal = document.createElement("div");
  normal.className = "normal";
  const rows = document.createElement("div");
  rows.className = "rows";
  const tasks = state.snapshot?.upcoming.next ?? [];
  if (tasks.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = state.snapshot ? "Nothing scheduled" : "Loading schedule...";
    rows.append(empty);
  }
  for (const task of tasks) {
    const row = document.createElement("div");
    row.className = "row";
    const when = document.createElement("span");
    when.className = "when";
    when.textContent = formatDate(task.date);
    const label = document.createElement("label");
    const text = document.createElement("span");
    text.className = "text";
    text.textContent = task.text;
    label.append(
      taskCheckbox(task, state.pending !== null, () => {
        sendCommand(
          context,
          state,
          "upcoming.toggle",
          { date: task.date, revision: task.revision, index: task.index },
          render,
        );
      }),
      text,
    );
    row.append(when, label);
    rows.append(row);
  }
  normal.append(rows, addForm(context, state, render, selected, null));
  return normal;
}

function focusView(
  context: WidgetContext,
  state: ReturnType<typeof initialState>,
  render: () => void,
  selected: string,
  month: string,
  selectDate: (value: string) => void,
  selectMonth: (value: string) => void,
): HTMLElement {
  const focus = document.createElement("div");
  focus.className = "focus";
  focus.append(calendar(state, selected, month, selectDate, selectMonth));

  const details = document.createElement("section");
  details.className = "selected-day";
  const title = document.createElement("h3");
  title.textContent = formatDate(selected, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  details.append(title);
  const dated = state.snapshot?.upcoming.dates.find((entry) => entry.date === selected);
  const rows = document.createElement("div");
  rows.className = "rows";
  if (!dated || dated.tasks.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No tasks for this date";
    rows.append(empty);
  } else {
    for (const task of dated.tasks) rows.append(focusTask(context, state, render, dated, task));
  }
  details.append(rows, addForm(context, state, render, selected, dated?.revision ?? null));
  focus.append(details);
  return focus;
}

function focusTask(
  context: WidgetContext,
  state: ReturnType<typeof initialState>,
  render: () => void,
  dated: DatedTasks,
  task: DatedTasks["tasks"][number],
): HTMLElement {
  const row = document.createElement("div");
  row.className = "row";
  const label = document.createElement("label");
  const text = document.createElement("span");
  text.className = "text";
  text.textContent = task.text;
  label.append(
    taskCheckbox(task, state.pending !== null, () => {
      sendCommand(
        context,
        state,
        "upcoming.toggle",
        { date: dated.date, revision: dated.revision, index: task.index },
        render,
      );
    }),
    text,
  );
  const remove = removeButton(task.text, () => {
    sendCommand(
      context,
      state,
      "upcoming.remove",
      { date: dated.date, revision: dated.revision, index: task.index },
      render,
    );
  });
  remove.disabled = state.pending !== null;
  row.append(label, remove);
  return row;
}

function calendar(
  state: ReturnType<typeof initialState>,
  selected: string,
  month: string,
  selectDate: (value: string) => void,
  selectMonth: (value: string) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "calendar";
  const header = document.createElement("div");
  header.className = "month-header";
  const previous = document.createElement("button");
  previous.type = "button";
  previous.textContent = "Prev";
  previous.disabled = month <= todayIso().slice(0, 7);
  previous.addEventListener("click", () => selectMonth(shiftMonth(month, -1)));
  const title = document.createElement("div");
  title.className = "month-title";
  title.textContent = formatDate(`${month}-01`, { month: "long", year: "numeric" });
  const next = document.createElement("button");
  next.type = "button";
  next.textContent = "Next";
  next.addEventListener("click", () => selectMonth(shiftMonth(month, 1)));
  header.append(previous, title, next);
  section.append(header);

  const weekdays = document.createElement("div");
  weekdays.className = "weekdays";
  for (const weekday of ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) {
    const label = document.createElement("span");
    label.textContent = weekday;
    weekdays.append(label);
  }
  section.append(weekdays);

  const days = document.createElement("div");
  days.className = "days";
  const [year, monthNumber] = month.split("-").map(Number);
  const first = new Date(Date.UTC(year, monthNumber - 1, 1));
  const leading = (first.getUTCDay() + 6) % 7;
  const count = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  for (let position = 0; position < 42; position += 1) {
    const dayNumber = position - leading + 1;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "day";
    if (dayNumber < 1 || dayNumber > count) {
      button.classList.add("outside");
      button.disabled = true;
    } else {
      const value = `${month}-${String(dayNumber).padStart(2, "0")}`;
      button.textContent = String(dayNumber);
      button.disabled = value <= todayIso();
      button.classList.toggle("selected", value === selected);
      const dated = state.snapshot?.upcoming.dates.find((entry) => entry.date === value);
      const incomplete = dated?.tasks.filter((task) => !task.done).length ?? 0;
      if (dated && dated.tasks.length > 0) {
        const badge = document.createElement("span");
        badge.className = "count";
        badge.textContent = incomplete ? String(incomplete) : "done";
        button.append(badge);
      }
      button.addEventListener("click", () => selectDate(value));
    }
    days.append(button);
  }
  section.append(days);
  return section;
}

function addForm(
  context: WidgetContext,
  state: ReturnType<typeof initialState>,
  render: () => void,
  initialDate: string,
  knownRevision: string | null,
): HTMLFormElement {
  const form = document.createElement("form");
  form.className = "upcoming-form";
  const dateInput = document.createElement("input");
  dateInput.type = "date";
  dateInput.min = tomorrowIso();
  dateInput.value = initialDate < tomorrowIso() ? tomorrowIso() : initialDate;
  dateInput.setAttribute("aria-label", "Scheduled date");
  const text = document.createElement("input");
  text.placeholder = "Add dated task";
  text.setAttribute("aria-label", "Upcoming task");
  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Add";
  for (const control of [dateInput, text, button]) {
    control.disabled = state.pending !== null || state.snapshot === null;
  }
  form.append(dateInput, text, button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = text.value.trim();
    if (!value || !dateInput.value) return;
    const dated = state.snapshot?.upcoming.dates.find((entry) => entry.date === dateInput.value);
    sendCommand(
      context,
      state,
      "upcoming.add",
      {
        date: dateInput.value,
        revision: dated?.revision ?? knownRevision,
        text: value,
      },
      render,
    );
  });
  return form;
}

function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function tomorrowIso(): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, "0")}-${String(tomorrow.getDate()).padStart(2, "0")}`;
}

function shiftMonth(value: string, offset: number): string {
  const [year, month] = value.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1 + offset, 1));
  return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}`;
}

function styleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = styles;
  return style;
}
