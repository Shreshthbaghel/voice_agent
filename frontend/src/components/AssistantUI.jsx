import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, Keyboard, Menu, X, Home, Clock, LogOut, Stethoscope } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

// ─── Desktop Drawer ──────────────────────────────────────────────────────────
function NavDrawer({ open, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const go = (path) => { navigate(path); onClose(); };
  const handleLogout = () => { logout(); navigate('/login'); onClose(); };

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 md:block hidden"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div className={`fixed top-0 left-0 h-full w-72 bg-white shadow-2xl z-50 transition-transform duration-300 ease-out hidden md:flex flex-col ${
        open ? 'translate-x-0' : '-translate-x-full'
      }`}>
        {/* Header */}
        <div className="bg-gradient-to-br from-[#1A365D] to-[#2B6CB0] p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <Stethoscope className="w-6 h-6" />
              <span className="font-bold text-lg">Voice Health</span>
            </div>
            <button onClick={onClose} className="p-1 rounded-lg hover:bg-white/20 transition">
              <X className="w-5 h-5" />
            </button>
          </div>
          {user && (
            <div>
              <p className="font-medium">{user.name}</p>
              <p className="text-white/70 text-sm">{user.email}</p>
            </div>
          )}
        </div>

        {/* Nav items */}
        <nav className="flex-1 p-4 space-y-1">
          <button
            onClick={() => go('/')}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[#1A365D] hover:bg-[#EBF8FF] transition font-medium text-sm"
          >
            <Home className="w-5 h-5 text-[#2B6CB0]" />
            Home
          </button>
          <button
            onClick={() => go('/history')}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[#1A365D] hover:bg-[#EBF8FF] transition font-medium text-sm"
          >
            <Clock className="w-5 h-5 text-[#2B6CB0]" />
            Chat History
          </button>
        </nav>

        {/* Logout */}
        <div className="p-4 border-t border-[#E2E8F0]">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-500 hover:bg-red-50 transition font-medium text-sm"
          >
            <LogOut className="w-5 h-5" />
            Sign out
          </button>
        </div>
      </div>
    </>
  );
}

// ─── Header ──────────────────────────────────────────────────────────────────
export function Header({ isListening }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      <NavDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <header className="bg-white border-b border-[#E2E8F0] px-4 md:px-8 py-4 z-30 relative">
        <div className="w-full flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {/* Hamburger — desktop only */}
            <button
              id="nav-menu-btn"
              onClick={() => setDrawerOpen(true)}
              className="hidden md:flex w-9 h-9 rounded-lg items-center justify-center text-[#1A365D] hover:bg-[#EBF8FF] transition"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="w-8 h-8 rounded-lg bg-[#2B6CB0] flex items-center justify-center text-white font-bold text-sm">VH</div>
            <span className="font-semibold text-[#1A365D] text-lg hidden sm:inline">Voice Health Assistant</span>
          </div>
          <div className="flex items-center gap-3">
            {isListening ? (
              <span className="flex items-center gap-2 text-sm text-green-600 font-medium">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" /> Listening
              </span>
            ) : (
              <span className="text-sm text-slate-400">Ready</span>
            )}
          </div>
        </div>
      </header>
    </>
  );
}

// ─── Chat bubble helpers ─────────────────────────────────────────────────────
function transcriptLabel(role, source, final = true) {
  if (source === 'stt') return final ? 'Captured transcript (STT)' : 'Captured transcript (STT) · listening…';
  if (source === 'tts') return final ? 'Assistant reply (TTS)' : 'Assistant reply (TTS) · speaking…';
  return role === 'user' ? 'You' : 'Assistant';
}

export function ChatBubble({ role, content, source = 'text', final = true }) {
  const isUser = role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[85%] md:max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
        isUser ? 'bg-[#EBF8FF] border border-[#2B6CB0]/20 text-[#1A365D] rounded-br-md'
               : 'bg-[#FDF6E3] text-[#1A365D] rounded-bl-md shadow-sm'
      } ${!final ? 'opacity-90' : ''}`}>
        <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1">
          {transcriptLabel(role, source, final)}
        </div>
        <div>
          {content}
          {!final && (
            <span className="inline-block w-1.5 h-4 ml-0.5 align-middle bg-[#2B6CB0]/70 animate-pulse" />
          )}
        </div>
      </div>
    </div>
  );
}

export function DisclaimerBanner() {
  return (
    <div className="text-center text-xs text-slate-500 bg-[#F7FAFC] border border-[#E2E8F0] rounded-lg px-4 py-2 mb-4">
      Demo assistant for medicine information only — not a substitute for professional medical advice.
    </div>
  );
}

export function MicButton({ active, large, onClick }) {
  const size = large ? 'w-20 h-20' : 'w-14 h-14';
  return (
    <button onClick={onClick}
      className={`${size} rounded-full flex items-center justify-center text-white transition-all shadow-lg ${
        active ? 'bg-red-500 hover:bg-red-600 ring-4 ring-red-200' : 'bg-[#2B6CB0] hover:bg-[#1A365D]'
      }`}>
      <Mic className={large ? 'w-8 h-8' : 'w-6 h-6'} />
    </button>
  );
}

export function LandingScreen({ onStartVoice, onSendText, isListening }) {
  const prompts = [
    { icon: '💊', title: 'Meds Info', desc: 'Get detailed information about dosage, side effects, and precautions for any medication.', example: 'What are the side effects of Metformin?' },
    { icon: '🔍', title: 'Check Medicine', desc: 'Verify interactions between two or more drugs.', example: 'Tell me about Paracetamol' },
    { icon: '📋', title: 'Prescription Check', desc: 'Analyze your current prescription for risks.', example: 'Does Amoxicillin need a prescription?' },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 md:py-16 pb-24 md:pb-16">
      <div className="text-center max-w-lg mb-8">
        <div className="hidden md:flex justify-center mb-8">
          <button onClick={onStartVoice}
            className="w-32 h-32 rounded-full bg-[#2B6CB0] text-white flex items-center justify-center shadow-lg hover:bg-[#1A365D] hover:scale-105 transition-all">
            <Mic className="w-14 h-14" />
          </button>
        </div>
        <h1 className="text-2xl md:text-3xl font-bold text-[#1A365D] mb-3">How can I help you today?</h1>
        <p className="text-slate-500 text-sm md:text-base">Tap the mic or type a medicine name below.</p>
      </div>

      {/* Feature cards — desktop */}
      <div className="hidden md:grid grid-cols-3 gap-4 w-full max-w-3xl mb-8">
        {prompts.map((p) => (
          <button key={p.title} onClick={() => onSendText(p.example)}
            className="bg-white rounded-xl border border-[#E2E8F0] p-5 text-left shadow-sm hover:shadow-md hover:border-[#2B6CB0]/40 transition-all group">
            <span className="text-2xl mb-2 block">{p.icon}</span>
            <h3 className="font-semibold text-[#1A365D] mb-1">{p.title}</h3>
            <p className="text-sm text-slate-500">{p.desc}</p>
          </button>
        ))}
      </div>

      {/* Feature cards — mobile (matches reference image) */}
      <div className="md:hidden w-full max-w-sm space-y-3 mb-6">
        {prompts.map((p) => (
          <button key={p.title} onClick={() => onSendText(p.example)}
            className="w-full bg-white rounded-2xl border border-[#E2E8F0] p-4 text-left shadow-sm active:scale-95 transition-all flex items-start gap-3">
            <span className="text-2xl w-10 h-10 rounded-xl bg-[#EBF8FF] flex items-center justify-center flex-shrink-0 text-base">{p.icon}</span>
            <div>
              <div className="font-semibold text-[#1A365D] text-sm">{p.title}</div>
              <div className="text-xs text-slate-500 mt-0.5">{p.desc}</div>
            </div>
          </button>
        ))}
      </div>

      <form className="w-full max-w-md flex gap-2" onSubmit={(e) => {
        e.preventDefault();
        const input = e.currentTarget.elements.namedItem('medicine');
        if (input.value.trim()) { onSendText(input.value.trim()); input.value = ''; }
      }}>
        <input name="medicine" type="text" placeholder="Ask about Aspirin, Insulin…"
          className="flex-1 rounded-full border border-[#E2E8F0] px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B6CB0]/30" />
        <button type="submit" className="rounded-full bg-[#2B6CB0] text-white px-5 py-2.5 text-sm font-medium">Ask</button>
      </form>

      {/* Mobile floating mic */}
      <div className="md:hidden fixed bottom-20 left-0 right-0 flex justify-center pointer-events-none">
        <div className="pointer-events-auto">
          <MicButton large active={isListening} onClick={onStartVoice} />
        </div>
      </div>
    </div>
  );
}

export function ConversationScreen({ transcript, isListening, isTyping, onToggleMic, onSendText, onEndSession }) {
  const [showInput, setShowInput] = useState(false);
  const [text, setText] = useState('');
  const bottomRef = useRef(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [transcript, isTyping]);

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full pb-16 md:pb-0">
      <div className="flex-1 overflow-y-auto px-4 py-4 md:px-0">
        <DisclaimerBanner />
        {transcript.map((entry, index) => (
          <ChatBubble
            key={`${entry.id}-${index}`}
            role={entry.role}
            content={entry.content}
            source={entry.source}
            final={entry.final !== false}
          />
        ))}
        {isTyping && (
          <div className="flex justify-start mb-4">
            <div className="bg-[#FDF6E3] rounded-2xl px-4 py-3 flex gap-1">
              {[0, 150, 300].map((d) => (
                <span key={d} className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-[#E2E8F0] bg-white px-4 py-4 md:px-0">
        {showInput && (
          <form className="flex gap-2 mb-4" onSubmit={(e) => {
            e.preventDefault();
            if (text.trim()) { onSendText(text.trim()); setText(''); }
          }}>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your message…"
              className="flex-1 rounded-full border border-[#E2E8F0] px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B6CB0]/30" autoFocus />
            <button type="submit" className="rounded-full bg-[#2B6CB0] text-white px-4 py-2 text-sm">Send</button>
          </form>
        )}
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400 hidden md:inline">
            {isListening ? 'Current Focus: Medicine Information' : 'Tap mic to speak'}
          </span>
          <div className="flex items-center gap-4 mx-auto md:mx-0">
            <button onClick={() => setShowInput(!showInput)} className="p-2 text-slate-400 hover:text-[#1A365D]"><Keyboard className="w-5 h-5" /></button>
            <MicButton active={isListening} onClick={onToggleMic} />
          </div>
          <button onClick={onEndSession} className="hidden md:inline text-sm text-red-400 hover:text-red-600 font-medium">End Session</button>
        </div>
      </div>
    </div>
  );
}
