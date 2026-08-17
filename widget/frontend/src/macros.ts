import type {
  WidgetContext,
  WidgetFrontend,
  WidgetPresentation,
} from "@dashboardd/widget-sdk";
import {
  applyUpdate,
  baseStyles,
  header,
  initialState,
  removeButton,
  sendCommand,
  setStatus,
} from "./shared.js";

const styles = `${baseStyles}
article { gap:6px; }
header { align-items:center; }
.totals { display:grid; grid-template-columns:repeat(4, 1fr); gap:5px; }
.total { min-width:0; text-align:center; }
.total .metric { display:block; font-size:15px; }
.total .label { color:var(--dashboardd-color-text-muted); font-size:10px; text-transform:uppercase; }
.food-form { display:grid; grid-template-columns:minmax(90px, 1fr) repeat(3, minmax(42px, .35fr)) auto; }
.food-form input { width:100%; }
.foods { display:none; min-height:0; flex:1 1 auto; }
.foods .row { grid-template-columns:minmax(100px, 1fr) auto auto; }
.food-macros { color:var(--dashboardd-color-text-muted); font-size:12px; }
:host([data-presentation=focus]) article { gap:10px; }
:host([data-presentation=focus]) .foods { display:block; }
`;

export function mount(
  container: HTMLElement,
  context: WidgetContext,
): WidgetFrontend {
  const shadow = container.attachShadow({ mode: "open" });
  const state = initialState();
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
    article.append(foods, foodForm(context, state, render));
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

function foodForm(
  context: WidgetContext,
  state: ReturnType<typeof initialState>,
  render: () => void,
): HTMLFormElement {
  const form = document.createElement("form");
  form.className = "food-form";
  const fields: Array<[string, string, string]> = [
    ["food", "Food", "text"],
    ["protein", "P", "number"],
    ["carbs", "C", "number"],
    ["fat", "F", "number"],
  ];
  const inputs = new Map<string, HTMLInputElement>();
  for (const [name, placeholder, type] of fields) {
    const input = document.createElement("input");
    input.name = name;
    input.type = type;
    input.placeholder = placeholder;
    input.setAttribute("aria-label", name);
    if (type === "number") input.step = "any";
    input.disabled = state.pending !== null || state.snapshot === null;
    inputs.set(name, input);
    form.append(input);
  }
  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Add";
  button.disabled = state.pending !== null || state.snapshot === null;
  form.append(button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const today = state.snapshot?.today;
    const food = inputs.get("food")?.value.trim() ?? "";
    const protein = inputs.get("protein")?.value.trim() ?? "";
    const carbs = inputs.get("carbs")?.value.trim() ?? "";
    const fat = inputs.get("fat")?.value.trim() ?? "";
    if (!today || !food || !protein || !carbs || !fat) return;
    sendCommand(
      context,
      state,
      "food.add",
      {
        date: today.date,
        revision: today.revision,
        row: `${food},${protein},${carbs},${fat}`,
      },
      render,
    );
  });
  return form;
}

function format(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function styleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = styles;
  return style;
}
