"use client";
/**
 * components/ChatbotFloating/useChatbot.ts
 * ==========================================
 * Hook principal del chatbot. Centraliza todo el estado y la lógica:
 *  - Apertura/cierre del panel
 *  - Envío de mensajes con streaming SSE
 *  - Reconocimiento de voz (SpeechRecognition)
 *  - Síntesis de voz (SpeechSynthesis)
 *  - Valoraciones (thumbs up/down)
 *  - Gestión de mensajes no leídos
 */

import { useState, useCallback, useRef } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";

// ── Tipos ─────────────────────────────────────────────────────────────────

export interface MensajeChat {
  id?: number;           // id en BD (solo mensajes del asistente guardados)
  rol: "usuario" | "asistente" | "accion";
  contenido: string;
  cargando?: boolean;    // true mientras se recibe el stream
  buscando?: boolean;    // true cuando Claude activa web_search
  accionando?: boolean;  // true mientras la herramienta agéntica se ejecuta
  herramienta?: string;  // nombre de la herramienta (para tracking de actualizaciones)
  valoracion?: number | null;
  timestamp: number;
}

export interface EstadoChatbot {
  abierto: boolean;
  mensajes: MensajeChat[];
  inputTexto: string;
  enviando: boolean;
  noLeidos: number;
  reconociendo: boolean;
  sessionId: string;
  abrir: () => void;
  cerrar: () => void;
  setInputTexto: (v: string) => void;
  enviarMensaje: (textoOpcional?: string) => Promise<void>;
  valorar: (mensajeId: number, valoracion: 1 | -1) => void;
  leerEnVoz: (texto: string) => void;
  iniciarVoz: () => void;
  detenerVoz: () => void;
}

// ── Hook ──────────────────────────────────────────────────────────────────

export function useChatbot(): EstadoChatbot {
  const api = useApi();
  const { toast } = useToast();

  // Estado del panel
  const [abierto, setAbierto]           = useState(false);
  const [mensajes, setMensajes]         = useState<MensajeChat[]>([]);
  const [inputTexto, setInputTexto]     = useState("");
  const [enviando, setEnviando]         = useState(false);
  const [noLeidos, setNoLeidos]         = useState(0);
  const [reconociendo, setReconociendo] = useState(false);

  // session_id generado una sola vez por montaje del componente
  // (nueva sesión al recargar la página — intencional)
  const [sessionId] = useState<string>(() => {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  });

  // Referencia al objeto SpeechRecognition activo
  const reconocimientoRef = useRef<any>(null);

  // ── Abrir / cerrar ────────────────────────────────────────────────────

  const abrir = useCallback(() => {
    setAbierto(true);
    setNoLeidos(0);
  }, []);

  const cerrar = useCallback(() => {
    setAbierto(false);
  }, []);

  // ── Enviar mensaje con streaming SSE ─────────────────────────────────

  const enviarMensaje = useCallback(async (textoOpcional?: string) => {
    const texto = (textoOpcional ?? inputTexto).trim();
    if (!texto || enviando) return;

    setInputTexto("");
    setEnviando(true);

    // Agregar mensaje del usuario al estado local
    const msgUsuario: MensajeChat = {
      rol: "usuario",
      contenido: texto,
      timestamp: Date.now(),
    };

    // Agregar burbuja de "cargando" para el asistente
    const placeholderId = Date.now() + 1;
    const msgBot: MensajeChat = {
      id: undefined,
      rol: "asistente",
      contenido: "",
      cargando: true,
      buscando: false,
      timestamp: placeholderId,
    };

    setMensajes(prev => [...prev, msgUsuario, msgBot]);

    // Helpers para actualizar la burbuja del asistente
    const actualizarBot = (updater: (m: MensajeChat) => MensajeChat) => {
      setMensajes(prev =>
        prev.map(m => m.timestamp === placeholderId ? updater(m) : m)
      );
    };

    try {
      // Obtener el token del localStorage (mismo patrón que extractor-gmail)
      const token = typeof window !== "undefined"
        ? localStorage.getItem("sm_token")
        : null;

      // Construir historial para enviar al backend (últimos 10 turnos)
      const historialEnviar = mensajes
        .filter(m => !m.cargando && m.contenido.trim())
        .slice(-10)
        .map(m => ({ rol: m.rol, mensaje: m.contenido }));

      const resp = await fetch(`${api.BASE}/api/chatbot/mensaje`, {
        method: "POST",
        headers: {
          "Content-Type":  "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          mensaje:    texto,
          session_id: sessionId,
          historial:  historialEnviar,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail ?? err.message ?? `Error ${resp.status}`);
      }

      // Leer el stream SSE
      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No se pudo leer la respuesta del servidor");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        // Dividir por eventos SSE completos (terminan en \n\n)
        const partes = buffer.split("\n\n");
        buffer = partes.pop() ?? "";

        for (const parte of partes) {
          if (!parte.startsWith("data: ")) continue;
          try {
            const evento = JSON.parse(parte.slice(6));

            if (evento.tipo === "texto") {
              // Acumular chunk en la burbuja del asistente
              actualizarBot(m => ({
                ...m,
                contenido: m.contenido + evento.contenido,
                cargando:  true,
                buscando:  false,
              }));
            } else if (evento.tipo === "buscando") {
              actualizarBot(m => ({ ...m, buscando: true }));
            } else if (evento.tipo === "accion") {
              const herramienta = evento.herramienta as string;
              const estado      = evento.estado as string;
              if (estado === "iniciando") {
                // Insertar burbuja de acción justo ANTES del placeholder del asistente
                const msgAccion: MensajeChat = {
                  rol:        "accion",
                  contenido:  evento.mensaje ?? "Ejecutando acción...",
                  herramienta,
                  accionando: true,
                  timestamp:  Date.now(),
                };
                setMensajes(prev => {
                  const arr = [...prev];
                  // El placeholder del asistente siempre es el último elemento
                  arr.splice(arr.length - 1, 0, msgAccion);
                  return arr;
                });
              } else if (estado === "completado") {
                // Actualizar la burbuja de acción existente con el resultado
                setMensajes(prev =>
                  prev.map(m =>
                    m.rol === "accion" && m.herramienta === herramienta
                      ? { ...m, accionando: false, contenido: evento.mensaje ?? m.contenido }
                      : m
                  )
                );
              }
            } else if (evento.tipo === "fin") {
              // Quitar estado cargando y guardar el id del mensaje
              actualizarBot(m => ({
                ...m,
                cargando:   false,
                buscando:   false,
                id:         evento.mensaje_id ?? undefined,
                valoracion: null,
              }));
              // Si el panel está cerrado, incrementar no-leídos
              if (!abierto) {
                setNoLeidos(n => n + 1);
              }
            } else if (evento.tipo === "error") {
              toast("error", evento.mensaje ?? "Error del asistente IA");
              actualizarBot(m => ({
                ...m,
                contenido: evento.mensaje ?? "Error al procesar tu consulta.",
                cargando:  false,
                buscando:  false,
              }));
            }
          } catch {
            /* Ignorar líneas SSE malformadas */
          }
        }
      }
    } catch (err: any) {
      const msgError = err.message ?? "Error de conexión con el asistente";
      toast("error", msgError);
      actualizarBot(m => ({
        ...m,
        contenido: "No pude procesar tu consulta. Por favor intenta de nuevo.",
        cargando:  false,
        buscando:  false,
      }));
    } finally {
      setEnviando(false);
    }
  }, [inputTexto, enviando, mensajes, sessionId, api.BASE, abierto, toast]);

  // ── Valorar un mensaje ────────────────────────────────────────────────

  const valorar = useCallback((mensajeId: number, valoracion: 1 | -1) => {
    // Actualizar UI inmediatamente (optimistic update)
    setMensajes(prev =>
      prev.map(m => m.id === mensajeId ? { ...m, valoracion } : m)
    );
    // Enviar al backend (fire-and-forget)
    api.apiFetch("/api/chatbot/valoracion", {
      method: "POST",
      body: JSON.stringify({ mensaje_id: mensajeId, valoracion }),
    }).catch(() => {
      toast("error", "No se pudo guardar la valoración");
    });
  }, [api, toast]);

  // ── Síntesis de voz (TTS) ─────────────────────────────────────────────

  const leerEnVoz = useCallback((texto: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      toast("error", "Tu navegador no soporta síntesis de voz");
      return;
    }
    // Cancelar cualquier lectura en curso
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(texto);
    utterance.lang = "es-CO";
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  }, [toast]);

  // ── Reconocimiento de voz (STT) ───────────────────────────────────────

  const iniciarVoz = useCallback(() => {
    if (typeof window === "undefined") return;
    const SR = (window as any).SpeechRecognition
            || (window as any).webkitSpeechRecognition;
    if (!SR) {
      toast("error", "Tu navegador no soporta reconocimiento de voz. Usa Chrome.");
      return;
    }
    if (reconociendo) return;

    const rec = new SR();
    rec.lang = "es-CO";
    rec.continuous = false;
    rec.interimResults = false;

    rec.onresult = (e: any) => {
      const transcripcion = e.results[0]?.[0]?.transcript ?? "";
      if (transcripcion) setInputTexto(transcripcion);
    };
    rec.onerror = () => {
      setReconociendo(false);
      toast("error", "Error en el reconocimiento de voz");
    };
    rec.onend = () => setReconociendo(false);

    reconocimientoRef.current = rec;
    rec.start();
    setReconociendo(true);
  }, [reconociendo, toast]);

  const detenerVoz = useCallback(() => {
    reconocimientoRef.current?.stop();
    setReconociendo(false);
  }, []);

  return {
    abierto, mensajes, inputTexto, enviando, noLeidos, reconociendo, sessionId,
    abrir, cerrar, setInputTexto,
    enviarMensaje, valorar, leerEnVoz, iniciarVoz, detenerVoz,
  };
}
