import type { Case, Consultation, Document, Workspace } from "./types";

export const DISCLAIMER =
  "Apoyo informativo preliminar. No sustituye la asesoría de un profesional del derecho. Revisa el contenido antes de firmar, presentar o tomar una decisión vinculante.";
export const id = () => crypto.randomUUID();
export const dateLabel = (date: string, long = false) =>
  new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    month: long ? "long" : "short",
    ...(long ? { year: "numeric" } : {}),
    timeZone: "UTC",
  }).format(new Date(date.length === 10 ? `${date}T12:00:00Z` : date));
export const emptyWorkspace = (): Workspace => ({
  cases: [],
  documents: [],
  consultations: [],
  drafts: [],
});
export const blankCase = (): Case => ({
  id: id(),
  name: "",
  country: "México",
  region: "",
  locality: "",
  date: "",
  matter: "Contratos con proveedores",
  context: "",
  status: "En preparación",
});

export function demoWorkspace(): Workspace {
  const cases: Case[] = [
    {
      id: "demo-1",
      name: "Festival Horizonte",
      country: "México",
      region: "Puebla",
      locality: "Puebla",
      date: "2026-11-21",
      matter: "Contratos con proveedores",
      context:
        "Ejemplo ficticio: festival de música al aire libre para 500 personas. Revisión de condiciones de proveedores y cancelación.",
      status: "En revisión",
    },
    {
      id: "demo-2",
      name: "Encuentro Creativo 2026",
      country: "México",
      region: "Ciudad de México",
      locality: "Cuauhtémoc",
      date: "2026-12-04",
      matter: "Permisos y cumplimiento",
      context:
        "Ejemplo ficticio: encuentro profesional en un recinto privado para 120 personas.",
      status: "En preparación",
    },
    {
      id: "demo-3",
      name: "Cena Anual de Fundación",
      country: "México",
      region: "Jalisco",
      locality: "Guadalajara",
      date: "2026-12-12",
      matter: "Contratos con proveedores",
      context:
        "Ejemplo ficticio: cena con servicio de catering para 80 invitados.",
      status: "En preparación",
    },
  ];
  const documents: Document[] = [
    {
      id: "doc-demo-1",
      case_id: "demo-1",
      name: "Acuerdo de recinto · ejemplo.txt",
      size: 680,
      text: "DOCUMENTO FICTICIO PARA DEMOSTRACIÓN.\n\n1. Partes. Organizador: Producciones Horizonte. Proveedor: Recinto Los Olivos.\n\n2. Servicio. Uso del recinto el 21 de noviembre de 2026 para un festival con aforo previsto de 500 personas.\n\n3. Pago. Anticipo del 30% al confirmar la reserva. El saldo se pagará diez días antes del evento.\n\n4. Cancelación. Las partes acordarán por escrito el tratamiento del anticipo y los gastos ya realizados.\n\n5. Responsabilidades. Las condiciones de seguro y permisos quedan pendientes de revisión profesional.",
      created_at: "2026-10-06T15:00:00Z",
    },
    {
      id: "doc-demo-2",
      case_id: "demo-1",
      name: "Propuesta de sonido · ejemplo.txt",
      size: 280,
      text: "DOCUMENTO FICTICIO PARA DEMOSTRACIÓN.\n\nServicio de sonido para Festival Horizonte, 21 de noviembre de 2026.\n\nPago: 50% de anticipo. Horario de montaje: 08:00. Retiro: 23:00.\n\nNo se ha acordado una fecha límite de cancelación. Pendiente definir responsabilidades por daño al equipo.",
      created_at: "2026-10-05T15:00:00Z",
    },
    {
      id: "doc-demo-3",
      case_id: "demo-2",
      name: "Ficha del encuentro · ejemplo.txt",
      size: 150,
      text: "DOCUMENTO FICTICIO PARA DEMOSTRACIÓN.\n\nEncuentro profesional para 120 personas el 4 de diciembre de 2026. Recinto por confirmar.\n\nSe recopilarán nombres y correos para el registro. Pendiente revisar el aviso de privacidad.",
      created_at: "2026-10-04T15:00:00Z",
    },
  ];
  return { cases, documents, consultations: [], drafts: [] };
}

export function prepareAnswer(
  question: string,
  context: Case,
  documents: Document[],
): Consultation {
  const normalize = (value: string) =>
    value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  const terms =
    normalize(question)
      .match(/[a-z]{4,}/g)
      ?.filter(
        (t) =>
          ![
            "para",
            "como",
            "puedo",
            "sobre",
            "tiene",
            "este",
            "esta",
            "debo",
            "cuales",
            "evento",
            "necesito",
          ].includes(t),
      ) ?? [];
  const citations = documents
    .filter((d) => d.case_id === context.id)
    .flatMap((d) =>
      d.text
        .split(/\n\s*\n/)
        .map((passage, i) => ({
          document_id: d.id,
          title: d.name,
          passage,
          locator: `Párrafo ${i + 1}`,
          origin: "private" as const,
        })),
    )
    .filter((c) => terms.some((t) => normalize(c.passage).includes(t)))
    .slice(0, 4);
  return {
    id: id(),
    case_id: context.id,
    question,
    context: { ...context },
    citations,
    created_at: new Date().toISOString(),
    outcome: "INSUFFICIENT_EVIDENCE",
    disclaimer: DISCLAIMER,
    answer: citations.length
      ? "Encontré estos fragmentos relacionados en tus documentos. Son referencias privadas, no fuentes de derecho. No puedo confirmar sus efectos legales ni su validez: todavía no hay un corpus jurídico verificado ni un modelo de IA conectado. Puedes llevar estos pasajes y el contexto del evento a revisión profesional."
      : "Todavía no hay fuentes jurídicas verificadas suficientes para respaldar una respuesta. Tampoco encontré fragmentos relacionados en los documentos seleccionados. Agrega un documento de texto pertinente o prepara la pregunta para revisarla con un profesional. No puedo confirmar requisitos, permisos ni obligaciones legales.",
  };
}

export function analyzeDocument(document: Document) {
  const categories = [
    ["Partes", /partes|organizador|proveedor/i],
    ["Pagos", /pago|saldo|anticipo|precio/i],
    ["Fechas y plazos", /fecha|días|horario|noviembre|diciembre/i],
    ["Cancelación", /cancelaci[oó]n|penalidad|rescisi[oó]n/i],
    ["Responsabilidades", /responsabil|seguro|daño/i],
  ] as const;
  return categories.map(([title, pattern]) => ({
    title,
    matches: document.text
      .split(/\n\s*\n/)
      .map((text, i) => ({ text, locator: `Párrafo ${i + 1}` }))
      .filter((p) => pattern.test(p.text)),
  }));
}

export function draftText(
  kind: string,
  context: Case,
  parties: string,
  terms: string,
): string {
  return `BORRADOR PRELIMINAR — REVISIÓN PROFESIONAL REQUERIDA\n\nFicha de acuerdo: ${kind}\nEvento: ${context.name}\nLugar: ${context.locality}, ${context.region}, ${context.country}\nFecha del evento: ${context.date}\n\n1. PARTES\n${parties.trim() || "[PENDIENTE: nombres y datos de las partes]"}\n\n2. CONDICIONES PROPUESTAS POR EL USUARIO\n${terms.trim() || "[PENDIENTE: servicio, alcance, importe y fechas de pago]"}\n\n3. PUNTOS PENDIENTES DE ACUERDO Y REVISIÓN\n[PENDIENTE: condiciones de cancelación y devolución]\n[PENDIENTE: responsabilidades y seguros]\n[PENDIENTE: permisos que correspondan al lugar y al tipo de evento]\n[PENDIENTE: tratamiento de datos personales, si aplica]\n[PENDIENTE: revisión profesional del texto completo]\n\nEsta ficha organiza datos facilitados por el usuario; no es un contrato validado ni ha sido generada por un modelo de IA. No tiene fuentes jurídicas asociadas.\n\n${DISCLAIMER}`;
}

export function downloadText(
  name: string,
  text: string,
  type = "text/plain;charset=utf-8",
) {
  const url = URL.createObjectURL(new Blob(["\ufeff", text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
