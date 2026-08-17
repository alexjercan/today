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
  taskCheckbox,
} from "./shared.js";

const styles = `${baseStyles}
.rows { flex:1 1 auto; }
.row { grid-template-columns:1fr auto; }
.add input { width:100%; }
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

function styleElement(): HTMLStyleElement {
  const style = document.createElement("style");
  style.textContent = styles;
  return style;
}
