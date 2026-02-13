import React from "react";
import { AbsoluteFill } from "remotion";
import { COLORS, FONTS } from "./theme";

interface LaptopMockupProps {
  children: React.ReactNode;
  url?: string;
  activeNav?: string;
}

const NAV_ITEMS = [
  { label: "Dashboard", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1" },
  { label: "Contacts", icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" },
  { label: "Queue", icon: "M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" },
  { label: "Opportunities", icon: "M13 10V3L4 14h7v7l9-11h-7z" },
  { label: "Target Companies", icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" },
  { label: "Followers", icon: "M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" },
];

export const LaptopMockup: React.FC<LaptopMockupProps> = ({
  children,
  url = "localhost:5173",
  activeNav = "Dashboard",
}) => {
  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: COLORS.bg,
        fontFamily: FONTS.sans,
      }}
    >
      {/* Laptop body */}
      <div
        style={{
          width: 1600,
          height: 920,
          borderRadius: 16,
          backgroundColor: COLORS.card,
          border: `2px solid ${COLORS.border}`,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 80px rgba(0,0,0,0.6)",
        }}
      >
        {/* Browser chrome */}
        <div
          style={{
            height: 44,
            backgroundColor: "#252540",
            display: "flex",
            alignItems: "center",
            padding: "0 16px",
            gap: 8,
            flexShrink: 0,
          }}
        >
          <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#ff5f56" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#ffbd2e" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#27ca40" }} />
          <div
            style={{
              marginLeft: 16,
              flex: 1,
              height: 28,
              borderRadius: 6,
              backgroundColor: COLORS.bg,
              color: COLORS.textDim,
              fontSize: 13,
              display: "flex",
              alignItems: "center",
              paddingLeft: 14,
            }}
          >
            {url}
          </div>
        </div>

        {/* App area: sidebar + content */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {/* Sidebar */}
          <div
            style={{
              width: 220,
              backgroundColor: COLORS.sidebarBg,
              borderRight: `1px solid ${COLORS.border}`,
              display: "flex",
              flexDirection: "column",
              flexShrink: 0,
            }}
          >
            {/* Logo */}
            <div
              style={{
                height: 52,
                display: "flex",
                alignItems: "center",
                padding: "0 20px",
                borderBottom: `1px solid ${COLORS.border}`,
              }}
            >
              <span style={{ fontSize: 16, fontWeight: 700, color: COLORS.white }}>
                LinkedIn Agent
              </span>
            </div>

            {/* Nav items */}
            <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 2 }}>
              {NAV_ITEMS.map((item) => {
                const isActive = item.label === activeNav;
                return (
                  <div
                    key={item.label}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "8px 12px",
                      borderRadius: 8,
                      backgroundColor: isActive ? COLORS.sidebarActive : "transparent",
                      color: isActive ? COLORS.sidebarActiveText : COLORS.sidebarText,
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                  >
                    <svg
                      width={18}
                      height={18}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={1.5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d={item.icon} />
                    </svg>
                    {item.label}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Main content */}
          <div
            style={{
              flex: 1,
              backgroundColor: COLORS.bg,
              padding: 32,
              overflow: "hidden",
              position: "relative",
            }}
          >
            {children}
          </div>
        </div>
      </div>

      {/* Laptop base */}
      <div
        style={{
          width: 1800,
          height: 14,
          backgroundColor: "#252540",
          borderRadius: "0 0 12px 12px",
          marginTop: -2,
        }}
      />
    </AbsoluteFill>
  );
};
