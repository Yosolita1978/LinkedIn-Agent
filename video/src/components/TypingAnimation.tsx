import React from "react";
import { useCurrentFrame } from "remotion";
import { COLORS } from "./theme";

interface TypingAnimationProps {
  text: string;
  startFrame?: number;
  charsPerFrame?: number;
  style?: React.CSSProperties;
  showCursor?: boolean;
}

export const TypingAnimation: React.FC<TypingAnimationProps> = ({
  text,
  startFrame = 0,
  charsPerFrame = 2,
  style,
  showCursor = true,
}) => {
  const frame = useCurrentFrame();
  const elapsed = Math.max(0, frame - startFrame);
  const charCount = Math.min(Math.floor(elapsed * charsPerFrame), text.length);
  const displayedText = text.substring(0, charCount);
  const isTyping = charCount < text.length;
  const cursorVisible = showCursor && (isTyping ? true : Math.floor(frame / 15) % 2 === 0);

  return (
    <span style={style}>
      {displayedText}
      {showCursor && (
        <span
          style={{
            opacity: cursorVisible ? 1 : 0,
            color: COLORS.coolLight,
            fontWeight: 400,
          }}
        >
          |
        </span>
      )}
    </span>
  );
};
