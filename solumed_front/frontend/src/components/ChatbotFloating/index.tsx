"use client";
/**
 * components/ChatbotFloating/index.tsx
 * ======================================
 * Componente raíz del chatbot flotante.
 * Se importa en (app)/layout.tsx y aparece en TODAS las páginas autenticadas.
 *
 * Contiene:
 *  - Los keyframes CSS de las animaciones
 *  - El botón flotante circular (bottom-right)
 *  - Badge de mensajes no leídos
 *  - El panel de chat (condicional)
 */

import { Bot, X } from "lucide-react";
import { useChatbot } from "./useChatbot";
import ChatPanel from "./ChatPanel";

export default function ChatbotFloating() {
  const chatbot = useChatbot();

  return (
    <>
      {/* ── Animaciones globales para el chatbot ── */}
      <style>{`
        @keyframes chatDotPulse {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
          40%            { transform: scale(1);   opacity: 1;   }
        }
        @keyframes chatBtnPulse {
          0%, 100% { box-shadow: 0 4px 20px rgba(37,99,235,.45), 0 0 0 0 rgba(37,99,235,.4); }
          70%      { box-shadow: 0 4px 20px rgba(37,99,235,.45), 0 0 0 12px rgba(37,99,235,0); }
        }
        @keyframes chatPanelSlideUp {
          from { opacity: 0; transform: translateY(16px) scale(.97); }
          to   { opacity: 1; transform: translateY(0)    scale(1);   }
        }
        @keyframes chatMicPulse {
          0%, 100% { opacity: 1; }
          50%      { opacity: 0.5; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }

        /* Responsive: panel 100% ancho en móvil */
        @media (max-width: 480px) {
          .chatbot-panel {
            right:  0   !important;
            bottom: 0   !important;
            width:  100vw !important;
            height: 100dvh !important;
            border-radius: 0 !important;
          }
        }
      `}</style>

      {/* ── Panel de chat (visible cuando está abierto) ── */}
      {chatbot.abierto && (
        <ChatPanel
          mensajes={chatbot.mensajes}
          inputTexto={chatbot.inputTexto}
          enviando={chatbot.enviando}
          reconociendo={chatbot.reconociendo}
          setInputTexto={chatbot.setInputTexto}
          enviarMensaje={chatbot.enviarMensaje}
          valorar={chatbot.valorar}
          leerEnVoz={chatbot.leerEnVoz}
          iniciarVoz={chatbot.iniciarVoz}
          detenerVoz={chatbot.detenerVoz}
          cerrar={chatbot.cerrar}
        />
      )}

      {/* ── Botón flotante ── */}
      <button
        onClick={chatbot.abierto ? chatbot.cerrar : chatbot.abrir}
        title="Asistente IA"
        aria-label="Abrir asistente IA"
        style={{
          position:       "fixed",
          bottom:         24,
          right:          24,
          width:          56,
          height:         56,
          borderRadius:   "50%",
          background:     "#2563eb",
          border:         "none",
          cursor:         "pointer",
          display:        "flex",
          alignItems:     "center",
          justifyContent: "center",
          boxShadow:      "0 4px 20px rgba(37,99,235,.45)",
          zIndex:         9997,
          transition:     "transform .2s, background .2s",
          // Pulso suave cuando hay mensajes no leídos y el panel está cerrado
          animation: (!chatbot.abierto && chatbot.noLeidos > 0)
            ? "chatBtnPulse 2s infinite"
            : "none",
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLButtonElement).style.transform = "scale(1.08)";
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLButtonElement).style.transform = "scale(1)";
        }}
      >
        {/* Ícono: X cuando abierto, Bot cuando cerrado */}
        {chatbot.abierto
          ? <X size={22} color="#fff" />
          : <Bot size={22} color="#fff" />
        }

        {/* Badge de mensajes no leídos */}
        {!chatbot.abierto && chatbot.noLeidos > 0 && (
          <div style={{
            position:       "absolute",
            top:            -4,
            right:          -4,
            minWidth:       18,
            height:         18,
            borderRadius:   9,
            background:     "#ef4444",
            color:          "#fff",
            fontSize:       10,
            fontWeight:     700,
            display:        "flex",
            alignItems:     "center",
            justifyContent: "center",
            padding:        "0 4px",
            border:         "2px solid var(--bg, #0f1117)",
            lineHeight:     1,
          }}>
            {chatbot.noLeidos > 9 ? "9+" : chatbot.noLeidos}
          </div>
        )}
      </button>
    </>
  );
}
