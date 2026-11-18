import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UploadButton } from "./UploadButton";

function openUpload(onUpload: (file: File) => Promise<void>, iconOnly = false) {
  const { container } = render(
    <UploadButton onUpload={onUpload} iconOnly={iconOnly} />,
  );
  fireEvent.click(
    screen.getByRole("button", {
      name: iconOnly ? "Прикрепить документ" : "Загрузить документ",
    }),
  );
  const input = container.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("Поле выбора файла не найдено");
  return input;
}

function chooseFiles(input: HTMLInputElement, ...files: File[]) {
  fireEvent.change(input, { target: { files } });
}

function confirmUpload() {
  fireEvent.click(
    screen.getByRole("button", { name: "Загрузить", exact: true }),
  );
}

function txt(name: string, content = "Учебный текст") {
  return new File([content], name, { type: "text/plain" });
}

describe("UploadButton", () => {
  it("показывает ошибку для неподдерживаемого формата", () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    chooseFiles(
      input,
      new File(["test"], "test.pdf", { type: "application/pdf" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Файл не подходит. Поддерживаются только файлы TXT.",
    );
    expect(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    ).toBeDisabled();
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("отправляет подходящий файл только после подтверждения", async () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    const file = txt("test.txt");
    chooseFiles(input, file);
    expect(screen.getByText("test.txt")).toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
    confirmUpload();
    await waitFor(() => {
      expect(onUpload).toHaveBeenCalledExactlyOnceWith(file);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("не допускает загрузку пустого файла", () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    chooseFiles(input, txt("empty.txt", ""));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Файл пустой. Выберите файл с текстом.",
    );
    expect(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    ).toBeDisabled();
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("не допускает загрузку файла больше 10 МиБ", () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    chooseFiles(
      input,
      new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.txt"),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Размер файла превышает 10 МБ.",
    );
    expect(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    ).toBeDisabled();
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("разрешает файл ровно 10 МиБ", () => {
    const input = openUpload(vi.fn().mockResolvedValue(undefined));
    chooseFiles(
      input,
      new File([new Uint8Array(10 * 1024 * 1024)], "limit.txt"),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    ).toBeEnabled();
  });

  it("сохраняет окно и выбранный файл при ошибке отправки", async () => {
    const onUpload = vi.fn().mockRejectedValue(new Error("Сервер недоступен"));
    const input = openUpload(onUpload);
    chooseFiles(input, txt("test.txt"));
    confirmUpload();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Сервер недоступен",
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("test.txt")).toBeInTheDocument();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Загрузить", exact: true }),
      ).toBeEnabled(),
    );
  });

  it("дополняет очередь при повторном выборе файлов", () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    expect(input).toHaveAttribute("multiple");
    chooseFiles(input, txt("first.txt"));
    chooseFiles(input, txt("second.txt"), txt("third.txt"));
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    for (const name of ["first.txt", "second.txt", "third.txt"]) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("убирает выбранный файл, сохраняя остальные в очереди", () => {
    const input = openUpload(vi.fn().mockResolvedValue(undefined));
    chooseFiles(input, txt("first.txt"), txt("second.txt"));
    fireEvent.click(
      screen.getByRole("button", { name: "Убрать файл «first.txt»" }),
    );
    expect(screen.queryByText("first.txt")).not.toBeInTheDocument();
    expect(screen.getByText("second.txt")).toBeInTheDocument();
  });

  it("передаёт каждый выбранный файл отдельным вызовом", async () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    const first = txt("first.txt");
    const second = txt("second.txt");
    chooseFiles(input, first, second);
    confirmUpload();
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(onUpload).toHaveBeenCalledTimes(2);
    expect(onUpload).toHaveBeenNthCalledWith(1, first);
    expect(onUpload).toHaveBeenNthCalledWith(2, second);
  });

  it("отправляет последовательно и не допускает повторный submit во время очереди", async () => {
    let resolveFirst: () => void = () => {};
    const firstRequest = new Promise<void>((resolve) => {
      resolveFirst = resolve;
    });
    const onUpload = vi
      .fn()
      .mockReturnValueOnce(firstRequest)
      .mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    const first = txt("first.txt");
    const second = txt("second.txt");
    chooseFiles(input, first, second);
    const dialog = screen.getByRole("dialog");
    const form = dialog.querySelector("form");
    if (!form) throw new Error("Форма загрузки не найдена");
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(onUpload).toHaveBeenCalledWith(first);
    expect(
      screen.getByRole("button", { name: /Добавить файлы/ }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Закрыть окно загрузки" }),
    ).toBeDisabled();
    fireEvent(dialog, new Event("cancel", { cancelable: true }));
    expect(dialog).toBeInTheDocument();
    await act(async () => {
      resolveFirst();
    });
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(onUpload).toHaveBeenCalledTimes(2);
    expect(onUpload).toHaveBeenNthCalledWith(2, second);
  });

  it.each([
    {
      reason: "неподдерживаемом формате",
      invalidFile: () => new File(["pdf"], "invalid.pdf"),
    },
    {
      reason: "превышении размера",
      invalidFile: () =>
        new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.txt"),
    },
    {
      reason: "нулевом размере",
      invalidFile: () => txt("empty.txt", ""),
    },
  ])(
    "блокирует всю очередь при $reason и отправляет её после удаления неподходящего файла",
    async ({ invalidFile }) => {
      const onUpload = vi.fn().mockResolvedValue(undefined);
      const input = openUpload(onUpload);
      const valid = txt("valid.txt");
      const invalid = invalidFile();
      chooseFiles(input, valid, invalid);

      const submit = screen.getByRole("button", {
        name: "Загрузить",
        exact: true,
      });
      expect(submit).toBeDisabled();
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(
        screen.getByText("Уберите файлы с ошибками, чтобы загрузить список."),
      ).toBeInTheDocument();

      // Disabled не заменяет защиту обработчика от прямой отправки формы.
      const form = submit.closest("form");
      if (!form) throw new Error("Форма загрузки не найдена");
      fireEvent.submit(form);
      expect(onUpload).not.toHaveBeenCalled();

      fireEvent.click(
        screen.getByRole("button", {
          name: `Убрать файл «${invalid.name}»`,
        }),
      );
      expect(submit).toBeEnabled();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      confirmUpload();

      await waitFor(() =>
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
      );
      expect(onUpload).toHaveBeenCalledExactlyOnceWith(valid);
    },
  );

  it("после частичного успеха повторяет только неуспешный файл", async () => {
    const onUpload = vi
      .fn()
      .mockResolvedValue(undefined)
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error("Ошибка второго файла"))
      .mockResolvedValueOnce(undefined);
    const input = openUpload(onUpload);
    const first = txt("first.txt");
    const second = txt("second.txt");
    const third = txt("third.txt");
    chooseFiles(input, first, second, third);
    confirmUpload();
    await waitFor(() => {
      expect(onUpload).toHaveBeenCalledTimes(3);
      expect(
        screen.getByRole("button", { name: "Загрузить", exact: true }),
      ).toBeEnabled();
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Ошибка второго файла");
    expect(screen.getAllByText("Передан на обработку")).toHaveLength(2);
    confirmUpload();
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(onUpload).toHaveBeenCalledTimes(4);
    expect(onUpload).toHaveBeenNthCalledWith(4, second);
  });

  it("показывает серверный лимит библиотеки отдельно для каждого непринятого файла", async () => {
    const onUpload = vi
      .fn()
      .mockRejectedValue(
        new Error("document_limit_reached: Достигнут лимит документов"),
      );
    const input = openUpload(onUpload);
    chooseFiles(input, txt("first.txt"), txt("second.txt"));
    confirmUpload();
    await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(2));
    expect(onUpload).toHaveBeenCalledTimes(2);
    for (const alert of screen.getAllByRole("alert")) {
      expect(alert).toHaveTextContent("document_limit_reached");
    }
    expect(screen.queryByText("Передан на обработку")).not.toBeInTheDocument();
  });

  it("не объединяет разные файлы с одинаковым именем", async () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    const first = txt("same.txt", "Первый текст");
    const second = txt("same.txt", "Второй текст");
    chooseFiles(input, first, second);
    expect(screen.getAllByText("same.txt")).toHaveLength(2);
    confirmUpload();
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(onUpload).toHaveBeenNthCalledWith(1, first);
    expect(onUpload).toHaveBeenNthCalledWith(2, second);
  });

  it("добавляет файлы через скрепку тем же способом", () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload, true);
    chooseFiles(input, txt("first.txt"), txt("second.txt"));
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(onUpload).not.toHaveBeenCalled();
  });

  it("очищает очередь при закрытии без отправки и новом открытии", () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(onUpload);
    chooseFiles(input, txt("first.txt"));
    fireEvent.click(screen.getByRole("button", { name: "Отмена" }));
    fireEvent.click(screen.getByRole("button", { name: "Загрузить документ" }));
    expect(screen.queryByText("first.txt")).not.toBeInTheDocument();
    expect(onUpload).not.toHaveBeenCalled();
  });
});
