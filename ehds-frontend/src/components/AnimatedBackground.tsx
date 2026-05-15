import { useEffect, useRef } from 'react';

interface P {
  x: number; y: number;
  vx: number; vy: number;
  r: number;
  hue: number;
  a: number;
  da: number;
}

export function AnimatedBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const mouse = { x: -9999, y: -9999 };
    let particles: P[] = [];

    const init = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      const N = Math.min(80, Math.floor((canvas.width * canvas.height) / 13000));
      particles = Array.from({ length: N }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        r: Math.random() * 1.8 + 0.8,
        hue: 195 + Math.random() * 80,   // cyan → blue → indigo
        a: Math.random() * 0.4 + 0.15,
        da: (Math.random() * 0.005 + 0.001) * (Math.random() > 0.5 ? 1 : -1),
      }));
    };

    const LINK_D = 125;
    const REPEL_D = 140;
    const REPEL_F = 0.033;

    const tick = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const { width: w, height: h } = canvas;

      for (const p of particles) {
        const dx = p.x - mouse.x;
        const dy = p.y - mouse.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < REPEL_D * REPEL_D && d2 > 0) {
          const d = Math.sqrt(d2);
          const f = (1 - d / REPEL_D) * REPEL_F;
          p.vx += (dx / d) * f;
          p.vy += (dy / d) * f;
        }

        p.vx *= 0.982;
        p.vy *= 0.982;
        p.x = (p.x + p.vx + w) % w;
        p.y = (p.y + p.vy + h) % h;

        p.a += p.da;
        if (p.a > 0.58 || p.a < 0.08) p.da *= -1;
      }

      // Edges (gradient lines)
      for (let i = 0; i < particles.length - 1; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < LINK_D) {
            const alpha = (1 - d / LINK_D) * 0.1;
            const g = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
            g.addColorStop(0, `hsla(${a.hue},78%,68%,${alpha})`);
            g.addColorStop(1, `hsla(${b.hue},78%,68%,${alpha})`);
            ctx.beginPath();
            ctx.strokeStyle = g;
            ctx.lineWidth = 0.7;
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // Nodes: outer glow + solid core
      for (const p of particles) {
        const grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4.5);
        grd.addColorStop(0, `hsla(${p.hue},80%,72%,${p.a * 0.35})`);
        grd.addColorStop(1, `hsla(${p.hue},80%,72%,0)`);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * 4.5, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${p.hue},92%,78%,${p.a})`;
        ctx.fill();
      }

      animId = requestAnimationFrame(tick);
    };

    const onMouse = (e: MouseEvent) => { mouse.x = e.clientX; mouse.y = e.clientY; };
    const onLeave = () => { mouse.x = -9999; mouse.y = -9999; };

    init();
    window.addEventListener('resize', init);
    window.addEventListener('mousemove', onMouse);
    window.addEventListener('mouseleave', onLeave);
    tick();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', init);
      window.removeEventListener('mousemove', onMouse);
      window.removeEventListener('mouseleave', onLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0, left: 0,
        width: '100%', height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
        opacity: 0.55,
      }}
    />
  );
}
