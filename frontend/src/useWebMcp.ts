import { useEffect, useRef } from "react";
import type { Case } from "./types";

type ModelContext = {
  registerTool: (
    tool: {
      name: string;
      title: string;
      description: string;
      inputSchema: object;
      annotations: object;
      execute: (input: unknown) => Promise<object>;
    },
    options: { signal: AbortSignal },
  ) => void | Promise<void>;
};
/** Optional browser capability; unsupported browsers keep the regular interface. */
export function useWebMcp(
  cases: Case[],
  prepare: (caseId: string, question: string) => void,
) {
  const latest = useRef({ cases, prepare });
  latest.current = { cases, prepare };
  useEffect(() => {
    const context = (document as Document & { modelContext?: ModelContext })
      .modelContext;
    if (!context?.registerTool) return;
    const lifecycle = new AbortController();
    try {
      const registration = context.registerTool(
        {
          name: "start_juridia_consultation",
          title: "Preparar una consulta",
          description:
            "Abre el asistente con un expediente existente y una pregunta. No envía la consulta ni genera una respuesta.",
          inputSchema: {
            type: "object",
            properties: {
              case_id: { type: "string" },
              question: { type: "string", minLength: 1, maxLength: 4000 },
            },
            required: ["case_id", "question"],
            additionalProperties: false,
          },
          annotations: { readOnlyHint: false, untrustedContentHint: true },
          async execute(input) {
            if (!input || typeof input !== "object")
              throw new Error("Datos no válidos.");
            const { case_id, question } = input as Record<string, unknown>;
            if (
              typeof case_id !== "string" ||
              typeof question !== "string" ||
              !question.trim() ||
              question.length > 4000 ||
              !latest.current.cases.some((c) => c.id === case_id)
            )
              throw new Error("Expediente o pregunta no válidos.");
            latest.current.prepare(case_id, question);
            await new Promise<void>((resolve) =>
              requestAnimationFrame(() =>
                requestAnimationFrame(() => resolve()),
              ),
            );
            return { status: "prepared", case_id };
          },
        },
        { signal: lifecycle.signal },
      );
      void Promise.resolve(registration).catch(() => {});
    } catch {
      /* Optional experimental API must never prevent normal navigation. */
    }
    return () => lifecycle.abort();
  }, []);
}
