import React, { useEffect, useRef, useState } from "react";
import { AlertTriangle, Mic, Send, Square, Volume2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import api, { getBaseUrl } from "../../api/api";
import { formatDateTime } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

const quickPrompts = ["Wound status", "Medicine reminder", "Pain today", "Contact doctor", "I have fever and severe pain"];

export default function VoiceAssistant() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [lastCommand, setLastCommand] = useState(null);
  const [error, setError] = useState("");
  const endRef = useRef(null);
  const recorderRef = useRef(null);
  const recognitionRef = useRef(null);
  const chunksRef = useRef([]);

  const load = () => {
    setLoading(true);
    api
      .get("/patients/me/voice-assistant/messages")
      .then((response) => setMessages(response.data.messages || []))
      .catch((err) => setError(err.response?.data?.detail || "Unable to load assistant history."))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const playAssistantAudio = (audioUrl) => {
    if (!audioUrl) return;
    const url = audioUrl.startsWith("http") ? audioUrl : `${getBaseUrl()}${audioUrl}`;
    const audio = new Audio(url);
    audio.play().catch(() => {});
  };

  const applyCommandResult = (data) => {
    if (data.message_log) {
      setMessages((current) => [...current, data.message_log]);
    }
    setLastCommand(data);
    playAssistantAudio(data.audio_url);
    const route = data.result?.route || data.command?.route;
    if (route && route !== "/patient/voice-assistant") {
      setTimeout(() => navigate(route), 650);
    }
  };

  const send = async (message = input) => {
    if (!message.trim()) return;
    setSending(true);
    setError("");
    try {
      const response = await api.post("/patients/me/voice-command/text", { message, speak: true });
      applyCommandResult(response.data);
      setInput("");
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to send message.");
    } finally {
      setSending(false);
    }
  };

  const sendAudio = async (blob) => {
    setSending(true);
    setError("");
    const form = new FormData();
    form.append("file", blob, "voice-command.webm");
    form.append("speak", "true");
    try {
      const response = await api.post("/patients/me/voice-command/audio", form);
      applyCommandResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to process voice command.");
    } finally {
      setSending(false);
    }
  };

  const startRecording = async () => {
    setError("");
    setLastCommand(null);
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.continuous = false;
      recognitionRef.current = recognition;
      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0]?.transcript || "")
          .join(" ")
          .trim();
        setRecording(false);
        if (transcript) {
          send(transcript);
        } else {
          setError("I could not hear a command. Please try again.");
        }
      };
      recognition.onerror = () => {
        setRecording(false);
        setError("Speech recognition failed. Please try again or type the command.");
      };
      recognition.onend = () => {
        setRecording(false);
      };
      recognition.start();
      setRecording(true);
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Microphone recording is not supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size > 0) sendAudio(blob);
      };
      recorder.start();
      setRecording(true);
    } catch (err) {
      setError("Microphone permission was denied or unavailable.");
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
    }
    setRecording(false);
  };

  return (
    <AppShell role="patient" title="Voice Assistant">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 text-center shadow-sm">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-[#ebf2ec] text-[#061907]">
            <Mic size={34} />
          </div>
          <h2 className="mt-4 text-xl font-bold text-[#061907]">Ask about your recovery</h2>
          <p className="mt-1 text-sm text-[#667064]">Speak commands, hear responses, and move through recovery tools hands-free.</p>
          <div className="mt-5 flex flex-wrap justify-center gap-3">
            <button
              type="button"
              onClick={recording ? stopRecording : startRecording}
              disabled={sending}
              className={`inline-flex items-center gap-2 rounded-lg px-5 py-3 text-sm font-bold text-white disabled:opacity-60 ${recording ? "bg-red-700 hover:bg-red-800" : "bg-[#061907] hover:bg-[#153315]"}`}
            >
              {recording ? <Square size={17} /> : <Mic size={17} />}
              {recording ? "Stop Listening" : "Start Voice Command"}
            </button>
            {lastCommand?.audio_url && (
              <button
                type="button"
                onClick={() => playAssistantAudio(lastCommand.audio_url)}
                className="inline-flex items-center gap-2 rounded-lg border border-[#d8d2c8] px-5 py-3 text-sm font-bold text-[#061907] hover:bg-[#ebf2ec]"
              >
                <Volume2 size={17} />
                Replay
              </button>
            )}
          </div>
          {recording && <p className="mt-3 text-sm font-semibold text-red-700">Listening...</p>}
        </section>

        <section className="min-h-[420px] rounded-xl border border-[#e4dfd7] bg-white p-5 shadow-sm">
          {loading ? (
            <div>Loading conversation...</div>
          ) : messages.length ? (
            <div className="space-y-5">
              {messages.map((message) => (
                <article key={message.id} className="space-y-3">
                  <Bubble side="right" label="You" text={message.user_message} time={message.created_at} />
                  <Bubble side="left" label="Assistant" text={message.assistant_response} time={message.created_at} urgent={message.urgency === "urgent"} />
                </article>
              ))}
              <div ref={endRef} />
            </div>
          ) : (
            <EmptyState title="No assistant messages yet" message="Ask about wound status, pain, reminders, or contacting your doctor." />
          )}
        </section>

        <section className="rounded-xl border border-[#e4dfd7] bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-wrap gap-2">
            {quickPrompts.map((prompt) => (
              <button key={prompt} onClick={() => send(prompt)} disabled={sending} className="rounded-full border border-[#d8d2c8] px-4 py-2 text-sm font-semibold text-[#4d574b] hover:bg-[#ebf2ec]">
                {prompt}
              </button>
            ))}
          </div>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              send();
            }}
            className="flex gap-3"
          >
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              className="min-w-0 flex-1 rounded-lg border border-[#d8d2c8] bg-[#fdf9f3] px-4 py-3 text-sm"
              placeholder="Type a command, or use the microphone above"
            />
            <button disabled={sending} className="inline-flex items-center gap-2 rounded-lg bg-[#061907] px-5 py-3 text-sm font-bold text-white disabled:opacity-60">
              <Send size={17} />
              Send
            </button>
          </form>
          {lastCommand?.transcript && (
            <div className="mt-3 rounded-lg border border-[#e4dfd7] bg-[#f8f4ee] p-3 text-sm text-[#4d574b]">
              <span className="font-semibold text-[#061907]">Command:</span> {lastCommand.transcript}
            </div>
          )}
          {error && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
        </section>
      </div>
    </AppShell>
  );
}

function Bubble({ side, label, text, time, urgent = false }) {
  const right = side === "right";
  return (
    <div className={`flex flex-col ${right ? "items-end" : "items-start"}`}>
      <div className={`max-w-[85%] rounded-xl p-4 text-sm shadow-sm ${right ? "bg-[#dfe9db] text-[#061907]" : urgent ? "bg-red-50 text-red-900 border border-red-200" : "bg-[#f8f4ee] text-[#061907]"}`}>
        {urgent && (
          <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-red-700">
            <AlertTriangle size={15} />
            Urgent alert created
          </div>
        )}
        {text}
      </div>
      <span className="mt-1 text-xs text-[#667064]">{label} • {formatDateTime(time)}</span>
    </div>
  );
}
