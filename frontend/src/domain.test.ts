import { describe, expect, it } from "vitest";
import { demoWorkspace, prepareAnswer, draftText } from "./domain";

describe("Política de evidencia preliminar", () => {
  it("abstiene sin evidencia y no fabrica citas", () => {
    const data = demoWorkspace();
    const answer = prepareAnswer("¿Qué permiso necesito?", data.cases[0], []);
    expect(answer.outcome).toBe("INSUFFICIENT_EVIDENCE");
    expect(answer.citations).toEqual([]);
  });
  it("solo utiliza documentos del expediente y pasajes literales privados", () => {
    const data = demoWorkspace();
    const answer = prepareAnswer(
      "anticipo y cancelación",
      data.cases[0],
      data.documents,
    );
    expect(answer.citations.length).toBeGreaterThan(0);
    for (const citation of answer.citations) {
      const doc = data.documents.find((d) => d.id === citation.document_id)!;
      expect(doc.case_id).toBe(data.cases[0].id);
      expect(doc.text).toContain(citation.passage);
      expect(citation.origin).toBe("private");
    }
  });
  it("conserva el contexto histórico al editar el expediente", () => {
    const data = demoWorkspace();
    const answer = prepareAnswer("Pregunta", data.cases[0], []);
    data.cases[0].locality = "Otra ciudad";
    expect(answer.context.locality).toBe("Puebla");
  });
  it("marca los datos incompletos y la revisión profesional en borradores", () => {
    const text = draftText("Recinto", demoWorkspace().cases[0], "", "");
    expect(text).toContain("[PENDIENTE:");
    expect(text).toContain("REVISIÓN PROFESIONAL REQUERIDA");
    expect(text).toContain("No tiene fuentes jurídicas asociadas");
  });
});
