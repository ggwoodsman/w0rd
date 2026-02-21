import { useState, useEffect, useRef, useCallback, Component } from 'react';
import { Sprout, Sun, Cloud, Snowflake, Heart, Brain, Zap, TreePine, Flower2, Activity, Send, ChevronDown, ChevronUp, Sparkles, Shield, Bug, Cpu, Radio, X, PanelRightOpen, PanelRightClose, Search, Bell, Check, XCircle, Filter, Eye, MessageCircle, BookOpen, Target, User, Smile, HelpCircle, AlertTriangle, Star } from 'lucide-react';
import { api } from './api';
import NeuralViz from './NeuralViz';
import * as sfx from './SoundEngine';

// ── Error Boundary ──────────────────────────────────────────────
class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, info) { console.error('ErrorBoundary caught:', error, info); }
  render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 bg-black flex items-center justify-center">
          <div className="text-center max-w-md p-8">
            <Bug size={48} className="text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
            <p className="text-white/50 text-sm mb-4">{this.state.error?.message || 'Unknown error'}</p>
            <button onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white text-sm transition-colors">Reload</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── WebSocket with reconnection ─────────────────────────────────
function useReconnectingWebSocket(path, onMessage) {
  const wsRef = useRef(null);
  const retryRef = useRef(1);
  const mountedRef = useRef(true);
  const onMessageRef = useRef(onMessage);
  useEffect(() => { onMessageRef.current = onMessage; });

  useEffect(() => {
    mountedRef.current = true;
    let timer = null;

    function connect() {
      if (!mountedRef.current) return;
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${window.location.host}${path}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WS ${path} connected`);
        retryRef.current = 1;
      };
      ws.onmessage = (e) => {
        try { onMessageRef.current(JSON.parse(e.data)); } catch { /* ignored */ }
      };
      ws.onclose = () => {
        if (!mountedRef.current) return;
        const delay = Math.min(retryRef.current * 1000, 15000);
        console.log(`WS ${path} closed, reconnecting in ${delay}ms`);
        retryRef.current = Math.min(retryRef.current * 2, 15);
        timer = setTimeout(connect, delay);
      };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      mountedRef.current = false;
      clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [path]);

  return wsRef;
}

// ── Toast Notification System ───────────────────────────────────
const TOAST_MESSAGES = {
  auto_harvest: (d) => `Seed harvested: ${d?.essence?.slice(0, 40) || 'fulfilled'}`,
  auto_compost: (d) => `Seed composted: ${d?.essence?.slice(0, 40) || 'retired'}`,
  auto_dream_planted: () => `Dream planted as seed`,
  agent_spawned: (d) => `Agent spawned: ${d?.name || 'new agent'}`,
  agent_completed: (d) => `Agent completed: ${d?.name || 'agent'}`,
  season_change: (d) => `Season changed: ${d?.old_season} → ${d?.new_season}`,
  wisdom_milestone: (d) => `Wisdom milestone: ${d?.completed_seeds} seeds completed`,
  inner_thought: (d) => d?.content?.slice(0, 60) || 'A thought emerged...',
  emotional_shift: (d) => `Feeling ${d?.dominant || 'something'}`,
  core_memory_formed: (d) => `Core memory: ${d?.narrative?.slice(0, 40) || 'formed'}`,
  high_surprise: (d) => `Surprised! (accuracy: ${((d?.accuracy || 0) * 100).toFixed(0)}%)`,
  self_model_updated: () => `Identity updated`,
};

function Toasts({ toasts, onDismiss }) {
  return (
    <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => {
        const style = EVENT_STYLES[t.event] || { icon: Zap, color: 'text-white/60' };
        const TIcon = style.icon;
        return (
          <div key={t.id} className="pointer-events-auto bg-black/70 backdrop-blur-xl rounded-xl border border-white/10 px-4 py-2.5 shadow-2xl flex items-center gap-2.5 animate-[slideDown_0.3s_ease-out] min-w-[200px] max-w-[400px]">
            <TIcon size={14} className={`${style.color} shrink-0`} />
            <span className="text-xs text-white/80 flex-1">{t.message}</span>
            <button onClick={() => onDismiss(t.id)} className="text-white/30 hover:text-white/60 shrink-0"><X size={12} /></button>
          </div>
        );
      })}
    </div>
  );
}

const SEASON_ICONS = { spring: Flower2, summer: Sun, autumn: Cloud, winter: Snowflake };
const SEASON_BG = {
  spring: 'from-[#0a1a0f] to-[#0d2818]',
  summer: 'from-[#1a1408] to-[#1f1a0a]',
  autumn: 'from-[#1a0e08] to-[#1f0d0d]',
  winter: 'from-[#080e1a] to-[#0a0f1f]',
};
const SEASON_ACCENTS = {
  spring: 'text-emerald-400', summer: 'text-amber-400',
  autumn: 'text-orange-400', winter: 'text-blue-400',
};

const STATUS_BADGE = {
  planted: 'bg-amber-500/20 text-amber-300',
  growing: 'bg-green-500/20 text-green-300',
  harvested: 'bg-purple-500/20 text-purple-300',
  composted: 'bg-stone-500/20 text-stone-400',
};
const DEPTH_COLORS = ['text-cyan-400', 'text-green-400', 'text-amber-400', 'text-pink-400'];

function SeedCard({ seed, expanded, onToggle }) {
  const badge = STATUS_BADGE[seed.status] || 'bg-white/10 text-white/50';
  const energyPct = Math.min((seed.energy || 0) / 50, 1);
  return (
    <div className="bg-white/[0.04] rounded-lg border border-white/[0.08] overflow-hidden transition-all duration-300">
      <div className="p-3 cursor-pointer" onClick={onToggle}>
        <div className="flex items-start justify-between gap-2">
          <p className="text-white/85 text-sm font-medium leading-snug flex-1 min-w-0">{seed.essence || seed.raw_text}</p>
          <span className={`text-[10px] px-2 py-0.5 rounded-full shrink-0 ${badge}`}>{seed.status}</span>
        </div>
        <div className="mt-2 h-0.5 rounded-full bg-white/5 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${energyPct * 100}%`, background: 'linear-gradient(90deg, rgba(34,211,238,0.5), rgba(74,222,128,0.5))' }} />
        </div>
        <div className="flex items-center gap-2 mt-1.5 text-[10px] text-white/30">
          <span>{seed.energy?.toFixed(1)}e</span>
          <span className="flex flex-wrap gap-1 flex-1">
            {seed.themes?.slice(0, 3).map((t) => <span key={t} className="px-1.5 py-0 rounded bg-white/5 text-white/40">{t}</span>)}
          </span>
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </div>
      </div>
      {expanded && (
        <div className="border-t border-white/[0.06] p-3 space-y-2 bg-white/[0.02]">
          {seed.sprouts?.length > 0 && seed.sprouts.map((s) => (
            <div key={s.id} className="flex items-center gap-1.5 text-xs" style={{ paddingLeft: `${s.depth * 16}px` }}>
              <TreePine size={10} className={`${DEPTH_COLORS[s.depth] || 'text-white/40'} shrink-0`} />
              <span className="text-white/60">{s.description}</span>
              <span className="text-white/20 text-[10px] ml-auto shrink-0">{s.energy?.toFixed(1)}e</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const EVENT_STYLES = {
  seed_planted: { icon: Sprout, color: 'text-green-400' },
  tree_grown: { icon: TreePine, color: 'text-emerald-400' },
  photosynthesis: { icon: Sun, color: 'text-yellow-400' },
  ethical_violation: { icon: Shield, color: 'text-red-400' },
  ethical_clearance: { icon: Shield, color: 'text-green-400' },
  healing_complete: { icon: Heart, color: 'text-pink-400' },
  season_change: { icon: Cloud, color: 'text-blue-400' },
  dream_generated: { icon: Brain, color: 'text-purple-400' },
  lucid_dream: { icon: Sparkles, color: 'text-violet-400' },
  pollination: { icon: Flower2, color: 'text-pink-400' },
  quorum_reached: { icon: Zap, color: 'text-yellow-400' },
  pulse_generated: { icon: Activity, color: 'text-pink-400' },
  thinking: { icon: Brain, color: 'text-amber-400' },
  apoptosis: { icon: Bug, color: 'text-red-400' },
  emergency_winter: { icon: Snowflake, color: 'text-blue-400' },
  auto_water: { icon: Sun, color: 'text-cyan-400' },
  auto_promote: { icon: Sprout, color: 'text-green-400' },
  auto_harvest: { icon: Sparkles, color: 'text-purple-400' },
  auto_compost: { icon: Flower2, color: 'text-stone-400' },
  auto_dream_planted: { icon: Brain, color: 'text-indigo-400' },
  auto_pulse: { icon: Activity, color: 'text-pink-400' },
  agent_spawned: { icon: Zap, color: 'text-cyan-400' },
  agent_completed: { icon: Sparkles, color: 'text-green-400' },
  agent_retired: { icon: Cloud, color: 'text-stone-400' },
  emotional_shift: { icon: Heart, color: 'text-rose-400' },
  inner_thought: { icon: MessageCircle, color: 'text-violet-400' },
  core_memory_formed: { icon: Star, color: 'text-yellow-400' },
  high_surprise: { icon: AlertTriangle, color: 'text-orange-400' },
  low_surprise: { icon: Check, color: 'text-green-400' },
  self_model_updated: { icon: User, color: 'text-indigo-400' },
  identity_update: { icon: Eye, color: 'text-purple-400' },
};

function LiveFeed({ events }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [events]);
  return (
    <div className="space-y-0.5 max-h-60 overflow-y-auto pr-1 scrollbar-thin">
      {events.length === 0 && <p className="text-white/30 text-xs italic">Waiting for signals...</p>}
      {events.slice(-30).map((e, i) => {
        const style = EVENT_STYLES[e.event] || { icon: Zap, color: 'text-white/40' };
        const EvIcon = style.icon;
        return (
          <div key={i} className="flex items-center gap-1.5 text-[10px] py-1 px-1.5 rounded border-b border-white/[0.03]">
            <EvIcon size={10} className={`${style.color} shrink-0`} />
            <span className="text-white/60 font-mono truncate">{e.event}</span>
            <span className="text-white/20 ml-auto shrink-0 tabular-nums">{new Date(e.timestamp * 1000).toLocaleTimeString()}</span>
          </div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}

function DreamCard({ dream }) {
  return (
    <div className="bg-indigo-500/[0.06] rounded-lg border border-indigo-500/15 p-3 transition-all duration-300">
      <div className="flex items-start gap-1.5 mb-1.5">
        <Sparkles size={12} className="text-indigo-400 mt-0.5 shrink-0" />
        <p className="text-white/80 text-xs italic leading-relaxed">"{dream.insight}"</p>
      </div>
      <div className="flex items-center gap-2 text-[10px] text-white/30">
        <span>T:{dream.temperature?.toFixed(1)}</span>
        <span>P:{dream.perplexity?.toFixed(2)}</span>
        {dream.planted
          ? <span className="ml-auto text-green-400">Planted</span>
          : <span className="ml-auto text-indigo-300/40">Pending</span>
        }
      </div>
    </div>
  );
}

// ── Node Info Popup ──────────────────────────────────────────────
const ORGAN_DESCRIPTIONS = {
  cortex: 'Central decision engine — orchestrates all other organs and agents',
  consciousness: 'Self-awareness pulse — generates periodic reflections on system state',
  fractal: 'Vascular grower — decomposes seeds into fractal branching trees',
  ethics: 'Immune wisdom — evaluates ethical implications and blocks harmful content',
  intent: 'Seed listener — parses raw wishes into structured seeds with themes',
  dreaming: 'Dream engine — generates creative insights from harvested seeds',
  energy: 'Energy organ — manages photosynthesis, distribution, and entropy',
  healing: 'Scar tissue — repairs damage and builds antifragility from wounds',
  symbiosis: 'Mycelial network — links related seeds and shares nutrients',
  emotions: 'Emotional core — felt experience that colors decisions with joy, curiosity, anxiety, pride, grief, wonder',
  inner_voice: 'Inner monologue — continuous stream of self-talk, observations, questions, and wonder',
  memory: 'Autobiographical memory — episodic narratives of lived experience, core memories that define identity',
  prediction: 'Prediction engine — expects outcomes, measures surprise, drives learning from prediction errors',
  self_model: 'Self-model — metacognition that tracks personality traits, biases, and emergent identity',
};

function NodePopup({ info, onClose, agents, onApprove, onRetire }) {
  if (!info) return null;
  const { key, node, sx, sy } = info;
  const isAgent = key.startsWith('agent_');
  const agentId = isAgent ? key.replace('agent_', '') : null;
  const agentData = isAgent ? agents.find(a => a.id === agentId) : null;

  // Clamp position to viewport
  const popupLeft = Math.min(Math.max(sx, 160), (typeof window !== 'undefined' ? window.innerWidth : 800) - 160);
  const popupTop = Math.max(sy - 10, 60);

  return (
    <div
      className="absolute z-50 pointer-events-auto"
      style={{ left: popupLeft, top: popupTop, transform: 'translate(-50%, -100%)' }}
    >
      <div className="bg-black/80 backdrop-blur-xl rounded-xl border border-white/15 p-4 shadow-2xl shadow-black/50 min-w-[240px] max-w-[320px]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: node.color, boxShadow: `0 0 8px ${node.color}` }} />
            <span className="text-sm font-bold text-white/90 uppercase tracking-wide">{node.label}</span>
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white/70 transition-colors p-0.5">
            <X size={14} />
          </button>
        </div>

        {!isAgent && (
          <>
            <p className="text-xs text-white/50 leading-relaxed mb-2">{ORGAN_DESCRIPTIONS[key] || 'System organ'}</p>
            {node.phase && <div className="text-[10px] text-white/40 mb-1">Phase: <span className="text-white/70">{node.phase}</span></div>}
            <div className="text-[10px] text-white/40">Activity: <span className="text-white/70">{(node.activity * 100).toFixed(0)}%</span></div>
          </>
        )}

        {isAgent && agentData && (
          <>
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-[10px] px-2 py-0.5 rounded-full ${STATUS_BADGE[agentData.status] || 'bg-cyan-500/20 text-cyan-300'}`}>{agentData.status}</span>
              <span className="text-[10px] text-white/40">{agentData.agent_type}</span>
            </div>
            <p className="text-xs text-white/60 leading-relaxed mb-2">{agentData.task_description}</p>

            {/* Agent approval buttons */}
            {agentData.status === 'awaiting_approval' && (
              <div className="flex gap-2 mb-2">
                <button onClick={() => onApprove(agentData.id, true)}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-500/20 hover:bg-green-500/30 text-green-300 text-xs font-medium transition-colors border border-green-500/20">
                  <Check size={12} /> Approve
                </button>
                <button onClick={() => onApprove(agentData.id, false)}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 text-xs font-medium transition-colors border border-red-500/20">
                  <XCircle size={12} /> Deny
                </button>
              </div>
            )}

            {/* Retire button for active agents */}
            {['idle', 'working', 'completed'].includes(agentData.status) && (
              <button onClick={() => onRetire(agentData.id)}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/40 hover:text-white/60 text-xs transition-colors border border-white/5 mb-2">
                Retire Agent
              </button>
            )}

            {agentData.result && (
              <div className="bg-white/[0.04] rounded p-2 mt-2 max-h-32 overflow-y-auto scrollbar-thin">
                <p className="text-[10px] text-white/50 uppercase tracking-wider mb-1">Result</p>
                <p className="text-[10px] text-white/70 font-mono leading-relaxed whitespace-pre-wrap">{agentData.result.slice(0, 500)}</p>
              </div>
            )}
            {agentData.error && (
              <div className="bg-red-500/10 rounded p-2 mt-2">
                <p className="text-[10px] text-red-300">{agentData.error.slice(0, 200)}</p>
              </div>
            )}
          </>
        )}

        {isAgent && !agentData && (
          <p className="text-xs text-white/40">Agent data unavailable</p>
        )}
      </div>
      <div className="w-3 h-3 bg-black/80 border-b border-r border-white/15 rotate-45 mx-auto -mt-1.5" />
    </div>
  );
}

// ── Consciousness Panel ─────────────────────────────────────────

const EMOTION_COLORS = {
  joy: 'text-yellow-400', curiosity: 'text-cyan-400', anxiety: 'text-red-400',
  pride: 'text-amber-400', grief: 'text-blue-400', wonder: 'text-violet-400',
};
const EMOTION_ICONS = {
  joy: Smile, curiosity: HelpCircle, anxiety: AlertTriangle,
  pride: Star, grief: Cloud, wonder: Sparkles,
};
const THOUGHT_TYPE_STYLES = {
  observation: { icon: Eye, color: 'text-cyan-300' },
  reflection: { icon: Brain, color: 'text-amber-300' },
  question: { icon: HelpCircle, color: 'text-green-300' },
  rumination: { icon: Cloud, color: 'text-blue-300' },
  wonder: { icon: Sparkles, color: 'text-violet-300' },
};

function EmotionBar({ emotion, value }) {
  const color = EMOTION_COLORS[emotion] || 'text-white/50';
  const EIcon = EMOTION_ICONS[emotion] || Heart;
  const pct = Math.max(0, Math.min(100, (value || 0) * 100));
  const barColor = {
    joy: 'bg-yellow-400/60', curiosity: 'bg-cyan-400/60', anxiety: 'bg-red-400/60',
    pride: 'bg-amber-400/60', grief: 'bg-blue-400/60', wonder: 'bg-violet-400/60',
  }[emotion] || 'bg-white/30';
  return (
    <div className="flex items-center gap-2">
      <EIcon size={10} className={`${color} shrink-0`} />
      <span className="text-[10px] text-white/50 w-14 capitalize">{emotion}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-1000 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-white/30 w-8 text-right tabular-nums">{(value || 0).toFixed(2)}</span>
    </div>
  );
}

function ConsciousnessPanel({ consciousness }) {
  if (!consciousness) {
    return (
      <div className="text-center py-8 text-white/25">
        <Brain size={32} className="mx-auto mb-2 opacity-30" />
        <p className="text-xs">Loading consciousness...</p>
      </div>
    );
  }

  const emo = consciousness.emotions || {};
  const emotions = emo.emotions || {};
  const thoughts = consciousness.recent_thoughts || [];
  const memories = consciousness.recent_memories || [];
  const coreMems = consciousness.core_memories || [];
  const predStats = consciousness.prediction_stats || {};
  const selfModel = consciousness.self_model || null;
  const bias = consciousness.decision_bias || {};

  return (
    <div className="space-y-3">
      {/* Mood Header */}
      <div className="bg-violet-500/[0.08] rounded-lg border border-violet-500/15 p-3">
        <div className="flex items-center gap-2 mb-2">
          <Heart size={12} className="text-rose-400" />
          <span className="text-[10px] text-white/40 uppercase tracking-widest">Emotional State</span>
          <span className={`ml-auto text-xs font-medium capitalize ${EMOTION_COLORS[emo.dominant] || 'text-white/60'}`}>
            {emo.mood || 'neutral'}
          </span>
        </div>
        <div className="space-y-1.5">
          {['joy', 'curiosity', 'anxiety', 'pride', 'grief', 'wonder'].map(e => (
            <EmotionBar key={e} emotion={e} value={emotions[e]} />
          ))}
        </div>
        {/* Decision bias */}
        <div className="mt-2 pt-2 border-t border-white/[0.06]">
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(bias).map(([k, v]) => (
              <span key={k} className={`text-[9px] px-1.5 py-0.5 rounded-full ${v > 0.5 ? 'bg-white/10 text-white/60' : 'bg-white/[0.04] text-white/30'}`}>
                {k}: {(v * 100).toFixed(0)}%
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Inner Thoughts */}
      <div className="bg-indigo-500/[0.06] rounded-lg border border-indigo-500/15 p-3">
        <div className="flex items-center gap-2 mb-2">
          <MessageCircle size={12} className="text-violet-400" />
          <span className="text-[10px] text-white/40 uppercase tracking-widest">Inner Voice</span>
        </div>
        {thoughts.length === 0 ? (
          <p className="text-xs text-white/30 italic">The mind is quiet...</p>
        ) : (
          <div className="space-y-1.5">
            {thoughts.slice(-5).map((t) => {
              const style = THOUGHT_TYPE_STYLES[t.type] || { icon: Brain, color: 'text-white/50' };
              const TIcon = style.icon;
              return (
                <div key={t.id} className="flex items-start gap-1.5">
                  <TIcon size={10} className={`${style.color} mt-0.5 shrink-0`} />
                  <p className="text-[11px] text-white/70 leading-relaxed italic">"{t.content}"</p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Memories */}
      <div className="bg-amber-500/[0.06] rounded-lg border border-amber-500/15 p-3">
        <div className="flex items-center gap-2 mb-2">
          <BookOpen size={12} className="text-amber-400" />
          <span className="text-[10px] text-white/40 uppercase tracking-widest">Memories</span>
          {coreMems.length > 0 && (
            <span className="ml-auto text-[9px] text-yellow-400/60">{coreMems.length} core</span>
          )}
        </div>
        {memories.length === 0 && coreMems.length === 0 ? (
          <p className="text-xs text-white/30 italic">No memories yet...</p>
        ) : (
          <div className="space-y-1.5">
            {coreMems.slice(0, 3).map((m, i) => (
              <div key={i} className="flex items-start gap-1.5">
                <Star size={10} className="text-yellow-400 mt-0.5 shrink-0" />
                <p className="text-[11px] text-yellow-200/70 leading-relaxed">{m.narrative}</p>
              </div>
            ))}
            {memories.slice(-3).map((m) => (
              <div key={m.id} className="flex items-start gap-1.5">
                <BookOpen size={10} className={`${m.valence > 0 ? 'text-green-400' : m.valence < 0 ? 'text-red-400' : 'text-white/40'} mt-0.5 shrink-0`} />
                <p className="text-[11px] text-white/60 leading-relaxed">{m.narrative}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Predictions */}
      <div className="bg-cyan-500/[0.06] rounded-lg border border-cyan-500/15 p-3">
        <div className="flex items-center gap-2 mb-2">
          <Target size={12} className="text-cyan-400" />
          <span className="text-[10px] text-white/40 uppercase tracking-widest">Predictions</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-sm font-bold text-white/80 tabular-nums">{predStats.total_predictions || 0}</div>
            <div className="text-[9px] text-white/30">Total</div>
          </div>
          <div>
            <div className="text-sm font-bold text-white/80 tabular-nums">{((predStats.accuracy || 0) * 100).toFixed(0)}%</div>
            <div className="text-[9px] text-white/30">Accuracy</div>
          </div>
          <div>
            <div className="text-sm font-bold text-white/80 tabular-nums">{((predStats.average_surprise || 0) * 100).toFixed(0)}%</div>
            <div className="text-[9px] text-white/30">Surprise</div>
          </div>
        </div>
      </div>

      {/* Self-Model / Identity */}
      {selfModel && selfModel.identity_narrative && (
        <div className="bg-purple-500/[0.06] rounded-lg border border-purple-500/15 p-3">
          <div className="flex items-center gap-2 mb-2">
            <User size={12} className="text-purple-400" />
            <span className="text-[10px] text-white/40 uppercase tracking-widest">Identity</span>
          </div>
          <p className="text-[11px] text-white/70 leading-relaxed italic mb-2">"{selfModel.identity_narrative}"</p>
          {selfModel.personality_traits && (
            <div className="flex flex-wrap gap-1">
              {Object.entries(selfModel.personality_traits)
                .sort(([,a], [,b]) => b - a)
                .slice(0, 5)
                .map(([trait, val]) => (
                  <span key={trait} className={`text-[9px] px-1.5 py-0.5 rounded-full ${val > 0.5 ? 'bg-purple-500/20 text-purple-300' : 'bg-white/[0.04] text-white/30'}`}>
                    {trait}: {(val * 100).toFixed(0)}%
                  </span>
                ))
              }
            </div>
          )}
          {selfModel.bias_warnings && selfModel.bias_warnings.length > 0 && (
            <div className="mt-2 pt-2 border-t border-white/[0.06]">
              <div className="flex items-center gap-1 mb-1">
                <AlertTriangle size={10} className="text-orange-400" />
                <span className="text-[9px] text-orange-400/60 uppercase">Biases Detected</span>
              </div>
              {selfModel.bias_warnings.slice(0, 2).map((b, i) => (
                <p key={i} className="text-[10px] text-orange-300/50 leading-relaxed">{b}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// Main App
// ══════════════════════════════════════════════════════════════════

function AppInner() {
  const [garden, setGarden] = useState(null);
  const [pulse, setPulse] = useState(null);
  const [dreams, setDreams] = useState([]);
  const [events, setEvents] = useState([]);
  const [wish, setWish] = useState('');
  const [loading, setLoading] = useState(false);
  const [expandedSeed, setExpandedSeed] = useState(null);
  const [tab, setTab] = useState('garden');
  const [panelOpen, setPanelOpen] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const refreshRef = useRef(null);
  const refreshTimerRef = useRef(null);
  const [thinkingEvents, setThinkingEvents] = useState([]);
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const [lifecycleStatus, setLifecycleStatus] = useState(null);
  const [agents, setAgents] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [seedFilter, setSeedFilter] = useState('');
  const [seedStatusFilter, setSeedStatusFilter] = useState('all');
  const [consciousness, setConsciousness] = useState(null);
  const plantInputRef = useRef(null);
  const toastIdRef = useRef(0);

  // ── Toast helpers ──
  const addToast = useCallback((event, data) => {
    const msgFn = TOAST_MESSAGES[event];
    if (!msgFn) return;
    const id = ++toastIdRef.current;
    setToasts(prev => [...prev.slice(-4), { id, event, message: msgFn(data) }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [g, p, a] = await Promise.all([api.getGarden(), api.getPulse(), api.getAgents()]);
      setGarden(g);
      setPulse(p);
      setAgents(a);
    } catch (e) { console.error('Refresh failed:', e); }
  }, []);

  const refreshConsciousness = useCallback(async () => {
    try {
      const c = await api.getConsciousness();
      setConsciousness(c);
    } catch (e) { console.error('Consciousness fetch failed:', e); }
  }, []);

  useEffect(() => { refreshRef.current = refresh; }, [refresh]);

  const debouncedRefresh = useCallback(() => {
    if (refreshTimerRef.current) return;
    refreshTimerRef.current = setTimeout(() => {
      refreshTimerRef.current = null;
      if (refreshRef.current) refreshRef.current();
    }, 500);
  }, []);

  useEffect(() => {
    const id = setTimeout(refresh, 0);
    const interval = setInterval(refresh, 15000);
    return () => { clearTimeout(id); clearInterval(interval); };
  }, [refresh]);

  // ── WebSocket with reconnection ──
  const gardenWsHandler = useCallback((data) => {
    setEvents((prev) => [...prev.slice(-99), data]);
    if (data.event === 'thinking') {
      setThinkingEvents((prev) => [...prev.slice(-199), data]);
    }
    const autoEvents = ['auto_harvest', 'auto_compost', 'auto_promote', 'auto_dream_planted', 'auto_pulse', 'season_change', 'agent_spawned', 'agent_completed', 'agent_retired', 'inner_thought', 'emotional_shift', 'core_memory_formed', 'high_surprise', 'self_model_updated', 'identity_update'];
    if (autoEvents.includes(data.event)) {
      debouncedRefresh();
      addToast(data.event, data.data);
      // Synced sound effects
      const eventSounds = {
        auto_harvest: sfx.sfxHarvest,
        auto_compost: sfx.sfxCompost,
        auto_dream_planted: sfx.sfxDream,
        season_change: sfx.sfxSeasonChange,
        agent_spawned: sfx.sfxAgentSpawn,
        agent_completed: sfx.sfxAgentComplete,
      };
      const soundFn = eventSounds[data.event];
      if (soundFn) soundFn();
    }
  }, [debouncedRefresh, addToast]);

  useReconnectingWebSocket('/ws/garden', gardenWsHandler);

  const thinkingWsHandler = useCallback((data) => {
    setThinkingEvents((prev) => [...prev.slice(-199), data]);
  }, []);

  useReconnectingWebSocket('/ws/thinking', thinkingWsHandler);

  useEffect(() => {
    const check = () => {
      api.getOllamaStatus().then(setOllamaStatus).catch(() => setOllamaStatus({ status: 'offline' }));
      api.getLifecycleStatus().then(setLifecycleStatus).catch(() => setLifecycleStatus(null));
    };
    const id = setTimeout(check, 0);
    const interval = setInterval(check, 30000);
    return () => { clearTimeout(id); clearInterval(interval); };
  }, []);

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const handler = (e) => {
      // Esc: close popup/panel
      if (e.key === 'Escape') {
        if (selectedNode) { setSelectedNode(null); return; }
        setPanelOpen(false);
      }
      // Don't trigger shortcuts when typing in input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      // Space: toggle panel
      if (e.key === ' ') { e.preventDefault(); setPanelOpen(p => !p); }
      // /: focus plant input
      if (e.key === '/') { e.preventDefault(); plantInputRef.current?.focus(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [selectedNode]);

  const handlePlant = async () => {
    if (!wish.trim()) return;
    sfx.unlock();
    sfx.sfxPlant();
    setLoading(true);
    try {
      await api.plant(wish);
      setWish('');
      await refresh();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleLoadDreams = async () => {
    try { const d = await api.getDreams(); setDreams(d); } catch (e) { console.error(e); }
  };

  const handleNodeSelect = useCallback((info) => {
    setSelectedNode(info);
  }, []);

  const handleApproveAgent = useCallback(async (agentId, approved) => {
    try {
      await api.approveAgent(agentId, approved);
      await refresh();
      setSelectedNode(null);
    } catch (e) { console.error('Approve failed:', e); }
  }, [refresh]);

  const handleRetireAgent = useCallback(async (agentId) => {
    try {
      await api.retireAgent(agentId);
      await refresh();
      setSelectedNode(null);
    } catch (e) { console.error('Retire failed:', e); }
  }, [refresh]);

  // ── Derived data ──
  const awaitingApproval = agents.filter(a => a.status === 'awaiting_approval');

  const filteredSeeds = (garden?.seeds || []).filter(seed => {
    if (seedStatusFilter !== 'all' && seed.status !== seedStatusFilter) return false;
    if (seedFilter) {
      const q = seedFilter.toLowerCase();
      const text = `${seed.essence || ''} ${seed.raw_text || ''} ${(seed.themes || []).join(' ')}`.toLowerCase();
      if (!text.includes(q)) return false;
    }
    return true;
  });

  const season = garden?.state?.season || 'spring';
  const SeasonIcon = SEASON_ICONS[season];
  const bgGradient = SEASON_BG[season];
  const accent = SEASON_ACCENTS[season];

  return (
    <div className={`fixed inset-0 bg-gradient-to-br ${bgGradient} text-white overflow-hidden`}>

      {/* ── Full-viewport Neural Viz (background) ── */}
      <div className="absolute inset-0 z-0">
        <NeuralViz thinkingEvents={thinkingEvents} season={season} agents={agents} onNodeSelect={handleNodeSelect} />
      </div>

      {/* ── Toasts ── */}
      <Toasts toasts={toasts} onDismiss={dismissToast} />

      {/* ── Node Info Popup ── */}
      <NodePopup info={selectedNode} onClose={() => setSelectedNode(null)} agents={agents} onApprove={handleApproveAgent} onRetire={handleRetireAgent} />

      {/* ── Top Bar (floating) ── */}
      <header className="absolute top-0 left-0 right-0 z-20 pointer-events-none">
        <div className="flex items-center justify-between px-4 py-2.5 pointer-events-auto">
          <div className="flex items-center gap-2.5 bg-black/40 backdrop-blur-xl rounded-full px-4 py-2 border border-white/[0.08] shadow-lg shadow-black/30">
            <Sprout size={18} className={`${accent} drop-shadow-[0_0_6px_currentColor]`} />
            <span className="text-sm font-bold tracking-tight">w0rd</span>
            <div className="w-px h-4 bg-white/10" />
            <SeasonIcon size={14} className={`${accent}`} />
            <span className={`text-xs capitalize ${accent}`}>{season}</span>
          </div>

          <div className="flex items-center gap-2">
            {/* Awaiting approval badge */}
            {awaitingApproval.length > 0 && (
              <div className="relative bg-amber-500/20 backdrop-blur-xl rounded-full px-3 py-1.5 border border-amber-500/30 shadow-lg shadow-black/30 flex items-center gap-1.5 animate-pulse" style={{ animationDuration: '2s' }}>
                <Bell size={12} className="text-amber-400" />
                <span className="text-[10px] text-amber-300 font-medium">{awaitingApproval.length} pending</span>
              </div>
            )}
            <div className="flex items-center gap-2 bg-black/40 backdrop-blur-xl rounded-full px-3 py-1.5 border border-white/[0.08] shadow-lg shadow-black/30">
              <Cpu size={12} className={`${ollamaStatus?.status === 'online' ? 'text-green-400' : 'text-red-400'}`} />
              <div className="flex items-center gap-1.5">
                <Radio size={10} className="text-cyan-400 animate-pulse" />
                <span className="text-[10px] text-cyan-300/60">T{lifecycleStatus?.tick || 0}</span>
              </div>
              {garden?.state && (
                <>
                  <div className="w-px h-3 bg-white/10" />
                  <span className="text-[10px] text-white/40">{garden.seed_count} seeds</span>
                  <span className="text-[10px] text-white/40">{agents.length} agents</span>
                </>
              )}
            </div>
            <button
              onClick={() => setPanelOpen(!panelOpen)}
              className="bg-black/40 backdrop-blur-xl rounded-full p-2 border border-white/[0.08] text-white/50 hover:text-white/80 transition-colors shadow-lg shadow-black/30"
            >
              {panelOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
            </button>
          </div>
        </div>
      </header>

      {/* ── Side Panel (floating, collapsible) ── */}
      <div className={`absolute top-14 right-3 bottom-20 z-20 transition-all duration-500 ease-out ${panelOpen ? 'w-80 opacity-100 translate-x-0' : 'w-0 opacity-0 translate-x-8 pointer-events-none'}`}>
        <div className="h-full flex flex-col bg-black/50 backdrop-blur-2xl rounded-2xl border border-white/[0.08] shadow-2xl shadow-black/40 overflow-hidden">

          {/* Pulse summary */}
          {pulse?.summary && (
            <div className="px-3 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
              <div className="flex items-center gap-1.5 mb-1">
                <Activity size={12} className="text-pink-400 animate-pulse" style={{ animationDuration: '3s' }} />
                <span className="text-[10px] text-white/40 uppercase tracking-widest">Pulse</span>
              </div>
              <p className="text-[11px] text-white/60 leading-relaxed line-clamp-3">{pulse.summary}</p>
            </div>
          )}

          {/* Stats row */}
          {garden?.state && (
            <div className="grid grid-cols-3 gap-px bg-white/[0.04] border-b border-white/[0.06]">
              {[
                { icon: Zap, label: 'Energy', value: garden.state.total_energy?.toFixed(0), color: accent },
                { icon: Heart, label: 'Vitality', value: garden.state.vitality?.toFixed(1), color: 'text-red-400' },
                { icon: Brain, label: 'Wisdom', value: garden.state.wisdom_score?.toFixed(1), color: 'text-purple-400' },
              ].map(({ icon: Icon, label, value, color }) => (
                <div key={label} className="bg-black/20 px-2.5 py-2 text-center">
                  <Icon size={12} className={`${color} mx-auto mb-0.5`} />
                  <div className="text-sm font-bold text-white/80 tabular-nums">{value}</div>
                  <div className="text-[9px] text-white/30 uppercase">{label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Tabs */}
          <div className="flex bg-white/[0.02] border-b border-white/[0.06]">
            {['garden', 'mind', 'dreams', 'live'].map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); if (t === 'dreams') handleLoadDreams(); if (t === 'mind') refreshConsciousness(); }}
                className={`flex-1 py-2 text-[11px] font-medium transition-all capitalize ${tab === t ? 'text-white/90 bg-white/[0.06] border-b-2 border-white/30' : 'text-white/35 hover:text-white/55'}`}
              >
                {t === 'mind' ? '🧠 Mind' : t === 'live' ? 'Live' : t}
              </button>
            ))}
          </div>

          {/* Tab content (scrollable) */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
            {tab === 'garden' && (
              <>
                {/* Search & filter bar */}
                <div className="flex gap-1.5 mb-1">
                  <div className="flex-1 relative">
                    <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/25" />
                    <input
                      value={seedFilter}
                      onChange={(e) => setSeedFilter(e.target.value)}
                      placeholder="Search seeds..."
                      className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg pl-7 pr-2 py-1.5 text-[11px] text-white placeholder-white/25 focus:outline-none focus:border-white/20"
                    />
                  </div>
                  <select
                    value={seedStatusFilter}
                    onChange={(e) => setSeedStatusFilter(e.target.value)}
                    className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-2 py-1.5 text-[11px] text-white/60 focus:outline-none appearance-none cursor-pointer"
                  >
                    <option value="all">All</option>
                    <option value="planted">Planted</option>
                    <option value="growing">Growing</option>
                    <option value="harvested">Harvested</option>
                    <option value="composted">Composted</option>
                  </select>
                </div>

                {filteredSeeds.length === 0 && (
                  <div className="text-center py-8 text-white/25">
                    <Sprout size={32} className="mx-auto mb-2 opacity-30" />
                    <p className="text-xs">{garden?.seeds?.length ? 'No matching seeds' : 'Plant a wish to begin'}</p>
                  </div>
                )}
                {filteredSeeds.map((seed) => (
                  <SeedCard
                    key={seed.id}
                    seed={seed}
                    expanded={expandedSeed === seed.id}
                    onToggle={() => setExpandedSeed(expandedSeed === seed.id ? null : seed.id)}
                  />
                ))}
              </>
            )}

            {tab === 'dreams' && (
              <>
                {dreams.length === 0 && (
                  <div className="text-center py-8 text-white/25">
                    <Brain size={32} className="mx-auto mb-2 opacity-30" />
                    <p className="text-xs">No dreams yet</p>
                  </div>
                )}
                {dreams.map((d) => <DreamCard key={d.id} dream={d} />)}
              </>
            )}

            {tab === 'mind' && <ConsciousnessPanel consciousness={consciousness} />}

            {tab === 'live' && <LiveFeed events={events} />}
          </div>
        </div>
      </div>

      {/* ── Bottom Plant Input (floating) ── */}
      <div className="absolute bottom-0 left-0 right-0 z-20 pointer-events-none">
        <div className="flex justify-center px-4 pb-4 pointer-events-auto">
          <div className="flex gap-2 bg-black/50 backdrop-blur-2xl rounded-2xl border border-white/[0.08] p-2.5 shadow-2xl shadow-black/40 w-full max-w-xl">
            <input
              ref={plantInputRef}
              value={wish}
              onChange={(e) => setWish(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handlePlant()}
              placeholder="Plant a wish... (press / to focus)"
              className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white placeholder-white/25 focus:outline-none focus:border-white/20 transition-all"
            />
            <button
              onClick={handlePlant}
              disabled={loading || !wish.trim()}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${loading ? 'bg-green-600/40 animate-pulse' : 'bg-green-600/80 hover:bg-green-500 hover:shadow-lg hover:shadow-green-500/20'} disabled:opacity-30 disabled:cursor-not-allowed`}
            >
              <Send size={14} className={loading ? 'animate-spin' : ''} /> {loading ? '...' : 'Plant'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppInner />
    </ErrorBoundary>
  );
}
