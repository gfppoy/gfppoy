/* Evolutionary ecology, adapted from the supplied animation.
   All content and links work without this decorative script. */
(() => {
  "use strict";

  const canvas = document.getElementById("ecology");
  const hero = document.querySelector(".hero");
  const toggle = document.getElementById("animation-toggle");
  if (!canvas || !hero || !toggle) return;

  let ctx;
  try { ctx = canvas.getContext("2d"); } catch { return; }
  if (!ctx) return;

  const COLORS = ["#637f6b", "#9b8c66", "#7889a2", "#a47e75"];
  const MAX_NODES = 3500;
  const MAX_TIPS = 155;
  const FRAME_INTERVAL = 1000 / 30;
  const HOLD_DURATION = 2400;
  const FADE_DURATION = 1600;
  const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
  const random = (min, max) => min + Math.random() * (max - min);

  let width = 0;
  let height = 0;
  let pixelRatio = 0;
  let nodes = [];
  let tips = [];
  let tick = 0;
  let phase = "growing";
  let phaseStarted = 0;
  let cycleOpacity = 1;
  let frameId = null;
  let lastFrame = 0;
  let stoppedAt = null;
  let inView = true;
  let paused = motionPreference.matches;
  const mouse = { x: -999, y: -999 };

  function reset() {
    nodes = [];
    tips = [];
    tick = 0;
    phase = "growing";
    cycleOpacity = 1;

    for (let i = 0; i < 5; i++) {
      nodes.push({
        x: width * (0.15 + 0.7 * (i + 0.5) / 5) + random(-8, 8),
        y: height * (i % 2 ? 0.75 : 0.25),
        parent: -1,
        color: i % COLORS.length,
        organism: i
      });
      tips.push({
        id: i,
        angle: random(0, Math.PI * 2),
        alive: true,
        color: i % COLORS.length,
        organism: i
      });
    }

    // Start with a little growth so the art is visible immediately,
    // including as a still image when reduced motion is enabled.
    for (let i = 0; i < 65; i++) {
      if (update()) break;
    }
  }

  function update() {
    tick++;
    // Iterate over a snapshot: branching may append more tips.
    for (const tip of [...tips]) {
      if (!tip.alive) continue;
      const parent = nodes[tip.id];
      const angle = tip.angle + Math.sin(tick * 0.02 + tip.id) * 0.13 + random(-0.2, 0.2);
      const step = random(1.5, 3.2);
      let x = parent.x + Math.cos(angle) * step;
      let y = parent.y + Math.sin(angle) * step;

      const distance = Math.hypot(mouse.x - x, mouse.y - y);
      if (distance < 55) {
        x += (x - mouse.x) / (distance + 1) * 1.3;
        y += (y - mouse.y) / (distance + 1) * 1.3;
      }

      if (x < 6 || x > width - 6 || y < 6 || y > height - 6 || nodes.length >= MAX_NODES) {
        tip.alive = false;
        continue;
      }

      let collision = false;
      for (let j = 0; j < 12; j++) {
        const other = nodes[Math.floor(Math.random() * nodes.length)];
        if (other.organism !== tip.organism && (x - other.x) ** 2 + (y - other.y) ** 2 < 30) {
          collision = true;
          break;
        }
      }
      if (collision) {
        tip.angle += random(-1.6, 1.6);
        continue;
      }

      const id = nodes.length;
      nodes.push({ x, y, parent: tip.id, color: tip.color, organism: tip.organism });
      tip.id = id;
      tip.angle = angle;
      if (Math.random() < 0.012 && tips.length < MAX_TIPS) {
        tips.push({ id, angle: angle + random(-1.3, 1.3), alive: true, color: tip.color, organism: tip.organism });
      }
    }
    return nodes.length >= MAX_NODES || tips.every(tip => !tip.alive);
  }

  function render() {
    ctx.clearRect(0, 0, width, height);
    ctx.lineWidth = 0.85;
    ctx.lineCap = "round";
    ctx.globalAlpha = 0.55 * cycleOpacity;

    // Batch lines by colour, instead of issuing a stroke per segment.
    for (let color = 0; color < COLORS.length; color++) {
      ctx.beginPath();
      ctx.strokeStyle = COLORS[color];
      for (const node of nodes) {
        if (node.parent < 0 || node.color !== color) continue;
        const parent = nodes[node.parent];
        ctx.moveTo(parent.x, parent.y);
        ctx.lineTo(node.x, node.y);
      }
      ctx.stroke();
    }

    ctx.globalAlpha = cycleOpacity;
    for (const tip of tips) {
      if (!tip.alive) continue;
      const node = nodes[tip.id];
      ctx.fillStyle = COLORS[tip.color];
      ctx.beginPath();
      ctx.arc(node.x, node.y, 1.6, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (rect.width < 1 || rect.height < 1) return;
    if (Math.abs(rect.width - width) < 1 && Math.abs(rect.height - height) < 1 && dpr === pixelRatio) return;

    width = rect.width;
    height = rect.height;
    pixelRatio = dpr;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    mouse.x = mouse.y = -999;
    reset();
    const now = performance.now();
    phaseStarted = now - 900;
    stoppedAt = frameId === null ? now : null;
    render();
  }

  function animate(time) {
    frameId = null;
    if (!shouldAnimate()) return;

    if (time - lastFrame >= FRAME_INTERVAL) {
      lastFrame = time;
      if (phase === "growing") {
        cycleOpacity = Math.min(1, (time - phaseStarted) / 900);
        if (update()) {
          phase = "holding";
          phaseStarted = time;
        }
      } else if (phase === "holding" && time - phaseStarted >= HOLD_DURATION) {
        phase = "fading";
        phaseStarted = time;
      } else if (phase === "fading") {
        cycleOpacity = Math.max(0, 1 - (time - phaseStarted) / FADE_DURATION);
        if (cycleOpacity === 0) {
          reset();
          phaseStarted = time;
          cycleOpacity = 0;
        }
      }
      render();
    }
    frameId = requestAnimationFrame(animate);
  }

  function shouldAnimate() {
    return !paused && !document.hidden && inView && width > 0 && height > 0;
  }

  function syncPlayback() {
    const now = performance.now();
    if (shouldAnimate() && frameId === null) {
      if (stoppedAt !== null) phaseStarted += now - stoppedAt;
      stoppedAt = null;
      lastFrame = 0;
      frameId = requestAnimationFrame(animate);
    } else if (!shouldAnimate() && frameId !== null) {
      cancelAnimationFrame(frameId);
      frameId = null;
      stoppedAt = now;
    }
    toggle.textContent = paused ? "Play animation" : "Pause animation";
    // Pressed means the pause state is active.
    toggle.setAttribute("aria-pressed", String(paused));
  }

  toggle.addEventListener("click", () => {
    paused = !paused;
    syncPlayback();
  });
  motionPreference.addEventListener("change", event => {
    paused = event.matches;
    if (paused) {
      reset();
      phaseStarted = performance.now() - 900;
      cycleOpacity = 1;
      render();
    }
    syncPlayback();
  });
  document.addEventListener("visibilitychange", syncPlayback);

  // The canvas itself never intercepts text selection or link clicks.
  hero.addEventListener("pointermove", event => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = event.clientX - rect.left;
    mouse.y = event.clientY - rect.top;
  }, { passive: true });
  hero.addEventListener("pointerleave", () => { mouse.x = mouse.y = -999; }, { passive: true });

  window.addEventListener("resize", () => { resize(); syncPlayback(); }, { passive: true });
  if ("ResizeObserver" in window) {
    new ResizeObserver(() => { resize(); syncPlayback(); }).observe(canvas);
  }
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(entries => {
      inView = entries[0].isIntersecting;
      syncPlayback();
    }).observe(hero);
  }

  resize();
  toggle.hidden = false;
  syncPlayback();
})();
