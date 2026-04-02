(function () {
  if (typeof window === "undefined") return;
  if (window.__creaseiqBeamsMounted) return;
  window.__creaseiqBeamsMounted = true;

  var body = document.body;
  if (!body) return;

  var layer = document.createElement("div");
  layer.setAttribute("id", "global-beams-layer");
  layer.style.position = "fixed";
  layer.style.inset = "0";
  layer.style.pointerEvents = "none";
  layer.style.zIndex = "0";
  layer.style.overflow = "hidden";

  var canvas = document.createElement("canvas");
  canvas.style.position = "absolute";
  canvas.style.inset = "0";
  canvas.style.width = "100%";
  canvas.style.height = "100%";
  canvas.style.filter = "blur(20px)";
  canvas.style.opacity = "0.5";

  var haze = document.createElement("div");
  haze.style.position = "absolute";
  haze.style.inset = "0";
  haze.style.backdropFilter = "blur(20px)";
  haze.style.background = "rgba(255, 223, 181, 0.08)";

  layer.appendChild(canvas);
  layer.appendChild(haze);
  body.prepend(layer);

  if (getComputedStyle(body).position === "static") {
    body.style.position = "relative";
  }

  Array.prototype.forEach.call(body.children, function (child) {
    if (child === layer) return;
    var style = getComputedStyle(child);
    if (style.position === "static") {
      child.style.position = "relative";
    }
    if (!style.zIndex || style.zIndex === "auto") {
      child.style.zIndex = "1";
    }
  });

  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  var animationId = 0;
  var beams = [];
  var minimumBeams = 20;
  var palette = [];

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function rgbToHsl(r, g, b) {
    var rn = r / 255;
    var gn = g / 255;
    var bn = b / 255;
    var max = Math.max(rn, gn, bn);
    var min = Math.min(rn, gn, bn);
    var h = 0;
    var s = 0;
    var l = (max + min) / 2;

    if (max !== min) {
      var d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case rn:
          h = (gn - bn) / d + (gn < bn ? 6 : 0);
          break;
        case gn:
          h = (bn - rn) / d + 2;
          break;
        default:
          h = (rn - gn) / d + 4;
          break;
      }
      h = h / 6;
    }

    return {
      h: Math.round(h * 360),
      s: Math.round(s * 100),
      l: Math.round(l * 100),
    };
  }

  function parseColorToHsl(input) {
    if (!input) return null;
    var color = String(input).trim().toLowerCase();

    if (color[0] === "#") {
      var hex = color.slice(1);
      if (hex.length === 3) {
        hex = hex.split("").map(function (c) { return c + c; }).join("");
      }
      if (hex.length !== 6) return null;
      var rHex = parseInt(hex.slice(0, 2), 16);
      var gHex = parseInt(hex.slice(2, 4), 16);
      var bHex = parseInt(hex.slice(4, 6), 16);
      if (Number.isNaN(rHex) || Number.isNaN(gHex) || Number.isNaN(bHex)) return null;
      return rgbToHsl(rHex, gHex, bHex);
    }

    var rgbMatch = color.match(/^rgba?\(([^)]+)\)$/);
    if (rgbMatch) {
      var parts = rgbMatch[1].split(",").map(function (part) {
        return parseFloat(part.trim());
      });
      if (parts.length >= 3) {
        return rgbToHsl(parts[0], parts[1], parts[2]);
      }
    }

    return null;
  }

  function resolvePalette() {
    var root = getComputedStyle(document.documentElement);
    var cssColors = [
      root.getPropertyValue("--primary"),
      root.getPropertyValue("--secondary"),
      root.getPropertyValue("--chart-2"),
      root.getPropertyValue("--chart-4"),
      root.getPropertyValue("--chart-5"),
    ];

    var converted = cssColors
      .map(parseColorToHsl)
      .filter(function (entry) { return !!entry; });

    if (converted.length > 0) {
      return converted.map(function (entry, idx) {
        return {
          h: (entry.h + (idx % 2 === 0 ? -4 : 4) + 360) % 360,
          s: clamp(entry.s + 8, 25, 95),
          l: clamp(entry.l + (idx % 2 === 0 ? 4 : -2), 35, 82),
        };
      });
    }

    return [
      { h: 18, s: 40, l: 48 },
      { h: 28, s: 76, l: 72 },
      { h: 34, s: 68, l: 78 },
      { h: 22, s: 34, l: 44 },
    ];
  }

  function createBeam(width, height, i, total) {
    var angle = -35 + Math.random() * 10;
    var tone = palette[i % palette.length] || { h: 24, s: 60, l: 60 };
    return {
      x: (i % 3) * (width / 3) + width / 6 + (Math.random() - 0.5) * (width / 6),
      y: Math.random() * height * 1.5,
      width: 80 + Math.random() * 120,
      length: height * 2.5,
      angle: angle,
      speed: 0.5 + Math.random() * 0.7,
      opacity: 0.12 + Math.random() * 0.2,
      hue: (tone.h + (Math.random() - 0.5) * 8 + 360) % 360,
      sat: clamp(tone.s + (Math.random() - 0.5) * 10, 30, 95),
      light: clamp(tone.l + (Math.random() - 0.5) * 8, 32, 85),
      pulse: Math.random() * Math.PI * 2,
      pulseSpeed: 0.02 + Math.random() * 0.03,
    };
  }

  function resize() {
    var dpr = window.devicePixelRatio || 1;
    var w = window.innerWidth;
    var h = window.innerHeight;

    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    palette = resolvePalette();

    var total = Math.floor(minimumBeams * 1.5);
    beams = Array.from({ length: total }, function (_, i) {
      return createBeam(w, h, i, total);
    });
  }

  function resetBeam(beam, index, total) {
    var w = window.innerWidth;
    var h = window.innerHeight;
    var column = index % 3;
    var spacing = w / 3;
    beam.y = h + 120;
    beam.x = column * spacing + spacing / 2 + (Math.random() - 0.5) * spacing * 0.5;
    beam.width = 90 + Math.random() * 120;
    beam.speed = 0.45 + Math.random() * 0.45;
    var tone = palette[index % palette.length] || { h: 24, s: 60, l: 60 };
    beam.hue = (tone.h + (Math.random() - 0.5) * 10 + 360) % 360;
    beam.sat = clamp(tone.s + (Math.random() - 0.5) * 12, 30, 95);
    beam.light = clamp(tone.l + (Math.random() - 0.5) * 8, 32, 85);
    beam.opacity = 0.16 + Math.random() * 0.12;
  }

  function drawBeam(beam) {
    ctx.save();
    ctx.translate(beam.x, beam.y);
    ctx.rotate((beam.angle * Math.PI) / 180);

    var p = beam.opacity * (0.8 + Math.sin(beam.pulse) * 0.2);
    var gradient = ctx.createLinearGradient(0, 0, 0, beam.length);
    gradient.addColorStop(0, "hsla(" + beam.hue + ", " + beam.sat + "%, " + beam.light + "%, 0)");
    gradient.addColorStop(0.1, "hsla(" + beam.hue + ", " + beam.sat + "%, " + beam.light + "%, " + p * 0.45 + ")");
    gradient.addColorStop(0.4, "hsla(" + beam.hue + ", " + beam.sat + "%, " + beam.light + "%, " + p + ")");
    gradient.addColorStop(0.6, "hsla(" + beam.hue + ", " + beam.sat + "%, " + beam.light + "%, " + p + ")");
    gradient.addColorStop(0.9, "hsla(" + beam.hue + ", " + beam.sat + "%, " + beam.light + "%, " + p * 0.45 + ")");
    gradient.addColorStop(1, "hsla(" + beam.hue + ", " + beam.sat + "%, " + beam.light + "%, 0)");

    ctx.fillStyle = gradient;
    ctx.fillRect(-beam.width / 2, 0, beam.width, beam.length);
    ctx.restore();
  }

  function animate() {
    var w = window.innerWidth;
    var h = window.innerHeight;
    ctx.clearRect(0, 0, w, h);
    ctx.filter = "blur(35px)";

    var total = beams.length;
    beams.forEach(function (beam, index) {
      beam.y -= beam.speed;
      beam.pulse += beam.pulseSpeed;
      if (beam.y + beam.length < -100) {
        resetBeam(beam, index, total);
      }
      drawBeam(beam);
    });

    animationId = window.requestAnimationFrame(animate);
  }

  resize();
  animate();

  window.addEventListener("resize", resize);
  window.addEventListener("beforeunload", function () {
    if (animationId) window.cancelAnimationFrame(animationId);
  });
})();
