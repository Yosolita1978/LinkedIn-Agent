import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { COLORS, FONTS } from "../components/theme";
import { LaptopMockup } from "../components/LaptopMockup";
import { FadeIn } from "../components/FadeIn";

// Mock data
const CONTACT = {
  name: "Maria Rodriguez",
  title: "Senior PM at Microsoft",
  location: "Seattle, WA",
  score: 92,
  segment: "Cascadia AI",
  about: "Product leader focused on AI-powered developer tools. Previously at GitHub. Passionate about building inclusive tech communities in the Pacific Northwest.",
};

const BREAKDOWN = [
  { label: "Recency", value: 28, max: 30, color: COLORS.hot },
  { label: "Frequency", value: 16, max: 20, color: COLORS.warm },
  { label: "Depth", value: 22, max: 25, color: COLORS.cool },
  { label: "Responsiveness", value: 12, max: 15, color: COLORS.green },
  { label: "Initiation", value: 9, max: 10, color: COLORS.purple },
];

const MESSAGES = { total: 47, sent: 22, received: 25 };

export const SceneContactDetail: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Warmth badge bounce
  const badgeScale = spring({
    frame: frame - 15,
    fps,
    config: { damping: 8, stiffness: 120 },
  });

  return (
    <LaptopMockup activeNav="Contacts" url="localhost:5173/contacts/142">
      <div style={{ fontFamily: FONTS.sans }}>
        {/* Back link */}
        <FadeIn delay={0} duration={8}>
          <p style={{ fontSize: 12, color: COLORS.coolLight, margin: "0 0 12px 0" }}>
            &larr; Back to Contacts
          </p>
        </FadeIn>

        {/* Header card */}
        <FadeIn delay={5} duration={12}>
          <div
            style={{
              backgroundColor: COLORS.card,
              borderRadius: 8,
              border: `1px solid ${COLORS.border}`,
              padding: 20,
              marginBottom: 16,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h1 style={{ fontSize: 22, fontWeight: 700, color: COLORS.white, margin: 0 }}>
                  {CONTACT.name}
                </h1>
                <p style={{ fontSize: 14, color: COLORS.textMuted, margin: "4px 0 0 0" }}>
                  {CONTACT.title}
                </p>
                <p style={{ fontSize: 12, color: COLORS.textDim, margin: "2px 0 0 0" }}>
                  {CONTACT.location}
                </p>
                {/* Segment badge */}
                <span
                  style={{
                    display: "inline-block",
                    marginTop: 8,
                    padding: "3px 10px",
                    borderRadius: 9999,
                    fontSize: 11,
                    fontWeight: 500,
                    backgroundColor: "rgba(6,182,212,0.2)",
                    color: COLORS.cyan,
                  }}
                >
                  {CONTACT.segment}
                </span>
              </div>

              {/* Big warmth badge */}
              <div
                style={{
                  transform: `scale(${interpolate(badgeScale, [0, 1], [0, 1])})`,
                  backgroundColor: COLORS.hotBg,
                  color: COLORS.hotLight,
                  borderRadius: 9999,
                  padding: "6px 16px",
                  fontSize: 20,
                  fontWeight: 700,
                }}
              >
                HOT {CONTACT.score}
              </div>
            </div>

            {/* About */}
            <p
              style={{
                fontSize: 12,
                color: COLORS.textMuted,
                margin: "14px 0 0 0",
                paddingTop: 14,
                borderTop: `1px solid ${COLORS.border}`,
                lineHeight: 1.5,
              }}
            >
              {CONTACT.about}
            </p>
          </div>
        </FadeIn>

        {/* Warmth Breakdown — the hero animation */}
        <FadeIn delay={22} duration={10}>
          <div
            style={{
              backgroundColor: COLORS.card,
              borderRadius: 8,
              border: `1px solid ${COLORS.border}`,
              padding: 14,
              marginBottom: 16,
            }}
          >
            <p style={{ fontSize: 12, fontWeight: 500, color: COLORS.textMuted, margin: "0 0 12px 0" }}>
              Warmth Breakdown
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {BREAKDOWN.map((item, i) => {
                const barProgress = spring({
                  frame: frame - (28 + i * 8),
                  fps,
                  config: { damping: 18, stiffness: 80 },
                });
                const pct = (item.value / item.max) * 100;

                return (
                  <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ fontSize: 11, color: COLORS.textDim, width: 100, flexShrink: 0 }}>
                      {item.label}
                    </span>
                    <div
                      style={{
                        flex: 1,
                        height: 10,
                        backgroundColor: COLORS.barBg,
                        borderRadius: 9999,
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          borderRadius: 9999,
                          backgroundColor: item.color,
                          width: `${pct * barProgress}%`,
                        }}
                      />
                    </div>
                    <span style={{ fontSize: 11, color: COLORS.textDim, width: 40, textAlign: "right" }}>
                      {item.value}/{item.max}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </FadeIn>

        {/* Message Stats */}
        <FadeIn delay={80} duration={12}>
          <div
            style={{
              backgroundColor: COLORS.card,
              borderRadius: 8,
              border: `1px solid ${COLORS.border}`,
              padding: 14,
              marginBottom: 16,
            }}
          >
            <p style={{ fontSize: 12, fontWeight: 500, color: COLORS.textMuted, margin: "0 0 10px 0" }}>
              Messages
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, textAlign: "center" }}>
              {[
                { label: "Total", value: MESSAGES.total },
                { label: "Sent", value: MESSAGES.sent },
                { label: "Received", value: MESSAGES.received },
              ].map((stat) => (
                <div key={stat.label}>
                  <p style={{ fontSize: 20, fontWeight: 700, color: COLORS.white, margin: 0 }}>
                    {stat.value}
                  </p>
                  <p style={{ fontSize: 10, color: COLORS.textDim, margin: 0 }}>{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </FadeIn>

        {/* Resurrection Opportunity */}
        <FadeIn delay={100} duration={12}>
          <div
            style={{
              backgroundColor: COLORS.card,
              borderRadius: 8,
              border: `1px solid ${COLORS.border}`,
              padding: 14,
            }}
          >
            <p style={{ fontSize: 12, fontWeight: 500, color: COLORS.textMuted, margin: "0 0 10px 0" }}>
              Outreach Opportunities
            </p>
            <div
              style={{
                padding: 10,
                backgroundColor: COLORS.amberBgLight,
                border: `1px solid ${COLORS.amberBorder}`,
                borderRadius: 8,
              }}
            >
              <p style={{ fontSize: 11, fontWeight: 500, color: COLORS.amberLight, margin: "0 0 4px 0" }}>
                Promise Made
              </p>
              <p style={{ fontSize: 12, color: COLORS.text, margin: 0, lineHeight: 1.4 }}>
                You mentioned grabbing coffee next time you&apos;re in Seattle — she replied enthusiastically
              </p>
            </div>
          </div>
        </FadeIn>
      </div>
    </LaptopMockup>
  );
};
