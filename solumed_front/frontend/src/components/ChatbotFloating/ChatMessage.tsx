"use client";
/**
 * components/ChatbotFloating/ChatMessage.tsx
 * ============================================
 * Burbuja individual de mensaje en el chat.
 * Maneja:
 *  - Diferenciación visual usuario/asistente
 *  - Animación de typing (tres puntos pulsantes)
 *  - Indicador de búsqueda web
 *  - Botón de lectura en voz alta (TTS)
 *  - Botones de valoración thumbs up/down
 */

import { Volume2, ThumbsUp, ThumbsDown, Globe, Settings } from "lucide-react";
import type { MensajeChat } from "./useChatbot";

interface Props {
  mensaje: MensajeChat;
  onValorar?: (mensajeId: number, valoracion: 1 | -1) => void;
  onLeer?: (texto: string) => void;
}

// Formatea el timestamp en HH:MM
function formatHora(ts: number): string {
  return new Date(ts).toLocaleTimeString("es-CO", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Burbuja especial para acciones agénticas ──────────────────────────────
function BurbujaAccion({ mensaje }: { mensaje: MensajeChat }) {
  const enCurso = mensaje.accionando;

  return (
    <div style={{
      display:    "flex",
      alignItems: "flex-start",
      gap:        8,
      maxWidth:   "100%",
      margin:     "2px 0",
    }}>
      {/* Ícono de engranaje (animado si está en curso) */}
      <div style={{
        flexShrink:  0,
        marginTop:   2,
        animation:   enCurso ? "spin 1.5s linear infinite" : "none",
        color:       enCurso ? "#60a5fa" : "#22c55e",
        display:     "flex",
      }}>
        <Settings size={13} />
      </div>

      {/* Contenido de la acción */}
      <div style={{
        padding:      "7px 11px",
        borderRadius: "10px",
        background:   enCurso
          ? "rgba(96,165,250,.07)"
          : "rgba(34,197,94,.07)",
        border:       `1px solid ${enCurso
          ? "rgba(96,165,250,.2)"
          : "rgba(34,197,94,.2)"}`,
        fontSize:     12,
        color:        enCurso
          ? "rgba(96,165,250,.9)"
          : "rgba(34,197,94,.9)",
        fontStyle:    "italic",
        lineHeight:   1.4,
        maxWidth:     "85%",
      }}>
        {mensaje.contenido}
      </div>
    </div>
  );
}


export default function ChatMessage({ mensaje, onValorar, onLeer }: Props) {
  // Burbuja de acción agéntica (diferente al flujo normal)
  if (mensaje.rol === "accion") {
    return <BurbujaAccion mensaje={mensaje} />;
  }

  const esUsuario = mensaje.rol === "usuario";

  return (
    <div style={{
      display:       "flex",
      flexDirection: "column",
      alignItems:    esUsuario ? "flex-end" : "flex-start",
      gap:           4,
      maxWidth:      "100%",
    }}>
      {/* Burbuja de mensaje */}
      <div style={{
        maxWidth:     "82%",
        padding:      "9px 13px",
        borderRadius: esUsuario ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
        background:   esUsuario
          ? "rgba(37,99,235,.15)"
          : "var(--surface2, rgba(255,255,255,.06))",
        border:       `1px solid ${esUsuario
          ? "rgba(37,99,235,.25)"
          : "var(--border)"}`,
        wordBreak: "break-word",
      }}>

        {/* Animación de typing / indicador de búsqueda */}
        {mensaje.cargando && !mensaje.contenido ? (
          mensaje.buscando ? (
            // Buscando en internet
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Globe size={13} color="#60a5fa" style={{ flexShrink: 0 }} />
              <span style={{ fontSize: 12, color: "var(--text3, #64748b)", fontStyle: "italic" }}>
                Buscando en internet...
              </span>
            </div>
          ) : (
            // Tres puntos pulsantes
            <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "2px 0" }}>
              {[0, 1, 2].map(i => (
                <span key={i} style={{
                  width:        7,
                  height:       7,
                  borderRadius: "50%",
                  background:   "var(--text3, #64748b)",
                  display:      "inline-block",
                  animation:    `chatDotPulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                }} />
              ))}
            </div>
          )
        ) : (
          <>
            {/* Indicador de búsqueda en curso mientras ya hay texto */}
            {mensaje.buscando && (
              <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 5 }}>
                <Globe size={11} color="#60a5fa" />
                <span style={{ fontSize: 11, color: "#60a5fa", fontStyle: "italic" }}>
                  Buscando información actualizada...
                </span>
              </div>
            )}
            {/* Texto del mensaje */}
            <p style={{
              fontSize:   13,
              lineHeight: 1.55,
              color:      "var(--text)",
              margin:     0,
              whiteSpace: "pre-wrap",
            }}>
              {mensaje.contenido}
            </p>
          </>
        )}
      </div>

      {/* Timestamp */}
      <span style={{
        fontSize: 10,
        color:    "var(--text4, #475569)",
        padding:  "0 4px",
      }}>
        {formatHora(mensaje.timestamp)}
      </span>

      {/* Acciones del asistente: TTS + valoración */}
      {!esUsuario && !mensaje.cargando && mensaje.contenido && (
        <div style={{ display: "flex", gap: 4, padding: "0 2px" }}>
          {/* Botón escuchar en voz alta */}
          {onLeer && (
            <button
              onClick={() => onLeer(mensaje.contenido)}
              title="Escuchar en voz alta"
              style={{
                background: "none",
                border:     "1px solid var(--border)",
                borderRadius: 6,
                padding:    "3px 6px",
                cursor:     "pointer",
                color:      "var(--text3, #64748b)",
                display:    "flex",
                alignItems: "center",
                transition: "background .15s",
              }}
            >
              <Volume2 size={11} />
            </button>
          )}

          {/* Thumbs up */}
          {onValorar && mensaje.id && (
            <>
              <button
                onClick={() => onValorar(mensaje.id!, 1)}
                title="Útil"
                style={{
                  background:   mensaje.valoracion === 1
                    ? "rgba(34,197,94,.15)"
                    : "none",
                  border:       `1px solid ${mensaje.valoracion === 1
                    ? "rgba(34,197,94,.4)"
                    : "var(--border)"}`,
                  borderRadius: 6,
                  padding:      "3px 6px",
                  cursor:       "pointer",
                  color:        mensaje.valoracion === 1 ? "#22c55e" : "var(--text3, #64748b)",
                  display:      "flex",
                  alignItems:   "center",
                  transition:   "all .15s",
                }}
              >
                <ThumbsUp size={11} />
              </button>

              {/* Thumbs down */}
              <button
                onClick={() => onValorar(mensaje.id!, -1)}
                title="No útil"
                style={{
                  background:   mensaje.valoracion === -1
                    ? "rgba(239,68,68,.1)"
                    : "none",
                  border:       `1px solid ${mensaje.valoracion === -1
                    ? "rgba(239,68,68,.3)"
                    : "var(--border)"}`,
                  borderRadius: 6,
                  padding:      "3px 6px",
                  cursor:       "pointer",
                  color:        mensaje.valoracion === -1 ? "#ef4444" : "var(--text3, #64748b)",
                  display:      "flex",
                  alignItems:   "center",
                  transition:   "all .15s",
                }}
              >
                <ThumbsDown size={11} />
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
