import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Clock, MessageCircle, ChevronDown, ChevronUp, Pill, CheckCircle, Loader2 } from 'lucide-react';
import { getHistory, getHistoryDetail } from '../api/client';

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function SessionCard({ session }) {
  const [expanded, setExpanded] = useState(false);
  const { data: detail, isLoading } = useQuery({
    queryKey: ['history-detail', session.id],
    queryFn: () => getHistoryDetail(session.id),
    enabled: expanded,
    staleTime: 60_000,
  });

  return (
    <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-sm overflow-hidden transition-all hover:shadow-md">
      <button
        className="w-full text-left p-4 flex items-start gap-3"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Icon */}
        <div className="w-10 h-10 rounded-xl bg-[#EBF8FF] flex items-center justify-center flex-shrink-0 mt-0.5">
          <Pill className="w-5 h-5 text-[#2B6CB0]" />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-[#1A365D] truncate">
              {session.medicine_name || 'Voice Session'}
            </span>
            <span className={`flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
              session.status === 'completed'
                ? 'bg-green-100 text-green-700'
                : 'bg-amber-100 text-amber-700'
            }`}>
              {session.status === 'completed' ? 'Completed' : 'In Progress'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDate(session.started_at)}
          </p>
          {session.summary && (
            <p className="text-sm text-slate-500 mt-1.5 line-clamp-2">{session.summary}</p>
          )}
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
            <span className="flex items-center gap-1">
              <MessageCircle className="w-3 h-3" />
              {session.message_count} messages
            </span>
          </div>
        </div>

        {/* Expand arrow */}
        <div className="text-slate-400 flex-shrink-0 mt-1">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded messages */}
      {expanded && (
        <div className="border-t border-[#E2E8F0] bg-[#F7FAFC] px-4 py-3 max-h-80 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-6 text-slate-400">
              <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading messages…
            </div>
          ) : detail?.messages?.length ? (
            <div className="space-y-2">
              {detail.messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-[#EBF8FF] text-[#1A365D] rounded-br-md border border-[#2B6CB0]/20'
                      : 'bg-[#FDF6E3] text-[#1A365D] rounded-bl-md'
                  }`}>
                    <div className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 mb-0.5">
                      {msg.role === 'user' ? 'You' : 'Assistant'}
                    </div>
                    {msg.content}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400 text-center py-4">No messages in this session.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function HistoryPage() {
  const { data: sessions, isLoading, isError } = useQuery({
    queryKey: ['history'],
    queryFn: getHistory,
    staleTime: 30_000,
  });

  return (
    <div className="flex-1 flex flex-col max-w-2xl mx-auto w-full px-4 py-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-[#2B6CB0] flex items-center justify-center">
          <Clock className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#1A365D]">Chat History</h1>
          <p className="text-xs text-slate-400">Your past medicine consultations</p>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin mr-2" /> Loading history…
        </div>
      )}

      {isError && (
        <div className="text-center py-12 text-red-400">
          Failed to load history. Please try again.
        </div>
      )}

      {!isLoading && !isError && sessions?.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-[#EBF8FF] flex items-center justify-center mx-auto mb-4">
            <MessageCircle className="w-8 h-8 text-[#2B6CB0]/50" />
          </div>
          <h3 className="font-semibold text-[#1A365D] mb-1">No sessions yet</h3>
          <p className="text-sm text-slate-400">Start a voice session and it'll appear here.</p>
        </div>
      )}

      <div className="space-y-3">
        {sessions?.map((session) => (
          <SessionCard key={session.id} session={session} />
        ))}
      </div>
    </div>
  );
}
