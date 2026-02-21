import { useState, useEffect, useRef, useCallback } from 'react';
import { Sprout, Sun, Cloud, Snowflake, Heart, Brain, Zap, TreePine, Flower2, Activity, Send, ChevronDown, ChevronUp, Sparkles, Shield, Bug, Cpu, Radio, X, PanelRightOpen, PanelRightClose } from 'lucide-react';
import { api } from './api';
import NeuralViz from './NeuralViz';

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
};

function NodePopup({ info, onClose, agents }) {
  if (!info) return null;
  const { key, node, sx, sy } = info;
  const isAgent = key.startsWith('agent_');
  const agentId = isAgent ? key.replace('agent_', '') : null;
  const agentData = isAgent ? agents.find(a => a.id === agentId) : null;

  return (
    <div
      className="absolute z-50 pointer-events-auto"
      style={{ left: Math.min(sx, window.innerWidth - 300), top: Math.max(sy - 10, 60), transform: 'translate(-50%, -100%)' }}
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

// ══════════════════════════════════════════════════════════════════
// Main App
// ══════════════════════════════════════════════════════════════════

export default function App() {
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
  const wsRef = useRef(null);
  const thinkingWsRef = useRef(null);
  const refreshRef = useRef(null);
  const refreshTimerRef = useRef(null);
  const [thinkingEvents, setThinkingEvents] = useState([]);
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const [lifecycleStatus, setLifecycleStatus] = useState(null);
  const [agents, setAgents] = useState([]);

  const refresh = useCallback(async () => {
    try {
      const [g, p, a] = await Promise.all([api.getGarden(), api.getPulse(), api.getAgents()]);
      setGarden(g);
      setPulse(p);
      setAgents(a);
    } catch (e) { console.error('Refresh failed:', e); }
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

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/garden`);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setEvents((prev) => [...prev.slice(-99), data]);
        if (data.event === 'thinking') {
          setThinkingEvents((prev) => [...prev.slice(-199), data]);
        }
        const autoEvents = ['auto_harvest', 'auto_compost', 'auto_promote', 'auto_dream_planted', 'auto_pulse', 'season_change', 'agent_spawned', 'agent_completed', 'agent_retired'];
        if (autoEvents.includes(data.event)) {
          debouncedRefresh();
        }
      } catch { /* ignored */ }
    };
    ws.onopen = () => console.log('Garden WS connected');
    ws.onclose = () => setTimeout(() => {}, 3000);
    wsRef.current = ws;
    return () => ws.close();
  }, [debouncedRefresh]);

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/thinking`);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setThinkingEvents((prev) => [...prev.slice(-199), data]);
      } catch { /* ignored */ }
    };
    ws.onopen = () => console.log('Thinking WS connected');
    ws.onclose = () => setTimeout(() => {}, 3000);
    thinkingWsRef.current = ws;
    return () => ws.close();
  }, []);

  useEffect(() => {
    const check = () => {
      api.getOllamaStatus().then(setOllamaStatus).catch(() => setOllamaStatus({ status: 'offline' }));
      api.getLifecycleStatus().then(setLifecycleStatus).catch(() => setLifecycleStatus(null));
    };
    const id = setTimeout(check, 0);
    const interval = setInterval(check, 30000);
    return () => { clearTimeout(id); clearInterval(interval); };
  }, []);

  const handlePlant = async () => {
    if (!wish.trim()) return;
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

      {/* ── Node Info Popup ── */}
      <NodePopup info={selectedNode} onClose={() => setSelectedNode(null)} agents={agents} />

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
            {['garden', 'dreams', 'live'].map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); if (t === 'dreams') handleLoadDreams(); }}
                className={`flex-1 py-2 text-[11px] font-medium transition-all capitalize ${tab === t ? 'text-white/90 bg-white/[0.06] border-b-2 border-white/30' : 'text-white/35 hover:text-white/55'}`}
              >
                {t === 'live' ? 'Live' : t}
              </button>
            ))}
          </div>

          {/* Tab content (scrollable) */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
            {tab === 'garden' && (
              <>
                {garden?.seeds?.length === 0 && (
                  <div className="text-center py-8 text-white/25">
                    <Sprout size={32} className="mx-auto mb-2 opacity-30" />
                    <p className="text-xs">Plant a wish to begin</p>
                  </div>
                )}
                {garden?.seeds?.map((seed) => (
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

            {tab === 'live' && <LiveFeed events={events} />}
          </div>
        </div>
      </div>

      {/* ── Bottom Plant Input (floating) ── */}
      <div className="absolute bottom-0 left-0 right-0 z-20 pointer-events-none">
        <div className="flex justify-center px-4 pb-4 pointer-events-auto">
          <div className="flex gap-2 bg-black/50 backdrop-blur-2xl rounded-2xl border border-white/[0.08] p-2.5 shadow-2xl shadow-black/40 w-full max-w-xl">
            <input
              value={wish}
              onChange={(e) => setWish(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handlePlant()}
              placeholder="Plant a wish..."
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
