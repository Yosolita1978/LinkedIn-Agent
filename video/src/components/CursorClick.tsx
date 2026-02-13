import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

interface CursorClickProps {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  moveStartFrame: number;
  clickFrame: number;
}

export const CursorClick: React.FC<CursorClickProps> = ({
  startX,
  startY,
  endX,
  endY,
  moveStartFrame,
  clickFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Cursor movement
  const moveProgress = spring({
    frame: frame - moveStartFrame,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  const cursorX = interpolate(moveProgress, [0, 1], [startX, endX]);
  const cursorY = interpolate(moveProgress, [0, 1], [startY, endY]);

  // Click ripple
  const clickActive = frame >= clickFrame;
  const rippleProgress = clickActive
    ? spring({
        frame: frame - clickFrame,
        fps,
        config: { damping: 12, stiffness: 100 },
      })
    : 0;

  // Only show after movement starts
  const visible = frame >= moveStartFrame;
  if (!visible) return null;

  return (
    <>
      {/* Cursor */}
      <svg
        width={24}
        height={24}
        viewBox="0 0 24 24"
        style={{
          position: "absolute",
          left: cursorX,
          top: cursorY,
          zIndex: 100,
          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.5))",
          pointerEvents: "none",
        }}
      >
        <path
          d="M5 3l14 8-6 2-4 6z"
          fill="white"
          stroke="#333"
          strokeWidth={1}
        />
      </svg>

      {/* Click ripple */}
      {clickActive && rippleProgress < 0.99 && (
        <div
          style={{
            position: "absolute",
            left: endX + 4,
            top: endY + 4,
            width: 40,
            height: 40,
            borderRadius: "50%",
            border: "2px solid rgba(59,130,246,0.6)",
            transform: `translate(-50%, -50%) scale(${rippleProgress * 2})`,
            opacity: 1 - rippleProgress,
            pointerEvents: "none",
            zIndex: 99,
          }}
        />
      )}
    </>
  );
};
