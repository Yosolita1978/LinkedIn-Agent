import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { COLORS, FONTS } from "../components/theme";
import { LaptopMockup } from "../components/LaptopMockup";
import { FadeIn } from "../components/FadeIn";
import { CursorClick } from "../components/CursorClick";

const TABS = ["All", "Dormant", "Promise Made", "Unanswered", "They Waiting"];

const OPPORTUNITIES = [
  {
    name: "Carlos Vega",
    company: "Stripe",
    hookType: "dormant",
    score: 62,
    detail: "Last conversation 4 months ago about API integration project",
  },
  {
    name: "Lisa Chang",
    company: "Shopify",
    hookType: "promise made",
    score: 55,
    detail: "You mentioned meeting for coffee when visiting Toronto",
  },
  {
    name: "Ahmed Hassan",
    company: "Datadog",
    hookType: "they waiting",
    score: 48,
    detail: "They asked about your experience with monitoring tools",
  },
];

function WarmthBadgeSmall({ score }: { score: number }) {
  const bg = score >= 70 ? COLORS.hotBg : score >= 40 ? COLORS.warmBg : COLORS.coolBg;
  const color = score >= 70 ? COLORS.hotLight : score >= 40 ? COLORS.warmLight : COLORS.coolLight;
  return (
    <span
      style={{
        padding: "2px 6px",
        borderRadius: 9999,
        fontSize: 10,
        fontWeight: 600,
        backgroundColor: bg,
        color,
      }}
    >
      {score}
    </span>
  );
}

export const SceneOpportunities: React.FC = () => {
  const frame = useCurrentFrame();

  // Tab switch at frame 55
  const activeTabIndex = frame >= 55 ? 1 : 0;

  // Cursor click on "Generate & Queue" button at frame 130
  const showCursor = frame >= 110;

  return (
    <LaptopMockup activeNav="Opportunities" url="localhost:5173/opportunities">
      <div style={{ fontFamily: FONTS.sans, position: "relative" }}>
        {/* Title */}
        <FadeIn delay={0} duration={10}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: COLORS.white, margin: "0 0 16px 0" }}>
            Opportunities
          </h1>
        </FadeIn>

        {/* Tabs */}
        <FadeIn delay={5} duration={10}>
          <div
            style={{
              display: "flex",
              gap: 2,
              backgroundColor: COLORS.card,
              borderRadius: 8,
              padding: 4,
              border: `1px solid ${COLORS.border}`,
              width: "fit-content",
              marginBottom: 12,
            }}
          >
            {TABS.map((tab, i) => {
              const isActive = i === activeTabIndex;
              return (
                <div
                  key={tab}
                  style={{
                    padding: "6px 12px",
                    fontSize: 12,
                    fontWeight: 500,
                    borderRadius: 6,
                    backgroundColor: isActive ? COLORS.border : "transparent",
                    color: isActive ? COLORS.white : COLORS.textDim,
                    transition: "all 0.2s",
                  }}
                >
                  {tab}
                </div>
              );
            })}
          </div>
        </FadeIn>

        {/* Count */}
        <FadeIn delay={12} duration={8}>
          <p style={{ fontSize: 10, color: COLORS.textDim, margin: "0 0 12px 0" }}>
            24 opportunity(ies)
          </p>
        </FadeIn>

        {/* Opportunity Cards */}
        {OPPORTUNITIES.map((opp, i) => (
          <FadeIn key={opp.name} delay={15 + i * 12} duration={12}>
            <div
              style={{
                backgroundColor: COLORS.card,
                borderRadius: 8,
                border: `1px solid ${COLORS.border}`,
                padding: 14,
                marginBottom: 10,
              }}
            >
              {/* Header row */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 500, color: COLORS.coolLight, margin: 0 }}>
                    {opp.name}
                  </p>
                  <p style={{ fontSize: 10, color: COLORS.textDim, margin: "2px 0 0 0" }}>
                    {opp.company}
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 500,
                      padding: "2px 8px",
                      borderRadius: 9999,
                      backgroundColor: COLORS.amberBg,
                      color: COLORS.amberLight,
                      textTransform: "capitalize",
                    }}
                  >
                    {opp.hookType}
                  </span>
                  <WarmthBadgeSmall score={opp.score} />
                </div>
              </div>

              {/* Hook detail */}
              <p
                style={{
                  fontSize: 12,
                  color: COLORS.text,
                  margin: "8px 0 0 0",
                  padding: 8,
                  backgroundColor: "rgba(51,65,85,0.5)",
                  borderRadius: 6,
                  lineHeight: 1.4,
                }}
              >
                {opp.detail}
              </p>

              {/* Action buttons */}
              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <span
                  style={{
                    padding: "5px 10px",
                    fontSize: 11,
                    border: `1px solid ${COLORS.border}`,
                    color: COLORS.text,
                    borderRadius: 8,
                  }}
                >
                  View Contact
                </span>
                <span
                  style={{
                    padding: "5px 10px",
                    fontSize: 11,
                    backgroundColor: COLORS.blue,
                    color: COLORS.white,
                    borderRadius: 8,
                    fontWeight: 500,
                  }}
                >
                  Generate & Queue
                </span>
                <span
                  style={{
                    padding: "5px 10px",
                    fontSize: 11,
                    border: `1px solid ${COLORS.border}`,
                    color: COLORS.textDim,
                    borderRadius: 8,
                  }}
                >
                  Dismiss
                </span>
              </div>
            </div>
          </FadeIn>
        ))}

        {/* Cursor clicks on the "Dormant" tab, then on "Generate & Queue" */}
        <CursorClick
          startX={800}
          startY={400}
          endX={335}
          endY={72}
          moveStartFrame={42}
          clickFrame={52}
        />

        {showCursor && (
          <CursorClick
            startX={335}
            startY={72}
            endX={390}
            endY={314}
            moveStartFrame={110}
            clickFrame={128}
          />
        )}
      </div>
    </LaptopMockup>
  );
};
