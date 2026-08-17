import type { WidgetContext } from "@dashboardd/widget-sdk";

export type Task = { index: number; text: string; done: boolean };
export type Habit = { name: string; done: boolean };
export type Food = {
  index: number;
  name: string;
  protein: number;
  carbs: number;
  fat: number;
};
export type DatedTasks = { date: string; revision: string; tasks: Task[] };
export type CommandResult = {
  command_id: string;
  status: "succeeded" | "failed";
  error?: { code: string; message: string };
};
export type Snapshot = {
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

export type ViewState = {
  snapshot: Snapshot | null;
  pending: string | null;
  error: string | null;
  destroyed: boolean;
};

export const baseStyles = `
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

export function initialState(): ViewState {
  return { snapshot: null, pending: null, error: null, destroyed: false };
}

export function applyUpdate(state: ViewState, payload: unknown): boolean {
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

export function sendCommand(
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

export function header(title: string, snapshot: Snapshot | null): HTMLElement {
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

export function setStatus(root: ParentNode, state: ViewState): void {
  const status = required<HTMLElement>(root, ".status");
  status.textContent = state.pending ? "Saving..." : (state.error ?? "");
}

export function taskCheckbox(
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

export function removeButton(label: string, remove: () => void): HTMLButtonElement {
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

export function formatDate(value: string, options?: Intl.DateTimeFormatOptions): string {
  const parsed = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
    ...options,
  }).format(parsed);
}

export function required<T extends Element>(root: ParentNode, selector: string): T {
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
  return { command_id: value.command_id, status: value.status, error };
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
