// jsdom lacks the layout APIs React Flow relies on.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
class DOMMatrixStub {
  m22 = 1;
  constructor() {}
}
(globalThis as Record<string, unknown>).DOMMatrixReadOnly ??= DOMMatrixStub;
