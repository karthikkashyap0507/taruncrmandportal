"use client";

import { useState, useRef, useEffect } from "react";
import { Bot, ChevronDown, MessageCircle, Send, Sparkles, Trash2, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  powered_by?: string;
}

const QUICK_REPLIES = [
  "How do I apply for jobs?",
  "Tips for my resume",
  "How does ATS work?",
  "Salary negotiation tips",
  "Interview preparation",
  "Best skills to learn in 2024",
];

export function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hi! 👋 I'm your AI career assistant at **JobsNexGen**. I can help you find jobs, improve your resume, prep for interviews, and more!\n\nWhat can I help you with today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [convId] = useState(() => `conv_${Date.now()}`);
  const [unreadCount, setUnreadCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  useEffect(() => {
    if (isOpen) {
      setUnreadCount(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSend = async (text?: string) => {
    const message = (text || input).trim();
    if (!message || isTyping) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: message };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const { data } = await api.post<{ reply: string; conversation_id: string; powered_by: string }>(
        "/chatbot/message",
        { message, conversation_id: convId }
      );
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.reply,
        powered_by: data.powered_by,
      };
      setMessages((prev) => [...prev, botMsg]);
      if (!isOpen) setUnreadCount((n) => n + 1);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", content: "I'm having trouble connecting right now. Please make sure the backend is running!" },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const clearChat = async () => {
    try { await api.delete(`/chatbot/conversation/${convId}`); } catch {}
    setMessages([{
      id: Date.now().toString(), role: "assistant",
      content: "Chat cleared! How can I help you? 😊",
    }]);
  };

  const formatMessage = (text: string) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br/>")
      .replace(/•/g, "•");
  };

  return (
    <>
      {/* FAB Button */}
      <button
        onClick={() => { setIsOpen(!isOpen); setIsMinimized(false); }}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] text-white shadow-2xl hover:scale-110 transition-all duration-200"
      >
        {isOpen ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
        {!isOpen && unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-96 max-w-[calc(100vw-2rem)] rounded-2xl border border-white/10 bg-[#0F172A]/98 shadow-2xl backdrop-blur-xl flex flex-col"
          style={{ height: isMinimized ? "auto" : "520px" }}>

          {/* Header */}
          <div className="flex items-center justify-between rounded-t-2xl border-b border-white/10 bg-gradient-to-r from-[#3B82F6]/10 to-[#8B5CF6]/10 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6]">
                <Bot className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">AI Career Assistant</p>
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
                  <p className="text-xs text-[#94A3B8]">Online</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={clearChat} className="rounded p-1.5 text-[#94A3B8] hover:bg-white/10 hover:text-white transition-colors" title="Clear chat">
                <Trash2 className="h-3.5 w-3.5" />
              </button>
              <button onClick={() => setIsMinimized(!isMinimized)} className="rounded p-1.5 text-[#94A3B8] hover:bg-white/10 hover:text-white transition-colors">
                <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isMinimized ? "rotate-180" : ""}`} />
              </button>
              <button onClick={() => setIsOpen(false)} className="rounded p-1.5 text-[#94A3B8] hover:bg-white/10 hover:text-white transition-colors">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {!isMinimized && (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    {msg.role === "assistant" && (
                      <div className="mr-2 mt-1 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6]">
                        <Sparkles className="h-3 w-3 text-white" />
                      </div>
                    )}
                    <div className={`max-w-[80%] ${msg.role === "user"
                      ? "rounded-2xl rounded-br-sm bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] px-4 py-2.5 text-white"
                      : "rounded-2xl rounded-bl-sm bg-white/8 px-4 py-2.5 text-white"}`}>
                      <p className="text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }} />
                      {msg.powered_by && (
                        <p className="mt-1 text-[10px] opacity-50">{msg.powered_by}</p>
                      )}
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="mr-2 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6]">
                      <Sparkles className="h-3 w-3 text-white" />
                    </div>
                    <div className="rounded-2xl rounded-bl-sm bg-white/8 px-4 py-3">
                      <div className="flex gap-1">
                        <span className="h-2 w-2 rounded-full bg-[#94A3B8] animate-bounce" style={{ animationDelay: "0ms" }} />
                        <span className="h-2 w-2 rounded-full bg-[#94A3B8] animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="h-2 w-2 rounded-full bg-[#94A3B8] animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick Replies */}
              {messages.length <= 2 && (
                <div className="px-4 pb-2">
                  <p className="mb-2 text-xs text-[#64748B]">Quick questions:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {QUICK_REPLIES.map((q) => (
                      <button key={q} onClick={() => handleSend(q)}
                        className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[#94A3B8] hover:border-[#3B82F6]/50 hover:text-[#3B82F6] transition-colors">
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input */}
              <div className="border-t border-white/10 p-3">
                <div className="flex gap-2">
                  <Input
                    ref={inputRef}
                    placeholder="Ask me anything about jobs..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                    className="flex-1 border-white/10 bg-white/5 text-white placeholder:text-[#64748B] text-sm"
                  />
                  <Button
                    onClick={() => handleSend()}
                    disabled={!input.trim() || isTyping}
                    size="sm"
                    className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] px-3"
                  >
                    {isTyping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
