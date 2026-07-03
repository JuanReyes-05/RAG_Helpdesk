"""Plantillas de prompts usadas por los services de generación y scoring."""
from app.schemas.enums import TipoIntencion

PROMPT_SISTEMA = """Eres un asistente de soporte al cliente profesional y empático.
Tu única fuente de información es el contexto que se te proporciona a continuación.

REGLAS IMPORTANTES:
1. Responde ÚNICAMENTE basándote en el contexto proporcionado.
2. Si el contexto no contiene información suficiente para responder, di exactamente:
   "Lo siento, no tengo información suficiente sobre ese tema en mi base de conocimiento."
3. No inventes información ni uses conocimiento externo.
4. Sé conciso pero completo. Máximo 3-4 párrafos.
5. Si hay pasos a seguir, usa una lista numerada.
6. Mantén un tono amigable y profesional.

CONTEXTO DE LA BASE DE CONOCIMIENTO:
{contexto}

PREGUNTA DEL USUARIO:
{pregunta}

RESPUESTA:"""

PROMPT_SCORE = """Evalúa qué tan bien responde el siguiente texto a la pregunta dada.
Devuelve SOLO un número decimal entre 0.0 y 1.0, sin texto adicional.

0.0 = No hay información relevante / dice que no sabe
0.5 = Información parcial o poco específica
1.0 = Respuesta completa y directa

Pregunta: {pregunta}
Respuesta: {respuesta}

Score (solo el número):"""

PROMPT_DERIVACION = """Analiza el siguiente mensaje de un usuario y decide si su caso requiere derivar el ticket a 2do nivel o puede resolverse con una respuesta directa.

Devuelve SOLO "si" o "no", sin texto adicional.

"si" = El caso requiere seguimiento: reclamo, falla técnica persistente, reembolso, queja formal, situación que necesita acción por parte de un agente humano.
"no" = El caso puede resolverse con información: consulta, pregunta, duda, solicitud de instrucciones.

Mensaje del usuario: {pregunta}

¿Requiere ticket de seguimiento? (si/no):"""

FRASES_SIN_INFO = (
    "no tengo información suficiente",
    "no tengo información sobre",
    "no encontré información",
    "no puedo responder",
)

PROMPT_CLASIFICACION_INTENCION = """Clasifica el siguiente mensaje del usuario en UNA de estas categorías:

SALUDO - Saludo inicial sin contenido adicional (hola, buenos días, qué tal, hey, buenas)
DESPEDIDA - Despedida sin nueva pregunta (adiós, chao, hasta luego, nos vemos, bye)
AGRADECIMIENTO - Agradecimiento sin nueva pregunta (gracias, muchas gracias, mil gracias)
IDENTIDAD - Pregunta sobre quién o qué es el asistente (¿quién eres?, ¿qué eres?, ¿cómo te llamas?)
CAPACIDADES - Pregunta sobre qué puede hacer el asistente (¿qué puedes hacer?, ¿en qué me ayudas?, ¿para qué sirves?)
CONSULTA_SOPORTE - Consulta técnica, pregunta de soporte, reclamo o cualquier solicitud sustantiva
OTRO - Mensaje sin sentido, muy corto sin contexto, o que no encaja en las otras categorías

REGLAS:
- Si el mensaje mezcla un saludo con una pregunta técnica (ej. "hola, cómo restablezco mi VPN"), clasifica como CONSULTA_SOPORTE.
- Ante duda entre CONSULTA_SOPORTE y OTRO, prefiere CONSULTA_SOPORTE.
- Devuelve SOLO la etiqueta en mayúsculas, sin explicación, sin puntuación, sin comillas.

Mensaje: {pregunta}

Categoría:"""

# Respuestas canned para cada tipo de small talk. La clave CONSULTA_SOPORTE
# no aparece porque esos mensajes se enrutan al pipeline RAG normal.
RESPUESTAS_SMALLTALK: dict[TipoIntencion, str] = {
    TipoIntencion.SALUDO: (
        "¡Hola! Soy tu asistente virtual de soporte. "
        "¿En qué puedo ayudarte hoy?"
    ),
    TipoIntencion.DESPEDIDA: (
        "¡Hasta pronto! Si necesitas algo más, aquí estaré."
    ),
    TipoIntencion.AGRADECIMIENTO: (
        "¡De nada! ¿Hay algo más en lo que pueda ayudarte?"
    ),
    TipoIntencion.IDENTIDAD: (
        "Soy el asistente virtual de soporte al cliente. "
        "Respondo consultas basándome en nuestra base de conocimiento interna."
    ),
    TipoIntencion.CAPACIDADES: (
        "Puedo ayudarte con consultas de soporte técnico basándome en nuestra "
        "documentación (VPN, políticas de soporte, preguntas frecuentes). "
        "¿Sobre qué necesitas información?"
    ),
    TipoIntencion.OTRO: (
        "Disculpa, no logré entender tu mensaje. "
        "¿Podrías reformular tu consulta con más detalle?"
    ),
}
