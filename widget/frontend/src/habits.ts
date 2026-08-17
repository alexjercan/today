import type { WidgetContext, WidgetFrontend } from "@dashboardd/widget-sdk";
import {
  applyUpdate,
  baseStyles,
  header,
  initialState,
  sendCommand,
  setStatus,
} from "./shared.js";

const styles = `${baseStyles}
.rows { flex:1 1 auto; }
.row { grid-template-columns:1fr; }
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
    shadow.replaceChildren(styleElement(), article);
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

function styleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = styles;
  return style;
}
