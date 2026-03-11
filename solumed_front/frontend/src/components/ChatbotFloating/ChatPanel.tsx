"use client";
/**
 * components/ChatbotFloating/ChatPanel.tsx
 * ==========================================
 * Panel principal del chat (380×520px en desktop, 100% en móvil).
 *
 * Estructura:
 *  ┌─────────────────────┐
 *  │ HEADER              │
 *  ├─────────────────────┤
 *  │ MENSAJES (scroll)   │
 *  │  [sugerencias si    │
 *  │   chat vacío]       │
 *  ├─────────────────────┤
 *  │ INPUT               │
 *  └─────────────────────┘
 */

import { useRef, useEffect } from "react";
import { X, Bot, Circle, Minimize2 } from "lucide-react";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";
import type { EstadoChatbot } from "./useChatbot";

// Chips de sugerencias mostradas cuando el chat está vacío
const SUGERENCIAS = [
  "¿Cómo proceso una factura nueva?",
  "¿Cómo configuro el Extractor Gmail?",
  "¿Qué dice el Decreto 2200?",
];

type Props = Pick<EstadoChatbot,
  | "mensajes"
  | "inputTexto"
  | "enviando"
  | "reconociendo"
  | "setInputTexto"
  | "enviarMensaje"
  | "valorar"
  | "leerEnVoz"
  | "iniciarVoz"
  | "detenerVoz"
  | "cerrar"
>;

export default function ChatPanel({
  mensajes, inputTexto, enviando, reconociendo,
  setInputTexto, enviarMensaje, valorar, leerEnVoz,
  iniciarVoz, detenerVoz, cerrar,
}: Props) {
  const refFondo = useRef<HTMLDivElement>(null);

  // Auto-scroll al último mensaje cuando llegan nuevos
  useEffect(() => {
    refFondo.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes]);

  return (
    <div
      className="chatbot-panel"
      style={{
        position:      "fixed",
        bottom:        84,
        right:         24,
        width:         380,
        height:        520,
        background:    "var(--surface, #161b27)",
        border:        "1px solid var(--border)",
        borderRadius:  "var(--r-lg)",
        boxShadow:     "0 8px 40px rgba(0,0,0,.45)",
        display:       "flex",
        flexDirection: "column",
        zIndex:        9998,
        overflow:      "hidden",
        animation:     "chatPanelSlideUp .22s cubic-bezier(.16,1,.3,1)",
      }}
    >
      {/* ── HEADER ── */}
      <div style={{
        display:        "flex",
        alignItems:     "center",
        gap:            10,
        padding:        "12px 14px",
        background:     "#0c1421",
        borderBottom:   "1px solid rgba(255,255,255,.07)",
        flexShrink:     0,
      }}>
        {/* Avatar */}
        <div style={{
          width:          36,
          height:         36,
          borderRadius:   "50%",
          background:     "rgba(37,99,235,.2)",
          border:         "1px solid rgba(37,99,235,.35)",
          display:        "flex",
          alignItems:     "center",
          justifyContent: "center",
          flexShrink:     0,
        }}>
          <Bot size={18} color="#60a5fa" />
        </div>

        {/* Nombre y estado */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", lineHeight: 1.2 }}>
            Asistente IA
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 2 }}>
            <Circle
              size={7}
              color="#22c55e"
              fill="#22c55e"
              style={{ animation: enviando ? "chatMicPulse 1s infinite" : "none" }}
            />
            <span style={{ fontSize: 11, color: "#475569" }}>
              {enviando ? "Procesando..." : "En línea"}
            </span>
          </div>
        </div>

        {/* Botones header */}
        <button
          onClick={cerrar}
          title="Cerrar chat"
          style={{
            background:   "none",
            border:       "1px solid rgba(255,255,255,.1)",
            borderRadius: "var(--r-sm)",
            padding:      "5px 7px",
            cursor:       "pointer",
            color:        "#475569",
            display:      "flex",
            alignItems:   "center",
            transition:   "background .15s",
          }}
        >
          <X size={14} />
        </button>
      </div>

      {/* ── ÁREA DE MENSAJES ── */}
      <div style={{
        flex:       1,
        overflowY:  "auto",
        padding:    "14px 12px",
        display:    "flex",
        flexDirection: "column",
        gap:        10,
        scrollbarWidth: "thin",
      }}>
        {/* Sugerencias cuando el chat está vacío */}
        {mensajes.length === 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20, paddingTop: 16 }}>
            {/* Mensaje de bienvenida */}
            <div style={{
              display:        "flex",
              flexDirection:  "column",
              alignItems:     "center",
              gap:            10,
              textAlign:      "center",
            }}>
              <div style={{
                width:          52,
                height:         52,
                borderRadius:   "50%",
                background:     "rgba(37,99,235,.12)",
                border:         "1px solid rgba(37,99,235,.2)",
                display:        "flex",
                alignItems:     "center",
                justifyContent: "center",
              }}>
                <Bot size={24} color="#60a5fa" />
              </div>
              <div>
                <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", marginBottom: 4 }}>
                  ¡Hola! Soy tu Asistente IA
                </p>
                <p style={{ fontSize: 12, color: "var(--text3, #64748b)", lineHeight: 1.5 }}>
                  Puedo ayudarte a usar NexoFarma,<br />
                  responder sobre tus facturas<br />
                  y buscar información en internet.
                </p>
              </div>
            </div>

            {/* Chips de sugerencias */}
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              <p style={{ fontSize: 11, color: "var(--text4, #475569)", textAlign: "center" }}>
                Prueba preguntando:
              </p>
              {SUGERENCIAS.map(s => (
                <button
                  key={s}
                  onClick={() => enviarMensaje(s)}
                  style={{
                    padding:      "9px 13px",
                    background:   "rgba(37,99,235,.07)",
                    border:       "1px solid rgba(37,99,235,.18)",
                    borderRadius: "var(--r-md)",
                    color:        "#93c5fd",
                    fontSize:     12,
                    cursor:       "pointer",
                    textAlign:    "left",
                    transition:   "background .15s",
                    lineHeight:   1.4,
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Mensajes de la conversación */}
        {mensajes.map((msg, i) => (
          <ChatMessage
            key={`${msg.timestamp}-${i}`}
            mensaje={msg}
            onValorar={msg.id ? valorar : undefined}
            onLeer={leerEnVoz}
          />
        ))}

        {/* Referencia al fondo para auto-scroll */}
        <div ref={refFondo} />
      </div>

      {/* ── INPUT ── */}
      <ChatInput
        valor={inputTexto}
        onChange={setInputTexto}
        onEnviar={() => enviarMensaje()}
        onMicrofono={iniciarVoz}
        onDetenerMic={detenerVoz}
        enviando={enviando}
        reconociendo={reconociendo}
      />
    </div>
  );
}
