"use client";
/**
 * components/ChatbotFloating/ChatInput.tsx
 * ==========================================
 * Área de entrada del chat:
 *  - Textarea que se expande automáticamente (máx. 120px)
 *  - Enter para enviar, Shift+Enter para salto de línea
 *  - Botón micrófono (rojo cuando está escuchando)
 *  - Botón enviar (deshabilitado si está vacío o enviando)
 */

import { useRef, useEffect } from "react";
import { Send, Mic, MicOff, Loader2 } from "lucide-react";

interface Props {
  valor: string;
  onChange: (v: string) => void;
  onEnviar: () => void;
  onMicrofono: () => void;
  onDetenerMic: () => void;
  enviando: boolean;
  reconociendo: boolean;
}

export default function ChatInput({
  valor, onChange, onEnviar, onMicrofono, onDetenerMic,
  enviando, reconociendo,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-expansión del textarea
  const ajustarAltura = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  useEffect(() => {
    ajustarAltura();
  }, [valor]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!enviando && valor.trim()) onEnviar();
    }
  };

  return (
    <div style={{
      padding:      "10px 12px",
      borderTop:    "1px solid var(--border)",
      display:      "flex",
      alignItems:   "flex-end",
      gap:          8,
      background:   "var(--surface, #161b27)",
      borderRadius: "0 0 var(--r-lg) var(--r-lg)",
    }}>
      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={valor}
        onChange={e => { onChange(e.target.value); ajustarAltura(); }}
        onKeyDown={handleKeyDown}
        placeholder="Escríbeme o usa el micrófono..."
        rows={1}
        disabled={enviando}
        style={{
          flex:       1,
          resize:     "none",
          background: "rgba(255,255,255,.05)",
          border:     "1px solid var(--border)",
          borderRadius: "var(--r-sm)",
          padding:    "8px 10px",
          color:      "var(--text)",
          fontSize:   13,
          fontFamily: "var(--font-sans, sans-serif)",
          lineHeight: 1.5,
          outline:    "none",
          overflow:   "hidden",
          minHeight:  36,
          maxHeight:  120,
          transition: "border-color .15s",
        }}
      />

      {/* Botón micrófono */}
      <button
        type="button"
        onClick={reconociendo ? onDetenerMic : onMicrofono}
        title={reconociendo ? "Detener escucha" : "Activar micrófono"}
        disabled={enviando}
        style={{
          width:        36,
          height:       36,
          borderRadius: "50%",
          background:   reconociendo
            ? "rgba(239,68,68,.15)"
            : "rgba(255,255,255,.06)",
          border:       `1px solid ${reconociendo
            ? "rgba(239,68,68,.3)"
            : "var(--border)"}`,
          display:      "flex",
          alignItems:   "center",
          justifyContent: "center",
          cursor:       enviando ? "not-allowed" : "pointer",
          flexShrink:   0,
          transition:   "all .15s",
          // Pulso cuando está escuchando
          animation:    reconociendo ? "chatMicPulse 1s infinite" : "none",
        }}
      >
        {reconociendo
          ? <MicOff size={15} color="#f87171" />
          : <Mic size={15} color="#64748b" />
        }
      </button>

      {/* Botón enviar */}
      <button
        type="button"
        onClick={onEnviar}
        disabled={enviando || !valor.trim()}
        title="Enviar mensaje"
        style={{
          width:          36,
          height:         36,
          borderRadius:   "50%",
          background:     (enviando || !valor.trim())
            ? "rgba(37,99,235,.1)"
            : "rgba(37,99,235,.2)",
          border:         "1px solid rgba(37,99,235,.3)",
          display:        "flex",
          alignItems:     "center",
          justifyContent: "center",
          cursor:         (enviando || !valor.trim()) ? "not-allowed" : "pointer",
          flexShrink:     0,
          transition:     "all .15s",
          opacity:        (enviando || !valor.trim()) ? 0.5 : 1,
        }}
      >
        {enviando
          ? <Loader2 size={14} color="#93c5fd" style={{ animation: "spin 1s linear infinite" }} />
          : <Send size={14} color="#93c5fd" />
        }
      </button>
    </div>
  );
}
