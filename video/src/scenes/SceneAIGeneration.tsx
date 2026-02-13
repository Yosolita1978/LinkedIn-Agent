import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { COLORS, FONTS } from "../components/theme";
import { LaptopMockup } from "../components/LaptopMockup";
import { FadeIn } from "../components/FadeIn";
import { TypingAnimation } from "../components/TypingAnimation";
import { CursorClick } from "../components/CursorClick";

const MESSAGE_TEXT =
  "Hey Carlos! It's been a while since we chatted about that API integration project at Stripe. I've been diving deep into some similar work lately and thought of you. Would love to catch up and hear how things evolved on your end. Coffee chat sometime this week?";

const MESSAGE_TEXT_2 =
  "Carlos, hope you're doing well! I was reminiscing about our API integration conversation and wondered how things progressed. Let's reconnect soon.";

export const SceneAIGeneration: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Timeline:
  // 0-10: Page visible with generate section
  // 10-18: Cursor moves to Generate button
  // 18: Click on Generate
  // 20-40: "Generating..." spinner
  // 42: Variations appear, typing starts
  // 42-115: Typing animation for variation 1
  // 118-128: Variation 2 fades in
  // 130-140: Cursor clicks variation 1
  // 142-155: "Add to Queue" button fades in, cursor moves
  // 155: Click Add to Queue
  // 160-175: Success banner slides in
  // 175-210: Hold

  const showGenerating = frame >= 20 && frame < 42;
  const showVariations = frame >= 42;
  const variation1Selected = frame >= 135;
  const showAddButton = frame >= 142;
  const showSuccess = frame >= 162;

  // Success banner spring
  const successY = showSuccess
    ? spring({
        frame: frame - 162,
        fps,
        config: { damping: 12, stiffness: 100 },
      })
    : 0;

  return (
    <LaptopMockup activeNav="Contacts" url="localhost:5173/contacts/87">
      <div style={{ fontFamily: FONTS.sans, position: "relative" }}>
        {/* Abbreviated contact header */}
        <FadeIn delay={0} duration={8}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 16,
            }}
          >
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 700, color: COLORS.white, margin: 0 }}>
                Carlos Vega
              </h1>
              <p style={{ fontSize: 12, color: COLORS.textMuted, margin: "2px 0 0 0" }}>
                Senior Engineer at Stripe
              </p>
            </div>
            <span
              style={{
                padding: "4px 12px",
                borderRadius: 9999,
                fontSize: 14,
                fontWeight: 600,
                backgroundColor: COLORS.warmBg,
                color: COLORS.warmLight,
              }}
            >
              62
            </span>
          </div>
        </FadeIn>

        {/* Generate Message Section */}
        <FadeIn delay={4} duration={10}>
          <div
            style={{
              backgroundColor: COLORS.card,
              borderRadius: 8,
              border: `1px solid ${COLORS.border}`,
              padding: 16,
            }}
          >
            <p style={{ fontSize: 12, fontWeight: 500, color: COLORS.textMuted, margin: "0 0 12px 0" }}>
              Generate Message
            </p>

            {/* Controls row */}
            <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
              {/* Purpose dropdown */}
              <div
                style={{
                  padding: "7px 12px",
                  backgroundColor: COLORS.border,
                  border: `1px solid ${COLORS.textDim}`,
                  borderRadius: 8,
                  fontSize: 12,
                  color: COLORS.text,
                }}
              >
                reconnect
              </div>

              {/* Generate button */}
              <div
                style={{
                  padding: "7px 16px",
                  backgroundColor: showGenerating ? COLORS.textDim : COLORS.blue,
                  color: COLORS.white,
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 500,
                }}
              >
                {showGenerating ? "Generating..." : "Generate"}
              </div>
            </div>

            {/* Spinner animation */}
            {showGenerating && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <div
                  style={{
                    width: 16,
                    height: 16,
                    border: `2px solid ${COLORS.border}`,
                    borderTopColor: COLORS.coolLight,
                    borderRadius: "50%",
                    transform: `rotate(${(frame - 20) * 15}deg)`,
                  }}
                />
                <span style={{ fontSize: 11, color: COLORS.textDim }}>
                  AI is crafting your message...
                </span>
              </div>
            )}

            {/* Variations */}
            {showVariations && (
              <div>
                <p style={{ fontSize: 10, color: COLORS.textDim, margin: "0 0 10px 0" }}>
                  2 variation(s) — 847 tokens used
                </p>

                {/* Variation 1 */}
                <div
                  style={{
                    padding: 12,
                    borderRadius: 8,
                    border: `1px solid ${variation1Selected ? COLORS.blue : COLORS.border}`,
                    backgroundColor: variation1Selected ? COLORS.blueBg : "transparent",
                    marginBottom: 8,
                  }}
                >
                  <p style={{ fontSize: 10, color: COLORS.textDim, margin: "0 0 4px 0" }}>
                    Variation 1
                  </p>
                  <p style={{ fontSize: 12, color: COLORS.text, margin: 0, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                    <TypingAnimation
                      text={MESSAGE_TEXT}
                      startFrame={42}
                      charsPerFrame={2.5}
                      showCursor={frame < 135}
                    />
                  </p>
                </div>

                {/* Variation 2 */}
                <FadeIn delay={118} duration={10}>
                  <div
                    style={{
                      padding: 12,
                      borderRadius: 8,
                      border: `1px solid ${COLORS.border}`,
                      marginBottom: 10,
                    }}
                  >
                    <p style={{ fontSize: 10, color: COLORS.textDim, margin: "0 0 4px 0" }}>
                      Variation 2
                    </p>
                    <p style={{ fontSize: 12, color: COLORS.text, margin: 0, lineHeight: 1.5 }}>
                      {MESSAGE_TEXT_2}
                    </p>
                  </div>
                </FadeIn>

                {/* Add to Queue button */}
                {showAddButton && !showSuccess && (
                  <FadeIn delay={142} duration={8}>
                    <div
                      style={{
                        display: "inline-block",
                        padding: "7px 16px",
                        backgroundColor: COLORS.green,
                        color: COLORS.white,
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 500,
                      }}
                    >
                      Add to Queue
                    </div>
                  </FadeIn>
                )}

                {/* Success banner */}
                {showSuccess && (
                  <div
                    style={{
                      padding: 12,
                      backgroundColor: COLORS.greenBg,
                      border: `1px solid ${COLORS.greenBorder}`,
                      borderRadius: 8,
                      transform: `translateY(${interpolate(successY, [0, 1], [20, 0])}px)`,
                      opacity: successY,
                    }}
                  >
                    <p style={{ fontSize: 12, color: COLORS.green, margin: 0 }}>
                      Added to queue! <span style={{ textDecoration: "underline" }}>View queue</span>
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </FadeIn>

        {/* Cursor: clicks Generate button */}
        <CursorClick
          startX={700}
          startY={300}
          endX={365}
          endY={113}
          moveStartFrame={8}
          clickFrame={18}
        />

        {/* Cursor: clicks Variation 1 */}
        {frame >= 125 && (
          <CursorClick
            startX={365}
            startY={113}
            endX={500}
            endY={260}
            moveStartFrame={125}
            clickFrame={135}
          />
        )}

        {/* Cursor: clicks Add to Queue */}
        {frame >= 148 && (
          <CursorClick
            startX={500}
            startY={260}
            endX={360}
            endY={460}
            moveStartFrame={148}
            clickFrame={158}
          />
        )}
      </div>
    </LaptopMockup>
  );
};
