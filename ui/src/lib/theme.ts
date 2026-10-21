import { useSyncExternalStore } from "react";

export type Theme = "light" | "dark";

const KEY = "spado-theme";
const listeners = new Set<() => void>();
const media = typeof window.matchMedia === "function" ? window.matchMedia("(prefers-color-scheme: dark)") : undefined;

function stored(): Theme | null {
  try {
    const value = localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

let choice = stored();

/** The explicit choice when there is one, otherwise the system appearance. */
function resolve(): Theme {
  return choice ?? (media?.matches ? "dark" : "light");
}

function apply() {
  document.documentElement.dataset.theme = resolve();
  listeners.forEach((listener) => listener());
}

media?.addEventListener("change", apply);
apply();

export function setTheme(theme: Theme) {
  choice = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // Storage unavailable: the choice lasts until reload.
  }
  apply();
}

export function useTheme(): Theme {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => document.documentElement.dataset.theme as Theme,
  );
}

/** Persisted on/off preference, for small view toggles. */
export function readFlag(key: string, fallback: boolean): boolean {
  try {
    const value = localStorage.getItem(key);
    return value === null ? fallback : value === "1";
  } catch {
    return fallback;
  }
}

export function writeFlag(key: string, value: boolean) {
  try {
    localStorage.setItem(key, value ? "1" : "0");
  } catch {
    // Not persisted; the in-memory state still applies.
  }
}
