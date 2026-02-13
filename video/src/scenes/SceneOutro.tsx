import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { COLORS, FONTS } from "../components/theme";

export const SceneOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo
  const logoScale = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  const logoOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Tech stack
  const stackOpacity = interpolate(frame, [20, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const stackY = interpolate(frame, [20, 35], [10, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // GitHub line
  const ghOpacity = interpolate(frame, [35, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Glow
  const glowOpacity = interpolate(frame, [0, 30], [0, 0.25], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: COLORS.bg,
        fontFamily: FONTS.sans,
      }}
    >
      {/* Glow */}
      <div
        style={{
          position: "absolute",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${COLORS.emerald} 0%, transparent 70%)`,
          opacity: glowOpacity,
          filter: "blur(100px)",
        }}
      />

      {/* Logo */}
      <div
        style={{
          opacity: logoOpacity,
          transform: `scale(${interpolate(logoScale, [0, 1], [0.85, 1])})`,
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontSize: 64,
            fontWeight: 800,
            color: COLORS.white,
            margin: 0,
            letterSpacing: -1,
          }}
        >
          LinkedIn Agent
        </h1>
      </div>

      {/* Tech stack */}
      <p
        style={{
          opacity: stackOpacity,
          transform: `translateY(${stackY}px)`,
          fontSize: 18,
          color: COLORS.textMuted,
          marginTop: 20,
          textAlign: "center",
        }}
      >
        Built with FastAPI + React + OpenAI Agents SDK
      </p>

      {/* GitHub */}
      <p
        style={{
          opacity: ghOpacity,
          fontSize: 14,
          color: COLORS.textDim,
          marginTop: 16,
        }}
      >
        Open Source on GitHub
      </p>
    </AbsoluteFill>
  );
};
