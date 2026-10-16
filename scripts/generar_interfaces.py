"""Genera los siete mockups documentales SVG de juridIA; solo biblioteca estándar.

Uso: python scripts/generar_interfaces.py
Los archivos se escriben en docs/interfaces, relativo a la raíz del proyecto.
No crea una aplicación ni requiere dependencias de dibujo o fuentes externas.
"""

from html import escape
from pathlib import Path
import textwrap
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "interfaces"
C = {
    "bg": "#f4f6f5", "white": "#ffffff", "ink": "#243432",
    "muted": "#586965", "green": "#174d49", "pale": "#e7f0ed",
    "line": "#d4dfda", "amber": "#775515", "amber_bg": "#fff4db",
    "red": "#8b3333", "red_bg": "#fff0ee", "disabled": "#e9edeb",
}


class Screen:
    """Primitivas de un lienzo documental de 1200 x 1000 píxeles."""

    def __init__(self, ident, title, desc, active=None, admin=False):
        self.ident = ident
        self.parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1000" '
            'viewBox="0 0 1200 1000" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(ident + ". " + title)}</title>',
            f'<desc id="desc">{escape(desc)}</desc>',
            '<style>text{font-family:Arial,Helvetica,sans-serif} '
            '.label{font-weight:600} .small{font-size:13px}</style>',
        ]
        self.rect(0, 0, 1200, 1000, "bg", radius=0)
        self.rect(0, 0, 1200, 74, "white", radius=0)
        self.rect(36, 17, 40, 40, "green", radius=10)
        self.text(56, 45, "B", size=25, color="white", weight=700, anchor="middle")
        self.text(90, 34, "juridIA", size=17, color="green", weight=700)
        self.text(90, 55, "Apoyo jurídico preliminar para eventos", size=13, color="muted")
        self.pill(941, 25, 215, "Diseño preliminar · " + ident)
        if active:
            self.rect(0, 75, 1200, 57, "white", radius=0)
            labels = ["Fuentes", "Comentarios", "Cuenta"] if admin else [
                "Expedientes", "Consulta", "Documentos", "Borradores", "Cuenta"
            ]
            x = 44
            for label in labels:
                w = max(100, len(label) * 9 + 30)
                if label == active:
                    self.rect(x, 84, w, 37, "pale", radius=7)
                self.text(x + w / 2, 108, label, size=15,
                          color="green" if label == active else "muted",
                          weight=700 if label == active else 400, anchor="middle")
                x += w + 12
            self.text(1128, 108, "Salir", size=15, color="green", anchor="end")
        self.text(44, 174, title, size=30, weight=700)

    def rect(self, x, y, w, h, fill="white", stroke=None, radius=12):
        border = f' stroke="{C.get(stroke, stroke)}"' if stroke else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{radius}" fill="{C.get(fill, fill)}"{border}/>'
        )

    def text(self, x, y, value, size=16, color="ink", weight=400, anchor="start"):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{size}" '
            f'fill="{C.get(color, color)}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(str(value))}</text>'
        )

    def para(self, x, y, value, width, size=16, color="muted", line=23, weight=400):
        chars = max(12, int(width / (size * 0.55)))
        lines = []
        for paragraph in value.split("\n"):
            lines.extend(textwrap.wrap(paragraph, chars) or [""])
        for i, content in enumerate(lines):
            self.text(x, y + i * line, content, size, color, weight)
        return y + len(lines) * line

    def line(self, x1, y, x2):
        self.parts.append(f'<path d="M{x1} {y}H{x2}" stroke="{C["line"]}"/>')

    def card(self, x, y, w, h, title=None):
        self.rect(x, y, w, h, stroke="line")
        if title:
            self.text(x + 22, y + 35, title, size=19, weight=700)

    def pill(self, x, y, w, value, color="green", bg="pale"):
        self.rect(x, y, w, 27, bg, radius=13)
        self.text(x + w / 2, y + 18, value, size=12, color=color, weight=700, anchor="middle")

    def field(self, x, y, w, label, value="Por completar", h=43, required=False):
        self.text(x, y, label + (" *" if required else ""), size=14, weight=700)
        self.rect(x, y + 11, w, h, "white", "line", radius=7)
        self.para(x + 13, y + 37, value, w - 26, size=15, line=21)

    def button(self, x, y, w, label, style="primary", h=41):
        fill = {"primary": "green", "secondary": "white", "disabled": "disabled",
                "danger": "red_bg"}[style]
        color = {"primary": "white", "secondary": "green", "disabled": "muted",
                 "danger": "red"}[style]
        self.rect(x, y, w, h, fill, None if style == "primary" else "line", radius=7)
        self.text(x + w / 2, y + h / 2 + 5, label, size=14, color=color, weight=700, anchor="middle")

    def notice(self, x, y, w, title, body, h=88, warning=False):
        self.rect(x, y, w, h, "amber_bg" if warning else "pale", radius=9)
        color = "amber" if warning else "green"
        self.text(x + 18, y + 27, title, size=16, color=color, weight=700)
        self.para(x + 18, y + 51, body, w - 36, size=14, color=color, line=20)

    def states(self, loading, empty, error, ready):
        self.text(44, 861, "ESTADOS PREVISTOS · variantes para revisión del diseño", size=12, color="muted", weight=700)
        variants = [("Carga", loading), ("Vacío", empty), ("Error", error), ("Listo", ready)]
        for i, (label, content) in enumerate(variants):
            x = 44 + i * 282
            self.rect(x, 875, 266, 83, "white", "line", radius=9)
            self.text(x + 15, 898, label, size=13, color="green", weight=700)
            self.para(x + 15, 919, content, 236, size=12, line=16)
        self.text(44, 984, "Mockup estático · sin datos reales · controles ilustrativos", size=12, color="muted")
        self.text(1156, 984, self.ident + " / 07", size=12, color="muted", anchor="end")

    def save(self, name):
        xml = "\n".join(self.parts + ["</svg>"]) + "\n"
        ET.fromstring(xml)
        path = OUT / name
        path.write_text(xml, encoding="utf-8")
        return path


def ui01():
    s = Screen("UI01", "Acceso y recuperación", "Formulario de acceso vacío. Incluye correo, contraseña, creación de cuenta, recuperación y segundo factor para administradores. Los estados de carga, error y éxito son ejemplos de diseño.")
    s.text(44, 205, "Inicia sesión para trabajar con tus propios expedientes.", color="muted")
    s.card(44, 237, 528, 562, "Entrar a mi cuenta")
    s.field(70, 317, 476, "Correo electrónico", "nombre@ejemplo.invalid", required=True)
    s.field(70, 408, 476, "Contraseña", "Introduce tu contraseña", required=True)
    s.text(70, 483, "Los errores se muestran junto al campo correspondiente.", size=13, color="muted")
    s.button(70, 515, 476, "Entrar")
    s.line(70, 583, 546)
    s.text(70, 616, "Primera visita", size=15, weight=700)
    s.button(70, 638, 225, "Crear cuenta", "secondary")
    s.button(309, 638, 237, "Recuperar acceso", "secondary")
    s.para(70, 720, "El registro público crea una cuenta de Usuario. No concede permisos administrativos.", 465, size=14)
    s.card(596, 237, 560, 344, "Segundo factor administrativo")
    s.pill(620, 291, 247, "Solo después de validar contraseña")
    s.para(620, 345, "Introduce el código de tu aplicación de autenticación para completar el acceso.", 507)
    s.field(620, 416, 300, "Código MFA", "—  —  —  —  —  —")
    s.button(936, 427, 194, "Verificar", "secondary", h=43)
    s.para(620, 508, "Hasta verificarlo no se inicia una sesión administrativa. El desafío tiene vencimiento.", 508, size=14)
    s.notice(596, 603, 560, "Recuperación de acceso", "Solicita instrucciones con tu correo. La respuesta no revela si existe una cuenta asociada.", h=104)
    s.para(620, 754, "Aviso: apoyo informativo preliminar; requiere revisión profesional antes de una decisión vinculante.", 505, size=14)
    s.states("Verificando acceso…", "Completa correo y contraseña.", "No fue posible verificar el acceso.", "Sesión iniciada; abrir expedientes.")
    return s.save("UI01-acceso.svg")


def ui02():
    s = Screen("UI02", "Expedientes y contexto del evento", "Vista vacía de expedientes y formulario con nombre, país, región, localidad, materia, fecha relevante y contexto. Incluye buscar, crear, guardar y continuar a consulta, documentos o borradores.", "Expedientes")
    s.text(44, 204, "Define el contexto antes de solicitar información jurídica específica.", color="muted")
    s.card(44, 237, 355, 566, "Mis eventos")
    s.field(66, 312, 311, "Buscar expediente", "Nombre del evento")
    s.button(66, 390, 311, "Crear expediente")
    s.line(66, 455, 377)
    s.text(66, 489, "Sin expedientes todavía", size=18, weight=700)
    s.para(66, 523, "Crea el primero para reunir contexto, documentos y consultas de un evento.", 305)
    s.text(66, 664, "Al guardar aparecerán aquí:", size=14, weight=700)
    s.para(66, 694, "Nombre · Jurisdicción · Fecha\nAcción: Abrir expediente", 305, size=14)
    s.card(423, 237, 733, 566, "Nuevo expediente")
    s.field(447, 313, 685, "Nombre del evento", "Por completar", required=True)
    s.field(447, 402, 329, "País", "Seleccionar", required=True)
    s.field(803, 402, 329, "Estado / región", "Por completar")
    s.field(447, 491, 329, "Localidad", "Si la consulta lo requiere")
    s.field(803, 491, 329, "Materia", "Seleccionar", required=True)
    s.field(447, 580, 217, "Fecha relevante", "dd / mm / aaaa", required=True)
    s.field(688, 580, 444, "Contexto del evento", "Describe actividad y situación a revisar.", h=77, required=True)
    s.button(447, 708, 140, "Guardar")
    s.button(600, 708, 161, "Consultar", "secondary")
    s.button(774, 708, 173, "Documentos", "secondary")
    s.button(960, 708, 172, "Borradores", "secondary")
    s.text(447, 777, "Editar contexto no cambia las respuestas históricas.", size=13, color="muted")
    s.states("Cargando tus expedientes…", "Crea tu primer expediente.", "Completa los campos señalados.", "Expediente guardado; puedes abrirlo.")
    return s.save("UI02-expedientes.svg")


def ui03():
    s = Screen("UI03", "Consulta y fuentes", "Pantalla de consulta con contexto pendiente, pregunta vacía y documentos propios opcionales. La salida ilustrada es Sin fuentes suficientes: no muestra conclusiones ni citas inventadas. Incluye límites, revisión y reporte con fragmento compartido explícitamente.", "Consulta")
    s.text(44, 204, "Revisa el contexto y el respaldo de cada respuesta preliminar.", color="muted")
    s.rect(44, 230, 1112, 78, "white", "line")
    s.text(64, 255, "Expediente: por seleccionar", size=14, weight=700)
    s.text(64, 283, "Jurisdicción: por completar     ·     Fecha relevante: por completar", size=14, color="muted")
    s.button(976, 248, 160, "Cambiar contexto", "secondary")
    s.card(44, 331, 693, 225, "Tu pregunta")
    s.field(66, 399, 649, "Pregunta sobre tu evento", "Escribe qué necesitas revisar.", h=54)
    s.button(66, 484, 263, "Seleccionar documentos", "secondary")
    s.text(344, 510, "Opcionales · solo propios", size=12, color="muted")
    s.button(568, 484, 147, "Consultar")
    s.card(44, 577, 693, 241, "Respuesta preliminar")
    s.pill(66, 628, 218, "Sin fuentes suficientes", "amber", "amber_bg")
    s.para(66, 684, "No hay evidencia disponible para respaldar una respuesta específica. Completa el contexto y revisa qué fuentes o documentos faltan.", 638, size=16)
    s.text(66, 770, "Sin conclusiones jurídicas ni referencias inventadas.", size=13, color="muted")
    s.card(759, 331, 397, 487, "Evidencia y revisión")
    s.text(781, 401, "Fuentes jurídicas del corpus", size=15, weight=700)
    s.text(781, 431, "Ninguna fuente recuperada.", size=14, color="muted")
    s.text(781, 478, "Documentos privados", size=15, weight=700)
    s.text(781, 508, "Ninguno seleccionado.", size=14, color="muted")
    s.button(781, 538, 353, "Ver pasaje · sin evidencia", "disabled")
    s.para(781, 614, "Las citas mostrarán título, versión, vigencia y localizador disponibles.", 344, size=14)
    s.button(781, 667, 353, "Exportar resumen editable", "disabled")
    s.button(781, 721, 353, "Reportar respuesta", "secondary")
    s.para(781, 788, "Comparte solo el fragmento que selecciones.", 344, size=12, line=16)
    s.states("Preparando respuesta…", "Sin fuentes suficientes.", "No se pudo generar. Reintenta.", "Respuesta con evidencia y límites.")
    s.text(44, 839, "Apoyo informativo preliminar; no sustituye a un profesional del derecho autorizado.", size=12, color="green")
    return s.save("UI03-consulta.svg")


def ui04():
    s = Screen("UI04", "Documentos y análisis", "Gestión de documentos con carga PDF, DOCX o TXT, filtro de expediente y una fila ficticia rotulada en estado Procesando. El análisis está deshabilitado hasta disponer de texto. Se incluyen categorías de hallazgos y consecuencias de eliminar derivados.", "Documentos")
    s.text(44, 204, "Conserva el origen de cada hallazgo y revisa por separado sus categorías.", color="muted")
    s.button(44, 232, 263, "Subir PDF / DOCX / TXT")
    s.field(700, 222, 456, "Filtrar / asociar a expediente", "Seleccionar expediente propio")
    s.card(44, 308, 1112, 146)
    for x, label in [(66, "ARCHIVO"), (486, "ESTADO DE INGESTA"), (885, "ACCIONES")]:
        s.text(x, 337, label, size=12, color="muted", weight=700)
    s.line(66, 356, 1134)
    s.text(66, 390, "ejemplo-ficticio.pdf", size=16, weight=700)
    s.text(66, 423, "Ejemplo de estado · no es un archivo real", size=12, color="muted")
    s.pill(486, 373, 210, "Procesando · no disponible", "amber", "amber_bg")
    s.button(864, 373, 119, "Abrir", "disabled")
    s.button(996, 373, 138, "Eliminar", "danger")
    s.card(44, 477, 532, 225, "Texto y localizadores")
    s.para(66, 551, "Todavía no hay texto disponible. Cuando termine la ingesta se mostrará el documento con referencias de página o cláusula.", 482)
    s.button(66, 639, 486, "Analizar · espera a que esté listo", "disabled")
    s.card(600, 477, 556, 225, "Hallazgos por revisar")
    categories = ["Cláusulas", "Obligaciones", "Fechas / plazos", "Pagos / penalidades", "Riesgos", "Información faltante"]
    for i, label in enumerate(categories):
        x = 622 + (i % 2) * 258
        y = 531 + (i // 2) * 48
        s.rect(x, y, 236, 36, "bg", radius=6)
        s.text(x + 12, y + 24, label, size=14, color="muted")
    s.notice(44, 724, 532, "Antes de eliminar", "El borrado también bloquea resultados y exportaciones derivados. Confirma después de revisar el alcance.", h=103, warning=True)
    s.notice(600, 724, 556, "Revisión del origen", "Abre el fragmento de cada hallazgo. «No encontrado» no significa «no existe»; los riesgos requieren revisión.", h=103)
    s.states("Validando y extrayendo texto…", "No hay documentos cargados.", "Archivo inválido o sin texto útil.", "Documento listo para analizar.")
    return s.save("UI04-documentos.svg")


def ui05():
    s = Screen("UI05", "Borradores", "Preparación de un borrador preliminar con tipo de acuerdo, partes, condiciones y contexto pendientes. Editor vacío con campos marcados, revisión de fuentes y distinción entre texto generado y edición del usuario. No contiene cláusulas jurídicas inventadas.", "Borradores")
    s.text(44, 204, "Completa los datos y conserva visibles las limitaciones del texto.", color="muted")
    s.card(44, 233, 347, 585, "Datos del acuerdo")
    s.field(66, 308, 303, "Tipo de acuerdo", "Seleccionar tipo")
    s.para(66, 385, "Recinto · Artista · Catering\nPatrocinio · Técnico · Boletaje", 299, size=13, line=21)
    s.field(66, 458, 303, "Partes", "Por completar", h=54)
    s.field(66, 558, 303, "Condiciones", "Por completar", h=73)
    s.field(66, 675, 303, "Contexto del evento", "Seleccionar expediente")
    s.button(66, 753, 303, "Generar borrador")
    s.notice(415, 233, 741, "BORRADOR PRELIMINAR", "Revisión profesional requerida antes de firmar, presentar o tomar una decisión vinculante.", h=94, warning=True)
    s.card(415, 349, 741, 308, "Editor")
    s.pill(928, 368, 205, "Versión: sin guardar")
    s.text(438, 424, "[Nombre y tipo de acuerdo]", size=17, color="muted")
    s.text(438, 466, "[Partes y datos por completar]", size=16, color="muted")
    s.text(438, 508, "[Condiciones y contexto pendientes]", size=16, color="muted")
    s.line(438, 542, 1132)
    s.para(438, 574, "Aún no se ha generado contenido. Las modificaciones del usuario se distinguirán del texto generado.", 671, size=14)
    s.text(438, 632, "Añadir texto manualmente no le atribuye respaldo automático.", size=13, color="muted")
    s.card(415, 679, 741, 139)
    s.text(438, 708, "Fuentes: pendientes · Campos incompletos: por revisar", size=14, weight=700)
    s.text(438, 734, "Sin evidencia suficiente para atribuir respaldo jurídico.", size=13, color="muted")
    s.button(438, 757, 221, "Guardar versión", "disabled")
    s.button(675, 757, 457, "Exportar archivo editable", "disabled")
    s.states("Preparando borrador…", "Completa tipo, partes y contexto.", "Faltan datos o evidencia suficiente.", "Borrador editable para revisión.")
    return s.save("UI05-borradores.svg")


def ui06():
    s = Screen("UI06", "Administración de fuentes", "Vista administrativa del corpus, sin fuentes registradas. Exige rol administrador y MFA. Incluye metadatos, nueva versión, reindexación, activación, desactivación y retiro; reportes vacíos con acceso limitado al fragmento compartido.", "Fuentes", admin=True)
    s.text(44, 204, "Acceso previsto: rol Administrador y MFA verificado.", color="muted")
    s.button(934, 157, 222, "Agregar fuente")
    s.card(44, 237, 1112, 231, "Fuentes jurídicas del corpus")
    columns = [(66, "TÍTULO"), (408, "JURISDICCIÓN"), (645, "VIGENCIA"), (839, "VERSIÓN"), (1007, "ESTADO")]
    for x, label in columns:
        s.text(x, 311, label, size=12, color="muted", weight=700)
    s.line(66, 329, 1134)
    s.text(600, 375, "Todavía no hay fuentes registradas", size=20, weight=700, anchor="middle")
    s.text(600, 409, "Agrega una fuente y valida sus metadatos antes de activarla.", size=15, color="muted", anchor="middle")
    s.card(44, 491, 1112, 132, "Acciones sobre la fuente seleccionada")
    labels = [(66, 205, "Nueva versión"), (283, 195, "Reindexar"), (490, 195, "Activar"), (697, 210, "Desactivar"), (919, 215, "Retirar")]
    for x, w, label in labels:
        s.button(x, 549, w, label, "disabled")
    s.card(44, 646, 674, 179, "Comentarios recibidos")
    s.text(66, 715, "Sin reportes pendientes", size=16, weight=700)
    s.text(66, 744, "Se muestran motivo y fragmento compartido por el usuario.", size=13, color="muted")
    s.button(66, 763, 188, "Revisar", "disabled")
    s.button(268, 763, 428, "Registrar resolución", "disabled")
    s.notice(742, 646, 414, "Control de cambios", "Un reporte no modifica fuentes automáticamente. Un fallo de ingesta conserva la versión publicada.", h=179)
    s.states("Procesando versión o reindexado…", "No hay fuentes registradas.", "Ingesta fallida; corregir versión.", "Versión validada y activable.")
    return s.save("UI06-fuentes.svg")


def ui07():
    s = Screen("UI07", "Cuenta y privacidad", "Controles de sesiones, exportación y eliminación de cuenta. La fila de sesión es ficticia y está rotulada. Las solicitudes están vacías. La eliminación requiere confirmar y reautenticar, diferenciando exclusión inmediata, purga y rotación de copias.", "Cuenta")
    s.text(44, 204, "Gestiona tus sesiones y solicitudes sobre tus propios datos.", color="muted")
    s.card(44, 236, 663, 235, "Sesiones activas")
    s.pill(476, 255, 208, "Ejemplo ficticio de sesión")
    s.text(67, 326, "[ ] Este navegador", size=17, weight=700)
    s.text(67, 357, "Sesión actual · actividad por mostrar", size=14, color="muted")
    s.button(67, 399, 348, "Cerrar sesión seleccionada", "secondary")
    s.button(429, 399, 254, "Cerrar todas", "secondary")
    s.card(731, 236, 425, 235, "Mis datos")
    s.button(754, 306, 379, "Exportar mis datos")
    s.button(754, 362, 379, "Solicitar eliminación de cuenta", "danger")
    s.para(754, 435, "Eliminar requiere confirmación y reautenticación.", 375, size=13, line=18)
    s.card(44, 494, 1112, 174, "Solicitudes")
    for x, label in [(67, "FECHA"), (299, "TIPO"), (567, "ESTADO"), (902, "DESCARGA")]:
        s.text(x, 562, label, size=12, color="muted", weight=700)
    s.line(67, 579, 1133)
    s.text(67, 623, "No hay solicitudes registradas.", size=15, color="muted")
    s.button(871, 598, 262, "Descargar si disponible", "disabled")
    s.card(44, 691, 1112, 139, "Conservación y efecto del borrado")
    s.text(67, 752, "1. Exclusión inmediata", size=15, weight=700)
    s.text(435, 752, "2. Purga de datos activos", size=15, weight=700)
    s.text(825, 752, "3. Rotación de copias", size=15, weight=700)
    s.para(67, 781, "Política vigente y plazos: pendientes de aprobación para el lanzamiento. Una falla de purga mantiene el contenido inaccesible.", 1052, size=13, line=20)
    s.states("Preparando exportación / purga…", "Sin solicitudes de privacidad.", "Purga en reintento; sin acceso.", "Exportación disponible o purga hecha.")
    return s.save("UI07-cuenta.svg")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for make in (ui01, ui02, ui03, ui04, ui05, ui06, ui07):
        path = make()
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
