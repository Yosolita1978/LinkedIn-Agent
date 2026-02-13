import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { COLORS, FONTS } from "../components/theme";
import { LaptopMockup } from "../components/LaptopMockup";
import { FadeIn } from "../components/FadeIn";

// Mock data
const STATS = [
  { label: "Total Contacts", value: 847 },
  { label: "With Messages", value: 312 },
  { label: "Companies", value: 156 },
  { label: "Senior Contacts", value: 89 },
  { label: "Queue Drafts", value: 12 },
  { label: "Opportunities", value: 24 },
];

const WARMTH = { hot: 45, warm: 120, cool: 280, cold: 402 };
const WARMTH_TOTAL = 847;

const SEGMENTS = [
  { label: "MujerTech", count: 134, color: COLORS.pink },
  { label: "Cascadia AI", count: 89, color: COLORS.cyan },
  { label: "Job Target", count: 67, color: COLORS.amber },
  { label: "Untagged", count: 557, color: COLORS.textDim },
];

const TOP_CONTACTS = [
  { name: "Maria Rodriguez", company: "Microsoft", score: 92, msgs: 47 },
  { name: "James Chen", company: "Google", score: 87, msgs: 35 },
  { name: "Sofia Alvarez", company: "Meta", score: 81, msgs: 28 },
  { name: "David Park", company: "Amazon", score: 76, msgs: 22 },
  { name: "Ana Martinez", company: "Netflix", score: 73, msgs: 19 },
];

function WarmthBadgeInline({ score }: { score: number }) {
  const bg = score >= 70 ? COLORS.hotBg : score >= 40 ? COLORS.warmBg : COLORS.coolBg;
  const color = score >= 70 ? COLORS.hotLight : score >= 40 ? COLORS.warmLight : COLORS.coolLight;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 9999,
        fontSize: 12,
        fontWeight: 600,
        backgroundColor: bg,
        color,
      }}
    >
      {score}
    </span>
  );
}

export const SceneDashboard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Warmth bar animation
  const barProgress = spring({
    frame: frame - 40,
    fps,
    config: { damping: 20, stiffness: 60 },
  });

  // Segment bar animation
  const segBarProgress = spring({
    frame: frame - 55,
    fps,
    config: { damping: 20, stiffness: 60 },
  });

  return (
    <LaptopMockup activeNav="Dashboard" url="localhost:5173">
      <div style={{ fontFamily: FONTS.sans }}>
        {/* Title */}
        <FadeIn delay={0} duration={10}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: COLORS.white, margin: "0 0 20px 0" }}>
            Dashboard
          </h1>
        </FadeIn>

        {/* Stat Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12, marginBottom: 20 }}>
          {STATS.map((stat, i) => (
            <FadeIn key={stat.label} delay={8 + i * 5} duration={12}>
              <div
                style={{
                  backgroundColor: COLORS.card,
                  borderRadius: 8,
                  border: `1px solid ${COLORS.border}`,
                  padding: "12px 14px",
                }}
              >
                <p style={{ fontSize: 10, color: COLORS.textDim, margin: "0 0 4px 0" }}>
                  {stat.label}
                </p>
                <p style={{ fontSize: 22, fontWeight: 700, color: COLORS.white, margin: 0 }}>
                  {stat.value.toLocaleString()}
                </p>
              </div>
            </FadeIn>
          ))}
        </div>

        {/* Warmth + Segments side by side */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
          {/* Warmth Distribution */}
          <FadeIn delay={38} duration={12}>
            <div
              style={{
                backgroundColor: COLORS.card,
                borderRadius: 8,
                border: `1px solid ${COLORS.border}`,
                padding: 14,
              }}
            >
              <p style={{ fontSize: 12, fontWeight: 500, color: COLORS.textMuted, margin: "0 0 10px 0" }}>
                Warmth Distribution
              </p>
              <div
                style={{
                  display: "flex",
                  height: 14,
                  borderRadius: 9999,
                  overflow: "hidden",
                  backgroundColor: COLORS.barBg,
                  width: `${barProgress * 100}%`,
                }}
              >
                <div style={{ width: `${(WARMTH.hot / WARMTH_TOTAL) * 100}%`, backgroundColor: COLORS.hot }} />
                <div style={{ width: `${(WARMTH.warm / WARMTH_TOTAL) * 100}%`, backgroundColor: COLORS.warm }} />
                <div style={{ width: `${(WARMTH.cool / WARMTH_TOTAL) * 100}%`, backgroundColor: COLORS.cool }} />
                <div style={{ width: `${(WARMTH.cold / WARMTH_TOTAL) * 100}%`, backgroundColor: COLORS.cold }} />
              </div>
              <div style={{ display: "flex", gap: 14, marginTop: 8 }}>
                {[
                  { label: "Hot", count: WARMTH.hot, color: COLORS.hot },
                  { label: "Warm", count: WARMTH.warm, color: COLORS.warm },
                  { label: "Cool", count: WARMTH.cool, color: COLORS.cool },
                  { label: "Cold", count: WARMTH.cold, color: COLORS.cold },
                ].map((w) => (
                  <span key={w.label} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: COLORS.textDim }}>
                    <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: w.color, display: "inline-block" }} />
                    {w.label}: {w.count}
                  </span>
                ))}
              </div>
            </div>
          </FadeIn>

          {/* Segments */}
          <FadeIn delay={50} duration={12}>
            <div
              style={{
                backgroundColor: COLORS.card,
                borderRadius: 8,
                border: `1px solid ${COLORS.border}`,
                padding: 14,
              }}
            >
              <p style={{ fontSize: 12, fontWeight: 500, color: COLORS.textMuted, margin: "0 0 10px 0" }}>
                Audience Segments
              </p>
              <div
                style={{
                  display: "flex",
                  height: 14,
                  borderRadius: 9999,
                  overflow: "hidden",
                  backgroundColor: COLORS.barBg,
                  width: `${segBarProgress * 100}%`,
                }}
              >
                {SEGMENTS.map((seg) => (
                  <div
                    key={seg.label}
                    style={{
                      width: `${(seg.count / WARMTH_TOTAL) * 100}%`,
                      backgroundColor: seg.color,
                    }}
                  />
                ))}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 8 }}>
                {SEGMENTS.map((seg) => (
                  <div key={seg.label} style={{ display: "flex", justifyContent: "space-between", fontSize: 10 }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 5, color: COLORS.textMuted }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: seg.color, display: "inline-block" }} />
                      {seg.label}
                    </span>
                    <span style={{ color: COLORS.textDim }}>{seg.count} contacts</span>
                  </div>
                ))}
              </div>
            </div>
          </FadeIn>
        </div>

        {/* Top Warmest Contacts */}
        <FadeIn delay={68} duration={12}>
          <div
            style={{
              backgroundColor: COLORS.card,
              borderRadius: 8,
              border: `1px solid ${COLORS.border}`,
              padding: 14,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <p style={{ fontSize: 12, fontWeight: 500, color: COLORS.textMuted, margin: 0 }}>
                Top 10 Warmest Contacts
              </p>
              <span style={{ fontSize: 12, color: COLORS.coolLight }}>View all</span>
            </div>
            {TOP_CONTACTS.map((contact, i) => (
              <FadeIn key={contact.name} delay={75 + i * 4} duration={10}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "6px 0",
                    borderTop: i > 0 ? `1px solid ${COLORS.border}` : "none",
                  }}
                >
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 500, color: COLORS.text, margin: 0 }}>
                      {contact.name}
                    </p>
                    <p style={{ fontSize: 10, color: COLORS.textDim, margin: 0 }}>
                      {contact.company}
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 10, color: COLORS.textDim }}>{contact.msgs} msgs</span>
                    <WarmthBadgeInline score={contact.score} />
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </FadeIn>
      </div>
    </LaptopMockup>
  );
};
