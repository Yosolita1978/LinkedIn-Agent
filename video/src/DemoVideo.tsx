import { AbsoluteFill } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";

import { SceneIntro } from "./scenes/SceneIntro";
import { SceneDashboard } from "./scenes/SceneDashboard";
import { SceneContactDetail } from "./scenes/SceneContactDetail";
import { SceneOpportunities } from "./scenes/SceneOpportunities";
import { SceneAIGeneration } from "./scenes/SceneAIGeneration";
import { SceneOutro } from "./scenes/SceneOutro";

export const DemoVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      <TransitionSeries>
        {/* Scene 1: Intro — 4.0s */}
        <TransitionSeries.Sequence durationInFrames={120}>
          <SceneIntro />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          timing={linearTiming({ durationInFrames: 15 })}
          presentation={fade()}
        />

        {/* Scene 2: Dashboard — 9.0s */}
        <TransitionSeries.Sequence durationInFrames={270}>
          <SceneDashboard />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          timing={linearTiming({ durationInFrames: 15 })}
          presentation={slide({ direction: "from-right" })}
        />

        {/* Scene 3: Contact Detail — 9.0s */}
        <TransitionSeries.Sequence durationInFrames={270}>
          <SceneContactDetail />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          timing={linearTiming({ durationInFrames: 15 })}
          presentation={fade()}
        />

        {/* Scene 4: Opportunities — 6.0s */}
        <TransitionSeries.Sequence durationInFrames={180}>
          <SceneOpportunities />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          timing={linearTiming({ durationInFrames: 15 })}
          presentation={slide({ direction: "from-right" })}
        />

        {/* Scene 5: AI Generation — 7.0s */}
        <TransitionSeries.Sequence durationInFrames={210}>
          <SceneAIGeneration />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          timing={linearTiming({ durationInFrames: 15 })}
          presentation={fade()}
        />

        {/* Scene 6: Outro — 3.5s */}
        <TransitionSeries.Sequence durationInFrames={105}>
          <SceneOutro />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
