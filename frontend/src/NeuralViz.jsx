import { useEffect, useRef, useState } from 'react';
import { Zap } from 'lucide-react';

// ── Seasonal color palettes ──────────────────────────────────────
const SEASON_PALETTES = {
  spring: {
    intent: '#34d399', fractal: '#4ade80', dreaming: '#6ee7b7',
    consciousness: '#a7f3d0', cortex: '#10b981', ethics: '#86efac',
    energy: '#22c55e', healing: '#bbf7d0', symbiosis: '#059669',
  },
  summer: {
    intent: '#fbbf24', fractal: '#f59e0b', dreaming: '#fcd34d',
    consciousness: '#fde68a', cortex: '#f97316', ethics: '#fb923c',
    energy: '#facc15', healing: '#fef08a', symbiosis: '#ea580c',
  },
  autumn: {
    intent: '#f97316', fractal: '#ef4444', dreaming: '#fb923c',
    consciousness: '#fbbf24', cortex: '#dc2626', ethics: '#f87171',
    energy: '#ea580c', healing: '#fdba74', symbiosis: '#b91c1c',
  },
  winter: {
    intent: '#60a5fa', fractal: '#818cf8', dreaming: '#a78bfa',
    consciousness: '#93c5fd', cortex: '#3b82f6', ethics: '#6366f1',
    energy: '#38bdf8', healing: '#c4b5fd', symbiosis: '#1d4ed8',
  },
};

function getOrganColors(season) {
  return SEASON_PALETTES[season] || SEASON_PALETTES.spring;
}

// ── 3D positions (centered around origin) ────────────────────────
const ORGAN_3D = {
  consciousness: { x: 0, y: 1.2, z: 0 },
  fractal:       { x: -0.9, y: 0.7, z: 0.4 },
  ethics:        { x: 0.9, y: 0.7, z: 0.4 },
  intent:        { x: -1.3, y: 0, z: -0.3 },
  dreaming:      { x: 1.3, y: 0, z: -0.3 },
  cortex:        { x: 0, y: 0, z: 0 },
  energy:        { x: -0.9, y: -0.8, z: 0.5 },
  healing:       { x: 0.9, y: -0.8, z: 0.5 },
  symbiosis:     { x: 0, y: -1.2, z: -0.2 },
};

const CONNECTIONS = [
  ['cortex', 'consciousness'], ['cortex', 'fractal'], ['cortex', 'ethics'],
  ['cortex', 'intent'], ['cortex', 'dreaming'], ['cortex', 'energy'],
  ['cortex', 'healing'], ['cortex', 'symbiosis'],
  ['intent', 'fractal'], ['fractal', 'ethics'], ['ethics', 'energy'],
  ['energy', 'symbiosis'], ['symbiosis', 'healing'], ['healing', 'dreaming'],
  ['dreaming', 'consciousness'], ['intent', 'consciousness'],
];

// Agent type → base color (will be tinted by season)
const AGENT_TYPE_COLORS = {
  analyze:    '#60a5fa',
  code_gen:   '#4ade80',
  code_exec:  '#f87171',
  web_search: '#22d3ee',
  file_read:  '#fbbf24',
  file_write: '#fb923c',
  summarize:  '#a78bfa',
  decompose:  '#34d399',
  planner:    '#f472b6',
};

// Position agent nodes in a ring around the cortex
function agentPosition(index, total) {
  const angle = (index / Math.max(total, 1)) * Math.PI * 2;
  const radius = 0.7;
  return {
    x: Math.cos(angle) * radius,
    y: -0.05,
    z: Math.sin(angle) * radius,
  };
}

// ── Helpers ──────────────────────────────────────────────────────
function hexToRgb(hex) {
  return { r: parseInt(hex.slice(1, 3), 16), g: parseInt(hex.slice(3, 5), 16), b: parseInt(hex.slice(5, 7), 16) };
}
function rgba(hex, a) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}

// Rotate point around Y axis
function rotY(x, y, z, angle) {
  const c = Math.cos(angle), s = Math.sin(angle);
  return { x: x * c + z * s, y, z: -x * s + z * c };
}
// Rotate point around X axis
function rotX(x, y, z, angle) {
  const c = Math.cos(angle), s = Math.sin(angle);
  return { x, y: y * c - z * s, z: y * s + z * c };
}
// Project 3D → 2D with perspective
function project(x, y, z, cx, cy, fov) {
  const scale = fov / (fov + z + 3);
  return { sx: cx + x * scale * cx * 0.7, sy: cy - y * scale * cy * 0.7, scale };
}

export default function NeuralViz({ thinkingEvents, season = 'spring', agents = [], onNodeSelect }) {
  const canvasRef = useRef(null);
  const stateRef = useRef({
    nodes: {},
    rotX: 0.15,
    rotY: 0,
    autoRotY: 0,
    dragging: false,
    dragMoved: false,
    lastMouse: null,
    motes: [],
    inited: false,
    lastProjected: [],   // cached projected positions for hit-testing
  });
  const animRef = useRef(null);
  const onNodeSelectRef = useRef(onNodeSelect);
  useEffect(() => { onNodeSelectRef.current = onNodeSelect; }, [onNodeSelect]);
  const [activeTokens, setActiveTokens] = useState('');
  const [activeOrgan, setActiveOrgan] = useState('');
  const [activePhase, setActivePhase] = useState('');

  const organColors = getOrganColors(season);

  // ── Initialize / reinitialize on season change ──
  useEffect(() => {
    const st = stateRef.current;
    const nodes = {};
    for (const [organ, pos] of Object.entries(ORGAN_3D)) {
      const existing = st.nodes[organ];
      nodes[organ] = {
        x3: pos.x, y3: pos.y, z3: pos.z,
        color: organColors[organ] || '#888',
        label: organ,
        activity: existing?.activity || 0,
        phase: existing?.phase || '',
        breathe: existing?.breathe || Math.random() * Math.PI * 2,
        orbiters: existing?.orbiters || Array.from({ length: 3 }, (_, i) => ({
          angle: (Math.PI * 2 / 3) * i,
          speed: 0.01 + Math.random() * 0.02,
          dist: 28 + Math.random() * 10,
          size: 1.5,
        })),
        shockwaves: existing?.shockwaves || [],
      };
    }
    st.nodes = nodes;

    // Motes in 3D space
    const colors = Object.values(organColors);
    st.motes = Array.from({ length: 50 }, (_, i) => ({
      x: (Math.random() - 0.5) * 3.5,
      y: (Math.random() - 0.5) * 3.5,
      z: (Math.random() - 0.5) * 3,
      vx: (Math.random() - 0.5) * 0.003,
      vy: (Math.random() - 0.5) * 0.003,
      vz: (Math.random() - 0.5) * 0.002,
      size: 0.5 + Math.random() * 1.5,
      color: colors[i % colors.length],
      phase: Math.random() * Math.PI * 2,
    }));
    st.agentNodes = {};
    st.inited = true;
  }, [organColors]);

  // ── Sync dynamic agent nodes ──
  useEffect(() => {
    const st = stateRef.current;
    if (!st.inited) return;
    const activeAgents = agents.filter(a => a.status !== 'retired');
    const newAgentNodes = {};
    activeAgents.forEach((agent, i) => {
      const existing = st.agentNodes?.[agent.id];
      const pos = agentPosition(i, activeAgents.length);
      const statusActivity = agent.status === 'working' ? 0.8 : agent.status === 'completed' ? 0.4 : agent.status === 'awaiting_approval' ? 0.6 : 0.15;
      newAgentNodes[agent.id] = {
        x3: pos.x, y3: pos.y, z3: pos.z,
        color: AGENT_TYPE_COLORS[agent.agent_type] || '#888',
        label: agent.name,
        agentType: agent.agent_type,
        status: agent.status,
        seedId: agent.seed_id,
        activity: existing?.activity ?? statusActivity,
        targetActivity: statusActivity,
        phase: agent.status,
        breathe: existing?.breathe || Math.random() * Math.PI * 2,
        orbiters: existing?.orbiters || [{ angle: 0, speed: 0.02, dist: 20, size: 1.2 }],
        shockwaves: existing?.shockwaves || [],
        spawnAnim: existing?.spawnAnim ?? 0,
        isAgent: true,
      };
    });
    st.agentNodes = newAgentNodes;
  }, [agents]);

  // ── Canvas setup + animation loop + mouse handlers ──
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    let w = 0, h = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      w = rect.width; h = rect.height;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    // ── Mouse drag to rotate + click to select ──
    const onMouseDown = (e) => {
      const st = stateRef.current;
      st.dragging = true;
      st.dragMoved = false;
      st.lastMouse = { x: e.clientX, y: e.clientY };
    };
    const onMouseMove = (e) => {
      const st = stateRef.current;
      if (!st.dragging || !st.lastMouse) return;
      const dx = e.clientX - st.lastMouse.x;
      const dy = e.clientY - st.lastMouse.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) st.dragMoved = true;
      st.rotY += dx * 0.005;
      st.rotX += dy * 0.005;
      st.rotX = Math.max(-1.2, Math.min(1.2, st.rotX));
      st.lastMouse = { x: e.clientX, y: e.clientY };
    };
    const onMouseUp = (e) => {
      const st = stateRef.current;
      if (!st.dragMoved && onNodeSelectRef.current) {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        let hit = null;
        let bestDist = 30;
        for (const p of st.lastProjected || []) {
          const dx = mx - p.sx, dy = my - p.sy;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < bestDist) { bestDist = dist; hit = p; }
        }
        onNodeSelectRef.current(hit ? { key: hit.key, node: hit.node, sx: hit.sx, sy: hit.sy } : null);
      }
      st.dragging = false;
      st.lastMouse = null;
    };

    // Touch support (with dragMoved tracking for tap-to-select)
    const onTouchStart = (e) => {
      const t = e.touches[0];
      const st = stateRef.current;
      st.dragging = true;
      st.dragMoved = false;
      st.lastMouse = { x: t.clientX, y: t.clientY };
      st.touchStart = { x: t.clientX, y: t.clientY };
    };
    const onTouchMove = (e) => {
      e.preventDefault();
      const t = e.touches[0];
      const st = stateRef.current;
      if (!st.dragging || !st.lastMouse) return;
      const dx = t.clientX - st.lastMouse.x;
      const dy = t.clientY - st.lastMouse.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) st.dragMoved = true;
      st.rotY += dx * 0.005;
      st.rotX += dy * 0.005;
      st.rotX = Math.max(-1.2, Math.min(1.2, st.rotX));
      st.lastMouse = { x: t.clientX, y: t.clientY };
    };
    const onTouchEnd = () => {
      const st = stateRef.current;
      if (!st.dragMoved && st.touchStart && onNodeSelectRef.current) {
        const rect = canvas.getBoundingClientRect();
        const mx = st.touchStart.x - rect.left;
        const my = st.touchStart.y - rect.top;
        let hit = null;
        let bestDist = 40;
        for (const p of st.lastProjected || []) {
          const ddx = mx - p.sx, ddy = my - p.sy;
          const dist = Math.sqrt(ddx * ddx + ddy * ddy);
          if (dist < bestDist) { bestDist = dist; hit = p; }
        }
        onNodeSelectRef.current(hit ? { key: hit.key, node: hit.node, sx: hit.sx, sy: hit.sy } : null);
      }
      st.dragging = false;
      st.lastMouse = null;
      st.touchStart = null;
    };

    canvas.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('touchstart', onTouchStart, { passive: false });
    canvas.addEventListener('touchmove', onTouchMove, { passive: false });
    canvas.addEventListener('touchend', onTouchEnd);

    // ── Render loop ──
    const animate = () => {
      const st = stateRef.current;
      if (!st.inited) { animRef.current = requestAnimationFrame(animate); return; }
      const t = Date.now() * 0.001;
      const cx = w / 2, cy = h / 2 + 30;
      const fov = 3.5;

      // Auto-rotate slowly when not dragging
      if (!st.dragging) st.autoRotY += 0.002;
      const totalRotY = st.rotY + st.autoRotY;
      const totalRotX = st.rotX;

      // Clear
      ctx.clearRect(0, 0, w, h);

      // Project all organ nodes to 2D
      const projected = {};
      for (const [label, node] of Object.entries(st.nodes)) {
        node.breathe += 0.025;
        const bob = Math.sin(node.breathe) * 0.06;
        let { x, y, z } = rotY(node.x3, node.y3 + bob, node.z3, totalRotY);
        ({ x, y, z } = rotX(x, y, z, totalRotX));
        const p = project(x, y, z, cx, cy, fov);
        projected[label] = { ...p, z, node };
        node.activity *= 0.992;
        if (node.activity < 0.01) node.phase = '';
        node.orbiters.forEach(o => { o.angle += o.speed * (1 + node.activity * 3); });
        if (node.activity < 0.1 && node.orbiters.length > 3) node.orbiters.pop();
        node.shockwaves = node.shockwaves.filter(sw => { sw.life *= 0.94; sw.radius += (sw.max - sw.radius) * 0.08; return sw.life > 0.02; });
      }

      // Project dynamic agent nodes
      const agentProjected = {};
      for (const [id, node] of Object.entries(st.agentNodes || {})) {
        node.breathe += 0.03;
        node.spawnAnim = Math.min((node.spawnAnim || 0) + 0.04, 1);
        node.activity += (node.targetActivity - node.activity) * 0.05;
        const bob = Math.sin(node.breathe) * 0.04;
        let { x, y, z } = rotY(node.x3, node.y3 + bob, node.z3, totalRotY);
        ({ x, y, z } = rotX(x, y, z, totalRotX));
        const p = project(x, y, z, cx, cy, fov);
        agentProjected[id] = { ...p, z, node };
        node.orbiters.forEach(o => { o.angle += o.speed * (1 + node.activity * 2); });
        node.shockwaves = (node.shockwaves || []).filter(sw => { sw.life *= 0.94; sw.radius += (sw.max - sw.radius) * 0.08; return sw.life > 0.02; });
      }

      // Motes
      st.motes.forEach(m => {
        m.x += m.vx + Math.sin(t + m.phase) * 0.001;
        m.y += m.vy + Math.cos(t * 0.7 + m.phase) * 0.001;
        m.z += m.vz;
        if (m.x > 2) m.x = -2; if (m.x < -2) m.x = 2;
        if (m.y > 2) m.y = -2; if (m.y < -2) m.y = 2;
        if (m.z > 1.5) m.z = -1.5; if (m.z < -1.5) m.z = 1.5;
        let { x, y, z } = rotY(m.x, m.y, m.z, totalRotY);
        ({ x, y, z } = rotX(x, y, z, totalRotX));
        const p = project(x, y, z, cx, cy, fov);
        const flicker = 0.2 + Math.sin(t * 3 + m.phase) * 0.15;
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, m.size * p.scale, 0, Math.PI * 2);
        ctx.fillStyle = rgba(m.color, flicker * p.scale);
        ctx.fill();
      });

      // Merge organ + agent nodes, sort by Z (far first)
      const allProjected = [
        ...Object.entries(projected).map(([k, v]) => ({ key: k, ...v })),
        ...Object.entries(agentProjected).map(([k, v]) => ({ key: `agent_${k}`, ...v })),
      ];
      allProjected.sort((a, b) => a.z - b.z);

      // Cache projected positions for click hit-testing
      st.lastProjected = allProjected.map(p => ({ key: p.key, sx: p.sx, sy: p.sy, scale: p.scale, node: p.node }));

      // Draw organ connections
      for (const [fromLabel, toLabel] of CONNECTIONS) {
        const a = projected[fromLabel], b = projected[toLabel];
        if (!a || !b) continue;
        const act = Math.max(a.node.activity, b.node.activity) * 0.5;
        const alpha = 0.04 + act * 0.3;
        const avgScale = (a.scale + b.scale) / 2;

        ctx.beginPath();
        ctx.moveTo(a.sx, a.sy);
        ctx.lineTo(b.sx, b.sy);
        ctx.strokeStyle = rgba(a.node.color, alpha * avgScale);
        ctx.lineWidth = (0.5 + act * 2) * avgScale;
        ctx.stroke();

        // Lightning jitter when active
        if (act > 0.2) {
          ctx.beginPath();
          ctx.moveTo(a.sx, a.sy);
          for (let i = 1; i <= 5; i++) {
            const frac = i / 5;
            ctx.lineTo(
              a.sx + (b.sx - a.sx) * frac + (Math.random() - 0.5) * 10 * act * avgScale,
              a.sy + (b.sy - a.sy) * frac + (Math.random() - 0.5) * 10 * act * avgScale,
            );
          }
          ctx.strokeStyle = rgba(a.node.color, act * 0.2 * avgScale);
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      // Draw agent→cortex connections (dashed style)
      const cortexP = projected['cortex'];
      if (cortexP) {
        for (const [, ap] of Object.entries(agentProjected)) {
          const anim = ap.node.spawnAnim || 0;
          const act = ap.node.activity * anim;
          const avgScale = (cortexP.scale + ap.scale) / 2;
          ctx.save();
          ctx.setLineDash([4 * avgScale, 4 * avgScale]);
          ctx.beginPath();
          ctx.moveTo(cortexP.sx, cortexP.sy);
          ctx.lineTo(ap.sx, ap.sy);
          ctx.strokeStyle = rgba(ap.node.color, (0.08 + act * 0.4) * avgScale);
          ctx.lineWidth = (0.5 + act * 1.5) * avgScale;
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.restore();
        }
      }

      // Draw all nodes (organ + agent, sorted far→near)
      for (const item of allProjected) {
        const { sx, sy, scale, node } = item;
        const isAgent = !!node.isAgent;
        const anim = isAgent ? (node.spawnAnim || 0) : 1;
        const baseR = isAgent ? 14 : 20;
        const r = baseR * scale * anim;
        if (r < 0.5) continue;
        const act = node.activity;
        const color = node.color;

        // Shockwaves
        (node.shockwaves || []).forEach(sw => {
          ctx.beginPath();
          ctx.arc(sx, sy, sw.radius * scale * anim, 0, Math.PI * 2);
          ctx.strokeStyle = rgba(color, sw.life * 0.5 * scale);
          ctx.lineWidth = (2 + sw.life * 3) * scale;
          ctx.stroke();
        });

        // Outer glow
        if (act > 0.02) {
          const glowR = r + (isAgent ? 15 : 25 + act * 50) * scale * anim;
          const grad = ctx.createRadialGradient(sx, sy, r * 0.3, sx, sy, glowR);
          grad.addColorStop(0, rgba(color, act * 0.35 * scale));
          grad.addColorStop(0.5, rgba(color, act * 0.1 * scale));
          grad.addColorStop(1, rgba(color, 0));
          ctx.beginPath(); ctx.arc(sx, sy, glowR, 0, Math.PI * 2);
          ctx.fillStyle = grad; ctx.fill();
        }

        // Pulsing ring
        const ringR = r + (isAgent ? 4 : 6 + act * 10 + Math.sin(t * 3 + node.breathe) * 2) * scale * anim;
        ctx.beginPath(); ctx.arc(sx, sy, ringR, 0, Math.PI * 2);
        ctx.strokeStyle = rgba(color, (0.12 + act * 0.35) * scale);
        ctx.lineWidth = (1 + act * 1.5) * scale; ctx.stroke();

        // Agent: dashed ring for awaiting_approval
        if (isAgent && node.status === 'awaiting_approval') {
          ctx.save();
          ctx.setLineDash([3, 3]);
          ctx.beginPath(); ctx.arc(sx, sy, ringR + 4 * scale, 0, Math.PI * 2);
          ctx.strokeStyle = rgba('#fbbf24', 0.6 * scale);
          ctx.lineWidth = 1.5 * scale; ctx.stroke();
          ctx.setLineDash([]);
          ctx.restore();
        }

        // Orbiters
        (node.orbiters || []).forEach(o => {
          const ox = sx + Math.cos(o.angle) * o.dist * scale * anim;
          const oy = sy + Math.sin(o.angle) * o.dist * scale * anim;
          ctx.beginPath(); ctx.arc(ox, oy, o.size * (0.5 + act * 0.5) * scale, 0, Math.PI * 2);
          ctx.fillStyle = rgba(color, (0.25 + act * 0.5) * scale);
          ctx.fill();
        });

        // Core sphere gradient (agents are hexagonal-ish via smaller radius)
        const coreGrad = ctx.createRadialGradient(sx - r * 0.2, sy - r * 0.25, 0, sx, sy, r);
        coreGrad.addColorStop(0, rgba('#ffffff', (0.2 + act * 0.3) * scale * anim));
        coreGrad.addColorStop(0.4, rgba(color, (0.6 + act * 0.4) * scale * anim));
        coreGrad.addColorStop(1, rgba(color, (0.25 + act * 0.2) * scale * anim));
        ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.fillStyle = coreGrad; ctx.fill();

        // Border (agents get a double border)
        ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.strokeStyle = rgba(color, (0.5 + act * 0.5) * scale * anim);
        ctx.lineWidth = (isAgent ? 1.8 : 1.2 + act * 1.2) * scale; ctx.stroke();

        // Hot center
        if (act > 0.3) {
          ctx.beginPath(); ctx.arc(sx, sy, r * 0.3, 0, Math.PI * 2);
          ctx.fillStyle = rgba('#ffffff', act * 0.4 * scale);
          ctx.fill();
        }

        // Label
        const fontSize = Math.max(7, (isAgent ? 8 : 10) * scale);
        ctx.fillStyle = rgba('#ffffff', (0.5 + act * 0.4) * scale * anim);
        ctx.font = `${act > 0.3 ? 'bold ' : ''}${fontSize}px monospace`;
        ctx.textAlign = 'center';
        ctx.fillText(node.label.toUpperCase(), sx, sy + r + (isAgent ? 10 : 14) * scale);

        // Phase / status label
        if (node.phase && act > 0.1) {
          ctx.save();
          ctx.shadowColor = color; ctx.shadowBlur = 6 * scale;
          ctx.fillStyle = rgba(color, (0.7 + act * 0.3) * scale);
          ctx.font = `${Math.max(6, (isAgent ? 7 : 9) * scale)}px monospace`;
          ctx.fillText(node.phase, sx, sy - r - (isAgent ? 6 : 8) * scale);
          ctx.restore();
        }
      }

      animRef.current = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      canvas.removeEventListener('mousedown', onMouseDown);
      canvas.removeEventListener('touchstart', onTouchStart);
      canvas.removeEventListener('touchmove', onTouchMove);
      canvas.removeEventListener('touchend', onTouchEnd);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [organColors]);

  // ── Process thinking events ──
  useEffect(() => {
    if (!thinkingEvents || thinkingEvents.length === 0) return;
    const latest = thinkingEvents[thinkingEvents.length - 1];
    if (!latest) return;
    const data = latest.data || latest;
    const organ = data.organ;
    const phase = data.phase;
    const content = data.content || '';
    const token = data.token || '';
    const st = stateRef.current;

    if (organ && st.nodes[organ]) {
      const node = st.nodes[organ];
      node.activity = Math.min(node.activity + 0.5, 1.0);
      node.phase = phase || '';
      node.shockwaves.push({ radius: 5, max: 70 + Math.random() * 30, life: 1 });
      if (node.orbiters.length < 8) {
        node.orbiters.push({ angle: Math.random() * Math.PI * 2, speed: 0.03 + Math.random() * 0.03, dist: 32 + Math.random() * 18, size: 2 + Math.random() * 2 });
      }
    }
    if (token || content) setActiveTokens(content.slice(-150));
    if (organ) setActiveOrgan(organ);
    if (phase) setActivePhase(phase);
  }, [thinkingEvents]);

  return (
    <div className="relative w-full h-full" style={{ cursor: 'grab' }}>
      <canvas ref={canvasRef} className="w-full h-full" style={{ display: 'block' }} />

      {/* Active organ indicator */}
      {activeOrgan && (
        <div className="absolute top-3 left-3 pointer-events-none">
          <span className="text-xs px-2.5 py-1 rounded-full backdrop-blur-md animate-pulse" style={{ backgroundColor: rgba(organColors[activeOrgan] || '#888', 0.2), color: organColors[activeOrgan] || '#888', boxShadow: `0 0 12px ${rgba(organColors[activeOrgan] || '#888', 0.3)}`, border: `1px solid ${rgba(organColors[activeOrgan] || '#888', 0.3)}` }}>
            {activeOrgan} · {activePhase}
          </span>
        </div>
      )}

      {/* Thinking stream */}
      {activeTokens && (
        <div className="absolute bottom-16 left-0 right-0 p-4 bg-gradient-to-t from-black/60 via-black/30 to-transparent pointer-events-none">
          <div className="flex items-start gap-2 max-w-xl">
            <Zap size={14} className="text-yellow-400 mt-0.5 shrink-0 animate-pulse drop-shadow-[0_0_6px_rgba(250,204,21,0.5)]" />
            <p className="text-xs text-white/70 font-mono leading-relaxed break-words">
              {activeTokens}
              <span className="inline-block w-2 h-3.5 bg-yellow-400/80 ml-0.5 animate-pulse rounded-sm" />
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
