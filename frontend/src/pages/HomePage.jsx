import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, MessageCircle, Clock, LogOut } from 'lucide-react';
import { useLiveKit } from '../hooks/useLiveKit';
import { useAuth } from '../hooks/useAuth';
import {
  Header, LandingScreen, ConversationScreen,
} from '../components/AssistantUI';

// ─── Mobile bottom tab bar ───────────────────────────────────────────────────
function MobileTabBar({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'home',    label: 'Home',    Icon: Home },
    { id: 'chat',    label: 'Chat',    Icon: MessageCircle },
    { id: 'history', label: 'History', Icon: Clock },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-[#E2E8F0] flex z-30 safe-area-bottom shadow-lg">
      {tabs.map(({ id, label, Icon }) => {
        const active = activeTab === id;
        return (
          <button
            key={id}
            id={`tab-${id}`}
            onClick={() => onTabChange(id)}
            className={`flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors ${
              active ? 'text-[#2B6CB0]' : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Icon className="w-5 h-5" />
            <span className={`text-[10px] font-medium ${active ? 'text-[#2B6CB0]' : ''}`}>{label}</span>
            {active && <span className="w-1 h-1 rounded-full bg-[#2B6CB0] mt-0.5" />}
          </button>
        );
      })}
    </nav>
  );
}

export default function HomePage() {
  const [view, setView] = useState('landing');
  const [isTyping, setIsTyping] = useState(false);
  const [voiceProvider, setVoiceProvider] = useState('deepgram');
  const [mobileTab, setMobileTab] = useState('home');
  const { logout } = useAuth();
  const navigate = useNavigate();

  const { disconnect, toggleMic, sendText, isListening, transcript, error, isConnected } =
    useLiveKit(voiceProvider);

  const handleSendText = async (text) => {
    if (view === 'landing') setView('conversation');
    setMobileTab('chat');
    setIsTyping(true);
    await sendText(text);
    setIsTyping(false);
  };

  const handleStartVoice = async () => {
    setView('conversation');
    setMobileTab('chat');
    await toggleMic();
  };

  const handleEndSession = async () => {
    await disconnect({ clearChat: true });
    setView('landing');
    setMobileTab('home');
  };

  const handleTabChange = (tab) => {
    setMobileTab(tab);
    if (tab === 'history') {
      navigate('/history');
    } else if (tab === 'home') {
      setView('landing');
    } else if (tab === 'chat') {
      if (view === 'landing') setView('conversation');
    }
  };

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="min-h-screen flex flex-col">
      <Header isListening={isListening} />

      <div className="flex-1 flex flex-col">
        {/* Voice provider selector — desktop only */}
        <div className="hidden md:flex px-4 py-2 items-center justify-end gap-2 border-b border-[#E2E8F0] bg-white">
          <span className="text-xs text-slate-400">Voice provider:</span>
          <select
            value={voiceProvider}
            onChange={(e) => setVoiceProvider(e.target.value)}
            className="text-xs border border-[#E2E8F0] rounded-lg px-2 py-1"
            disabled={isConnected}
          >
            <option value="deepgram">Deepgram — English STT + TTS</option>
            <option value="sarvam">Sarvam — Hindi STT + TTS</option>
            <option value="elevenlabs">ElevenLabs — English STT + TTS</option>
          </select>
          <button onClick={handleLogout} className="ml-4 text-xs text-red-400 hover:text-red-600 font-medium flex items-center gap-1">
            <LogOut className="w-3 h-3" /> Sign out
          </button>
        </div>

        {error && (
          <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error.includes('LiveKit') || error.includes('503')
              ? 'Voice connection unavailable. You can still use text input.'
              : error}
          </div>
        )}

        {view === 'landing' ? (
          <LandingScreen
            onStartVoice={handleStartVoice}
            onSendText={handleSendText}
            isListening={isListening}
          />
        ) : (
          <ConversationScreen
            transcript={transcript}
            isListening={isListening}
            isTyping={isTyping}
            onToggleMic={toggleMic}
            onSendText={handleSendText}
            onEndSession={handleEndSession}
          />
        )}
      </div>

      {/* Mobile bottom tab bar */}
      <MobileTabBar activeTab={mobileTab} onTabChange={handleTabChange} />
    </div>
  );
}
