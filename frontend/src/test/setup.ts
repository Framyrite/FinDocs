import "@testing-library/jest-dom";

if (typeof HTMLDialogElement.prototype.showModal !== "function") {
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    writable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
}

if (typeof HTMLDialogElement.prototype.close !== "function") {
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    writable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute("open");
    },
  });
}
