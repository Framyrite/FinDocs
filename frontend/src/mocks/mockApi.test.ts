import { describe, it, expect } from "vitest";
import { mockApi } from "./mockApi";
import { mockDocuments } from "./data";

describe("mockApi askQuestion", () => {
  const demoId = mockDocuments[0].id; // ID "Лекции 3. Облигации"

  it("возвращает источник, если демо-док выбран явно", async () => {
    const answer = await mockApi.askQuestion({
      question: "Что?",
      document_ids: [demoId],
    });
    expect(answer.status).toBe("answered");
    expect(answer.sources[0].document_id).toBe(demoId);
  });

  it("возвращает insufficient_info, если демо-док не выбран", async () => {
    // Передаем рандомный ID (не демо)
    const answer = await mockApi.askQuestion({
      question: "Что?",
      document_ids: ["random-id"],
    });
    expect(answer.status).toBe("insufficient_info");
    expect(answer.sources).toHaveLength(0);
  });

  it("не подменяет источник для файла с похожим названием", async () => {
    // Загружаем новый файл с "Облигации" в названии
    const file = new File(["test"], "Мои Облигации.txt", {
      type: "text/plain",
    });
    const newDoc = await mockApi.uploadDocument(file);

    // Меняем статус на ready (имитация)
    await mockApi.getDocumentById(newDoc.id); // uploaded -> processing
    await mockApi.getDocumentById(newDoc.id); // processing -> ready

    // Спрашиваем по нему
    const answer = await mockApi.askQuestion({
      question: "Что?",
      document_ids: [newDoc.id],
    });

    // Должен быть insufficient_info, так как это не оригинальная лекция
    expect(answer.status).toBe("insufficient_info");
  });
});
