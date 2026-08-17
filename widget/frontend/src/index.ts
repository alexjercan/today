import type { WidgetContext, WidgetFrontend, WidgetPresentation } from "@dashboardd/widget-sdk";

type Task = { index: number; text: string; done: boolean };
type Habit = { name: string; done: boolean };
type Food = {
  index: number;
  name: string;
  protein: number;
  carbs: number;
  fat: number;
};
type DatedTasks = { date: string; revision: string; tasks: Task[] };
type FoodCandidate = { id: string; name: string; unit: "g" | "pc" };
type FoodSearchResult = {
  kind: "food.search";
  query: string;
  candidates: FoodCandidate[];
};
type CommandResult = {
  command_id: string;
  status: "succeeded" | "failed";
  error?: { code: string; message: string };
  result?: FoodSearchResult;
};
type Snapshot = {
  schema_version: 1;
  today: {
    date: string;
    title: string;
    revision: string;
    tasks: Task[];
    habits: Habit[];
    foods: Food[];
    macros: { protein: number; carbs: number; fat: number; calories: number };
    weight: number | null;
  };
  upcoming: {
    next: Array<Task & { date: string; revision: string }>;
    dates: DatedTasks[];
  };
  weight_history: Array<{ date: string; value: number }>;
  command_result: CommandResult | null;
};

type ViewState = {
  snapshot: Snapshot | null;
  pending: string | null;
  error: string | null;
  destroyed: boolean;
};

const baseStyles = `
:host { display:block; min-width:0; height:100%; color:var(--dashboardd-color-text); font-family:var(--dashboardd-font-mono); }
* { box-sizing:border-box; }
article { height:100%; min-height:0; display:flex; flex-direction:column; gap:8px; padding:10px; overflow:hidden; }
header { display:flex; align-items:start; justify-content:space-between; gap:8px; flex:0 0 auto; }
h2 { margin:0; color:var(--dashboardd-color-text-bright); font-size:15px; line-height:1.2; }
.date { color:var(--dashboardd-color-text-muted); font-size:12px; }
.status { min-height:16px; color:var(--dashboardd-color-danger); font-size:11px; text-align:right; }
.rows { min-height:0; overflow:auto; scrollbar-width:auto; scrollbar-color:var(--dashboardd-color-border) var(--dashboardd-color-surface); }
.row { display:grid; align-items:center; gap:7px; min-height:30px; border-bottom:1px solid color-mix(in srgb, var(--dashboardd-color-border) 28%, transparent); font-size:14px; }
.row:last-child { border-bottom:0; }
.row label { min-width:0; display:flex; align-items:center; gap:8px; cursor:pointer; }
.row .text { min-width:0; overflow-wrap:anywhere; }
input, button { min-height:32px; border:1px solid var(--dashboardd-color-border); border-radius:4px; background:var(--dashboardd-color-surface); color:var(--dashboardd-color-text); font:inherit; font-size:13px; }
input { min-width:0; padding:5px 7px; }
button { padding:4px 9px; cursor:pointer; }
button:hover:not(:disabled), button:focus-visible { border-color:var(--dashboardd-color-accent); color:var(--dashboardd-color-text-bright); }
button:disabled, input:disabled { cursor:wait; opacity:.6; }
input[type=checkbox] { width:18px; height:18px; min-height:18px; accent-color:var(--dashboardd-color-accent); cursor:pointer; flex:0 0 auto; }
form { display:flex; gap:6px; flex:0 0 auto; }
form input:first-of-type { flex:1 1 auto; }
.empty { padding:12px 2px; color:var(--dashboardd-color-text-muted); font-size:13px; }
.remove { display:none; min-height:26px; padding:2px 7px; color:var(--dashboardd-color-danger); }
:host([data-presentation=focus]) .remove { display:inline-block; }
.metric { color:var(--dashboardd-color-text-bright); font-variant-numeric:tabular-nums; }
`;

function initialState(): ViewState {
  return { snapshot: null, pending: null, error: null, destroyed: false };
}

function applyUpdate(state: ViewState, payload: unknown): boolean {
  const snapshot = parseSnapshot(payload);
  if (snapshot === null) return false;
  if (
    state.pending !== null &&
    snapshot.command_result?.command_id === state.pending
  ) {
    state.pending = null;
    state.error =
      snapshot.command_result.status === "failed"
        ? (snapshot.command_result.error?.message ?? "Write failed")
        : null;
  }
  state.snapshot = snapshot;
  return true;
}

function sendCommand(
  context: WidgetContext,
  state: ViewState,
  action: string,
  data: Record<string, unknown>,
  render: () => void,
): void {
  if (state.pending !== null) return;
  const commandId = createId();
  state.pending = commandId;
  state.error = null;
  render();
  void context
    .send({ command_id: commandId, action, data })
    .catch((error: unknown) => {
      if (state.destroyed || state.pending !== commandId) return;
      state.pending = null;
      state.error = error instanceof Error ? error.message : "Could not send";
      render();
    });
}

function header(title: string, snapshot: Snapshot | null): HTMLElement {
  const element = document.createElement("header");
  const heading = document.createElement("div");
  const h2 = document.createElement("h2");
  h2.textContent = title;
  const day = document.createElement("div");
  day.className = "date";
  day.textContent = snapshot ? formatDate(snapshot.today.date) : "Loading...";
  heading.append(h2, day);
  const status = document.createElement("div");
  status.className = "status";
  element.append(heading, status);
  return element;
}

function setStatus(root: ParentNode, state: ViewState): void {
  const status = required<HTMLElement>(root, ".status");
  status.textContent = state.pending ? "Saving..." : (state.error ?? "");
}

function taskCheckbox(
  task: Task,
  disabled: boolean,
  toggle: () => void,
): HTMLInputElement {
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = task.done;
  checkbox.disabled = disabled;
  checkbox.setAttribute("aria-label", `Toggle ${task.text}`);
  checkbox.addEventListener("change", toggle);
  return checkbox;
}

function removeButton(label: string, remove: () => void): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "remove";
  button.textContent = "Remove";
  button.setAttribute("aria-label", `Remove ${label}`);
  button.addEventListener("click", () => {
    if (globalThis.confirm(`Remove ${label}?`)) remove();
  });
  return button;
}

function formatDate(value: string, options?: Intl.DateTimeFormatOptions): string {
  const parsed = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
    ...options,
  }).format(parsed);
}

function required<T extends Element>(root: ParentNode, selector: string): T {
  const element = root.querySelector<T>(selector);
  if (!element) throw new Error(`missing widget element: ${selector}`);
  return element;
}

function parseSnapshot(value: unknown): Snapshot | null {
  if (!isRecord(value) || value.schema_version !== 1) return null;
  const today = value.today;
  const upcoming = value.upcoming;
  if (
    !isRecord(today) ||
    typeof today.date !== "string" ||
    typeof today.title !== "string" ||
    typeof today.revision !== "string" ||
    !Array.isArray(today.tasks) ||
    !Array.isArray(today.habits) ||
    !Array.isArray(today.foods) ||
    !isMacros(today.macros) ||
    !(today.weight === null || isFiniteNumber(today.weight)) ||
    !isRecord(upcoming) ||
    !Array.isArray(upcoming.next) ||
    !Array.isArray(upcoming.dates) ||
    !Array.isArray(value.weight_history)
  )
    return null;
  const tasks = today.tasks.map(parseTask);
  const habits = today.habits.map(parseHabit);
  const foods = today.foods.map(parseFood);
  const next = upcoming.next.map(parseDatedTask);
  const dates = upcoming.dates.map(parseDatedTasks);
  const history = value.weight_history.map(parseWeight);
  if (
    tasks.includes(null) ||
    habits.includes(null) ||
    foods.includes(null) ||
    next.includes(null) ||
    dates.includes(null) ||
    history.includes(null)
  )
    return null;
  const commandResult = parseCommandResult(value.command_result);
  if (value.command_result !== null && commandResult === null) return null;
  return {
    schema_version: 1,
    today: {
      date: today.date,
      title: today.title,
      revision: today.revision,
      tasks: tasks as Task[],
      habits: habits as Habit[],
      foods: foods as Food[],
      macros: today.macros,
      weight: today.weight as number | null,
    },
    upcoming: {
      next: next as Array<Task & { date: string; revision: string }>,
      dates: dates as DatedTasks[],
    },
    weight_history: history as Array<{ date: string; value: number }>,
    command_result: commandResult,
  };
}

function parseTask(value: unknown): Task | null {
  if (
    !isRecord(value) ||
    !Number.isInteger(value.index) ||
    (value.index as number) < 1 ||
    typeof value.text !== "string" ||
    typeof value.done !== "boolean"
  )
    return null;
  return { index: value.index as number, text: value.text, done: value.done };
}

function parseHabit(value: unknown): Habit | null {
  return isRecord(value) &&
    typeof value.name === "string" &&
    typeof value.done === "boolean"
    ? { name: value.name, done: value.done }
    : null;
}

function parseFood(value: unknown): Food | null {
  if (
    !isRecord(value) ||
    !Number.isInteger(value.index) ||
    typeof value.name !== "string" ||
    !isFiniteNumber(value.protein) ||
    !isFiniteNumber(value.carbs) ||
    !isFiniteNumber(value.fat)
  )
    return null;
  return {
    index: value.index as number,
    name: value.name,
    protein: value.protein,
    carbs: value.carbs,
    fat: value.fat,
  };
}

function parseDatedTask(value: unknown): (Task & { date: string; revision: string }) | null {
  const task = parseTask(value);
  return task && isRecord(value) && typeof value.date === "string" && typeof value.revision === "string"
    ? { ...task, date: value.date, revision: value.revision }
    : null;
}

function parseDatedTasks(value: unknown): DatedTasks | null {
  if (
    !isRecord(value) ||
    typeof value.date !== "string" ||
    typeof value.revision !== "string" ||
    !Array.isArray(value.tasks)
  )
    return null;
  const tasks = value.tasks.map(parseTask);
  return tasks.includes(null)
    ? null
    : { date: value.date, revision: value.revision, tasks: tasks as Task[] };
}

function parseWeight(value: unknown): { date: string; value: number } | null {
  return isRecord(value) && typeof value.date === "string" && isFiniteNumber(value.value)
    ? { date: value.date, value: value.value }
    : null;
}

function parseCommandResult(value: unknown): CommandResult | null {
  if (value === null) return null;
  if (
    !isRecord(value) ||
    typeof value.command_id !== "string" ||
    (value.status !== "succeeded" && value.status !== "failed")
  )
    return null;
  let error: { code: string; message: string } | undefined;
  if (value.error !== undefined) {
    if (!isRecord(value.error) || typeof value.error.code !== "string" || typeof value.error.message !== "string") return null;
    error = { code: value.error.code, message: value.error.message };
  }
  let result: FoodSearchResult | undefined;
  if (value.result !== undefined) {
    result = parseFoodSearchResult(value.result) ?? undefined;
    if (result === undefined) return null;
  }
  return { command_id: value.command_id, status: value.status, error, result };
}

function parseFoodSearchResult(value: unknown): FoodSearchResult | null {
  if (
    !isRecord(value) ||
    value.kind !== "food.search" ||
    typeof value.query !== "string" ||
    !Array.isArray(value.candidates)
  )
    return null;
  const candidates = value.candidates.map(parseFoodCandidate);
  return candidates.includes(null)
    ? null
    : {
        kind: "food.search",
        query: value.query,
        candidates: candidates as FoodCandidate[],
      };
}

function parseFoodCandidate(value: unknown): FoodCandidate | null {
  return isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    (value.unit === "g" || value.unit === "pc")
    ? { id: value.id, name: value.name, unit: value.unit }
    : null;
}

function isMacros(value: unknown): value is Snapshot["today"]["macros"] {
  return isRecord(value) && isFiniteNumber(value.protein) && isFiniteNumber(value.carbs) && isFiniteNumber(value.fat) && Number.isInteger(value.calories);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function createId(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

const tasksStyles = `${baseStyles}
.rows { flex:1 1 auto; }
.row { grid-template-columns:1fr auto; }
.add input { width:100%; }
`;

function mountTasks(
  container: HTMLElement,
  context: WidgetContext,
): WidgetFrontend {
  const shadow = container.attachShadow({ mode: "open" });
  const state = initialState();

  const render = (): void => {
    if (state.destroyed) return;
    const article = document.createElement("article");
    article.append(header("Tasks", state.snapshot));
    const rows = document.createElement("div");
    rows.className = "rows";
    const tasks = state.snapshot?.today.tasks ?? [];
    if (tasks.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = state.snapshot ? "No tasks today" : "Loading tasks...";
      rows.append(empty);
    }
    for (const task of tasks) {
      const row = document.createElement("div");
      row.className = "row";
      const label = document.createElement("label");
      const text = document.createElement("span");
      text.className = "text";
      text.textContent = task.text;
      const toggle = (): void => {
        const today = state.snapshot?.today;
        if (!today) return;
        sendCommand(
          context,
          state,
          "task.toggle",
          { date: today.date, revision: today.revision, index: task.index },
          render,
        );
      };
      label.append(taskCheckbox(task, state.pending !== null, toggle), text);
      const remove = removeButton(task.text, () => {
        const today = state.snapshot?.today;
        if (!today) return;
        sendCommand(
          context,
          state,
          "task.remove",
          { date: today.date, revision: today.revision, index: task.index },
          render,
        );
      });
      remove.disabled = state.pending !== null;
      row.append(label, remove);
      rows.append(row);
    }
    article.append(rows);

    const form = document.createElement("form");
    form.className = "add";
    const input = document.createElement("input");
    input.name = "task";
    input.placeholder = "Add task";
    input.setAttribute("aria-label", "New task");
    input.disabled = state.pending !== null || state.snapshot === null;
    const button = document.createElement("button");
    button.type = "submit";
    button.textContent = "Add";
    button.disabled = input.disabled;
    form.append(input, button);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const today = state.snapshot?.today;
      const text = input.value.trim();
      if (!today || !text) return;
      sendCommand(
        context,
        state,
        "task.add",
        { date: today.date, revision: today.revision, text },
        render,
      );
    });
    article.append(form);
    shadow.replaceChildren(tasksStyleElement(), article);
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

function tasksStyleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = tasksStyles;
  return style;
}

const habitsStyles = `${baseStyles}
.rows { flex:1 1 auto; }
.row { grid-template-columns:1fr; }
`;

function mountHabits(
  container: HTMLElement,
  context: WidgetContext,
): WidgetFrontend {
  const shadow = container.attachShadow({ mode: "open" });
  const state = initialState();
  const render = (): void => {
    if (state.destroyed) return;
    const article = document.createElement("article");
    article.append(header("Habits", state.snapshot));
    const rows = document.createElement("div");
    rows.className = "rows";
    const habits = state.snapshot?.today.habits ?? [];
    if (habits.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = state.snapshot ? "No habits configured" : "Loading habits...";
      rows.append(empty);
    }
    for (const habit of habits) {
      const row = document.createElement("div");
      row.className = "row";
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = habit.done;
      checkbox.disabled = state.pending !== null;
      checkbox.setAttribute("aria-label", `Toggle ${habit.name}`);
      checkbox.addEventListener("change", () => {
        const today = state.snapshot?.today;
        if (!today) return;
        sendCommand(
          context,
          state,
          "habit.toggle",
          { date: today.date, revision: today.revision, name: habit.name },
          render,
        );
      });
      const name = document.createElement("span");
      name.className = "text";
      name.textContent = habit.name;
      label.append(checkbox, name);
      row.append(label);
      rows.append(row);
    }
    article.append(rows);
    shadow.replaceChildren(habitsStyleElement(), article);
    setStatus(shadow, state);
  };
  render();
  return {
    update(payload: unknown): void {
      if (applyUpdate(state, payload)) render();
    },
    destroy(): void {
      state.destroyed = true;
      shadow.replaceChildren();
    },
  };
}

function habitsStyleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = habitsStyles;
  return style;
}

const macrosStyles = `${baseStyles}
article { gap:3px; padding:7px 10px; }
header { align-items:center; }
header > div { display:flex; align-items:baseline; gap:8px; }
header .status { min-height:0; }
.totals { display:grid; grid-template-columns:repeat(4, 1fr); gap:5px; }
.total { min-width:0; text-align:center; }
.total .metric { display:block; font-size:14px; }
.total .label { color:var(--dashboardd-color-text-muted); font-size:9px; text-transform:uppercase; }
.food-form { display:grid; grid-template-columns:minmax(100px, 1fr) minmax(76px, .35fr) auto; }
.food-form input { width:100%; }
.food-form input, .food-form button { min-height:27px; padding-block:2px; }
.food-picker { position:relative; min-width:0; }
.suggestions { position:absolute; z-index:2; left:0; right:0; bottom:calc(100% + 4px); max-height:58px; overflow:auto; border:1px solid var(--dashboardd-color-border); border-radius:4px; background:var(--dashboardd-color-surface); box-shadow:0 8px 18px color-mix(in srgb, var(--dashboardd-color-canvas) 70%, transparent); }
.suggestions:empty { display:none; }
.suggestion { width:100%; min-height:27px; display:flex; justify-content:space-between; gap:8px; border:0; border-radius:0; text-align:left; }
.suggestion.active { background:color-mix(in srgb, var(--dashboardd-color-accent) 16%, var(--dashboardd-color-surface)); color:var(--dashboardd-color-text-bright); }
.suggestion .unit { color:var(--dashboardd-color-text-muted); }
.quantity { position:relative; min-width:0; }
.quantity input { padding-right:28px; }
.quantity .unit { position:absolute; right:7px; top:50%; transform:translateY(-50%); color:var(--dashboardd-color-text-muted); font-size:11px; pointer-events:none; }
.foods { display:none; min-height:0; flex:1 1 auto; }
.foods .row { grid-template-columns:minmax(100px, 1fr) auto auto; }
.food-macros { color:var(--dashboardd-color-text-muted); font-size:12px; }
:host([data-presentation=focus]) article { gap:10px; padding:10px; }
:host([data-presentation=focus]) .food-form input,
:host([data-presentation=focus]) .food-form button { min-height:32px; padding-block:4px; }
:host([data-presentation=focus]) .suggestions { max-height:220px; }
:host([data-presentation=focus]) .foods { display:block; }
`;

type MacrosUiState = {
  query: string;
  amount: string;
  selected: FoodCandidate | null;
  candidates: FoodCandidate[];
  highlighted: number;
  searchCommandId: string | null;
  focus: "food" | "amount" | null;
};

function mountMacros(
  container: HTMLElement,
  context: WidgetContext,
): WidgetFrontend {
  const shadow = container.attachShadow({ mode: "open" });
  const state = initialState();
  const ui: MacrosUiState = {
    query: "",
    amount: "",
    selected: null,
    candidates: [],
    highlighted: 0,
    searchCommandId: null,
    focus: null,
  };
  let searchTimer: number | undefined;

  const render = (): void => {
    if (state.destroyed) return;
    const article = document.createElement("article");
    article.append(header("Macros", state.snapshot));
    const totals = document.createElement("div");
    totals.className = "totals";
    const macros = state.snapshot?.today.macros;
    for (const [label, value, unit] of [
      ["Protein", macros?.protein, "g"],
      ["Carbs", macros?.carbs, "g"],
      ["Fat", macros?.fat, "g"],
      ["Calories", macros?.calories, ""],
    ] as const) {
      const total = document.createElement("div");
      total.className = "total";
      const metric = document.createElement("span");
      metric.className = "metric";
      metric.textContent = value === undefined ? "--" : `${format(value)}${unit}`;
      const name = document.createElement("span");
      name.className = "label";
      name.textContent = label;
      total.append(metric, name);
      totals.append(total);
    }
    article.append(totals);

    const foods = document.createElement("div");
    foods.className = "foods rows";
    const entries = state.snapshot?.today.foods ?? [];
    if (entries.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "No food logged";
      foods.append(empty);
    }
    for (const food of entries) {
      const row = document.createElement("div");
      row.className = "row";
      const name = document.createElement("span");
      name.className = "text";
      name.textContent = food.name;
      const values = document.createElement("span");
      values.className = "food-macros";
      values.textContent = `${format(food.protein)}P ${format(food.carbs)}C ${format(food.fat)}F`;
      const remove = removeButton(food.name, () => {
        const today = state.snapshot?.today;
        if (!today) return;
        sendCommand(
          context,
          state,
          "food.remove",
          { date: today.date, revision: today.revision, index: food.index },
          render,
        );
      });
      remove.disabled = state.pending !== null;
      row.append(name, values, remove);
      foods.append(row);
    }
    article.append(foods, foodForm(context, state, ui, render, scheduleSearch));
    shadow.replaceChildren(macrosStyleElement(), article);
    setStatus(shadow, state);
    if (ui.focus !== null) {
      const selector = ui.focus === "food" ? "input[name=food]" : "input[name=amount]";
      queueMicrotask(() => {
        const input = shadow.querySelector<HTMLInputElement>(selector);
        input?.focus();
        if (input?.type === "text") {
          input.setSelectionRange(input.value.length, input.value.length);
        }
      });
    }
  };

  const scheduleSearch = (): void => {
    if (searchTimer !== undefined) window.clearTimeout(searchTimer);
    if (ui.query.trim().length < 2) return;
    const query = ui.query.trim();
    searchTimer = window.setTimeout(() => {
      const commandId = createId();
      ui.searchCommandId = commandId;
      void context
        .send({
          command_id: commandId,
          action: "food.search",
          data: { query },
        })
        .catch((error: unknown) => {
          if (state.destroyed || ui.searchCommandId !== commandId) return;
          ui.searchCommandId = null;
          state.error = error instanceof Error ? error.message : "Could not search";
          render();
        });
    }, 200);
  };

  render();
  return {
    update(payload: unknown): void {
      const pending = state.pending;
      if (!applyUpdate(state, payload)) return;
      const result = state.snapshot?.command_result;
      if (result?.command_id === ui.searchCommandId) {
        ui.searchCommandId = null;
        if (
          result.status === "succeeded" &&
          result.result?.kind === "food.search" &&
          result.result.query === ui.query.trim()
        ) {
          ui.candidates = result.result.candidates;
          ui.highlighted = 0;
        } else if (result.status === "failed") {
          state.error = result.error?.message ?? "Food search failed";
        }
      }
      if (pending !== null && result?.command_id === pending && result.status === "succeeded") {
        ui.query = "";
        ui.amount = "";
        ui.selected = null;
        ui.candidates = [];
        ui.focus = "food";
      }
      render();
    },
    setPresentation(presentation: WidgetPresentation): void {
      shadow.host.setAttribute("data-presentation", presentation);
    },
    destroy(): void {
      state.destroyed = true;
      if (searchTimer !== undefined) window.clearTimeout(searchTimer);
      shadow.replaceChildren();
    },
  };
}

function foodForm(
  context: WidgetContext,
  state: ReturnType<typeof initialState>,
  ui: MacrosUiState,
  render: () => void,
  scheduleSearch: () => void,
): HTMLFormElement {
  const form = document.createElement("form");
  form.className = "food-form";

  const picker = document.createElement("div");
  picker.className = "food-picker";
  const food = document.createElement("input");
  food.name = "food";
  food.type = "text";
  food.placeholder = "Food";
  food.autocomplete = "off";
  food.value = ui.query;
  food.disabled = state.pending !== null || state.snapshot === null;
  food.setAttribute("role", "combobox");
  food.setAttribute("aria-label", "Food");
  food.setAttribute("aria-autocomplete", "list");
  food.setAttribute("aria-expanded", String(ui.candidates.length > 0));
  food.setAttribute("aria-controls", "food-suggestions");
  const suggestions = document.createElement("div");
  suggestions.id = "food-suggestions";
  suggestions.className = "suggestions";
  suggestions.setAttribute("role", "listbox");

  const selectCandidate = (candidate: FoodCandidate): void => {
    ui.selected = candidate;
    ui.query = candidate.name;
    ui.amount = candidate.unit === "pc" ? "1" : "100";
    ui.candidates = [];
    ui.focus = "amount";
    render();
  };
  ui.candidates.forEach((candidate, index) => {
    const option = document.createElement("button");
    option.type = "button";
    option.className = `suggestion${index === ui.highlighted ? " active" : ""}`;
    option.setAttribute("role", "option");
    option.setAttribute("aria-selected", String(index === ui.highlighted));
    const name = document.createElement("span");
    name.textContent = candidate.name;
    const unit = document.createElement("span");
    unit.className = "unit";
    unit.textContent = candidate.unit === "pc" ? "pieces" : "grams";
    option.append(name, unit);
    option.addEventListener("mousedown", (event) => event.preventDefault());
    option.addEventListener("click", () => selectCandidate(candidate));
    suggestions.append(option);
  });
  food.addEventListener("input", () => {
    ui.query = food.value;
    ui.selected = null;
    ui.candidates = [];
    ui.highlighted = 0;
    ui.focus = "food";
    suggestions.replaceChildren();
    food.setAttribute("aria-expanded", "false");
    scheduleSearch();
  });
  food.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" && ui.candidates.length > 0) {
      event.preventDefault();
      ui.highlighted = (ui.highlighted + 1) % ui.candidates.length;
      ui.focus = "food";
      render();
    } else if (event.key === "ArrowUp" && ui.candidates.length > 0) {
      event.preventDefault();
      ui.highlighted =
        (ui.highlighted - 1 + ui.candidates.length) % ui.candidates.length;
      ui.focus = "food";
      render();
    } else if (event.key === "Enter" && ui.candidates.length > 0) {
      event.preventDefault();
      selectCandidate(ui.candidates[ui.highlighted]);
    } else if (event.key === "Escape") {
      ui.candidates = [];
      suggestions.replaceChildren();
      food.setAttribute("aria-expanded", "false");
    }
  });
  picker.append(food, suggestions);

  const quantity = document.createElement("div");
  quantity.className = "quantity";
  const amount = document.createElement("input");
  amount.name = "amount";
  amount.type = "number";
  amount.step = "any";
  amount.min = "0";
  amount.placeholder = "Quantity";
  amount.value = ui.amount;
  amount.disabled =
    state.pending !== null || state.snapshot === null || ui.selected === null;
  amount.setAttribute("aria-label", "Quantity");
  amount.addEventListener("input", () => {
    ui.amount = amount.value;
    ui.focus = "amount";
  });
  const unit = document.createElement("span");
  unit.className = "unit";
  unit.textContent = ui.selected?.unit === "pc" ? "pc" : ui.selected ? "g" : "";
  quantity.append(amount, unit);

  const numericAmount = Number(ui.amount);
  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Add";
  button.disabled =
    state.pending !== null ||
    state.snapshot === null ||
    ui.selected === null ||
    !Number.isFinite(numericAmount) ||
    numericAmount <= 0;

  form.append(picker, quantity, button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const today = state.snapshot?.today;
    const selected = ui.selected;
    const value = Number(ui.amount);
    if (!today || !selected || !Number.isFinite(value) || value <= 0) return;
    sendCommand(
      context,
      state,
      "food.add",
      {
        date: today.date,
        revision: today.revision,
        food_id: selected.id,
        amount: value,
      },
      render,
    );
  });
  return form;
}

function format(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function macrosStyleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = macrosStyles;
  return style;
}

const weightStyles = `${baseStyles}
article { justify-content:space-between; gap:5px; }
header .date { display:none; }
.current { flex:1 1 auto; display:flex; align-items:center; justify-content:center; min-height:0; }
.value { border:0; background:transparent; color:var(--dashboardd-color-text-bright); font-size:22px; font-weight:700; white-space:nowrap; }
.weight-form { display:grid; grid-template-columns:1fr auto; }
.history { display:none; min-height:0; flex:1 1 auto; }
.history .row { grid-template-columns:1fr auto; }
.change { color:var(--dashboardd-color-secondary); font-size:13px; }
:host([data-presentation=focus]) header .date { display:block; }
:host([data-presentation=focus]) .current { flex:0 0 auto; justify-content:flex-start; }
:host([data-presentation=focus]) .value { font-size:30px; }
:host([data-presentation=focus]) .history { display:block; }
`;

function mountWeight(
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
    shadow.replaceChildren(weightStyleElement(), article);
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

function weightStyleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = weightStyles;
  return style;
}

const upcomingStyles = `${baseStyles}
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

function mountUpcoming(
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
    shadow.replaceChildren(upcomingStyleElement(), article);
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

function upcomingStyleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = upcomingStyles;
  return style;
}


export function mount(
  container: HTMLElement,
  context: WidgetContext,
): WidgetFrontend {
  let frontend: WidgetFrontend;
  switch (context.variantId) {
    case "tasks":
      frontend = mountTasks(container, context);
      break;
    case "habits":
      frontend = mountHabits(container, context);
      break;
    case "macros":
      frontend = mountMacros(container, context);
      break;
    case "weight":
      frontend = mountWeight(container, context);
      break;
    case "upcoming":
      frontend = mountUpcoming(container, context);
      break;
    default:
      throw new Error(`unsupported Today variant: ${context.variantId}`);
  }
  void context
    .send({ command_id: createId(), action: "refresh", data: {} })
    .catch(() => {});
  return frontend;
}
