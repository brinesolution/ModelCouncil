"use client";

import { useState } from "react";

import { LedStatus } from "@/components/industrial/led-status";
import { PanelDetails } from "@/components/industrial/panel-details";
import type {
  SimulationAgentProfile,
  SimulationAgentTraits,
  SimulationConversation,
} from "@/types/results";

interface ConversationLedgerProps {
  conversations: SimulationConversation[];
}

const TRAIT_LABELS: ReadonlyArray<[keyof SimulationAgentTraits, string]> = [
  ["sociability", "Sociability"],
  ["price_sensitivity", "Price sensitivity"],
  ["technology_adoption", "Technology adoption"],
  ["emotionality", "Emotionality"],
  ["logicality", "Logicality"],
  ["stubbornness", "Stubbornness"],
  ["influence_power", "Influence power"],
  ["product_need", "Generic product motivation"],
  ["risk_tolerance", "Risk tolerance"],
  ["brand_loyalty", "Brand loyalty"],
];

function percent01(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function readableKey(value: string): string {
  if (!value || value === "unspecified") return "Unspecified";
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

interface AgentProfileButtonProps {
  profile: SimulationAgentProfile;
  profileKey: string;
  openProfileKey: string | null;
  onToggle: (profileKey: string) => void;
  compact?: boolean;
}

function AgentProfileButton({
  profile,
  profileKey,
  openProfileKey,
  onToggle,
  compact = false,
}: AgentProfileButtonProps) {
  const expanded = openProfileKey === profileKey;
  return (
    <button
      type="button"
      className={`agentProfileTrigger ${compact ? "agentProfileTriggerCompact" : ""}`}
      onClick={() => onToggle(profileKey)}
      aria-expanded={expanded}
      title={`View Agent ${profile.agent_id} traits`}
    >
      Agent {profile.agent_id}
    </button>
  );
}

interface AgentProfilePanelProps {
  profile: SimulationAgentProfile;
  panelId: string;
  onClose: () => void;
}

function AgentProfilePanel({ profile, panelId, onClose }: AgentProfilePanelProps) {
  return (
    <div className="agentProfilePanel" id={panelId}>
      <div className="agentProfilePanelHeader">
        <div>
          <span className="techLabel">Synthetic agent profile</span>
          <strong>Agent {profile.agent_id}</strong>
        </div>
        <button type="button" className="agentProfileClose" onClick={onClose} aria-label={`Close Agent ${profile.agent_id} profile`}>
          ×
        </button>
      </div>

      <div className="agentIdentityGrid">
        <div><span>Age</span><strong>{profile.age}</strong></div>
        <div><span>Occupation</span><strong>{profile.occupation}</strong></div>
        <div><span>Income score</span><strong>{percent01(profile.income_score)}</strong></div>
        <div><span>Archetype</span><strong>{readableKey(profile.archetype_key)}</strong></div>
        <div><span>Demographic</span><strong>{readableKey(profile.demographic_key)}</strong></div>
        <div><span>Occupation model</span><strong>{readableKey(profile.occupation_key)}</strong></div>
        <div><span>Language</span><strong>{profile.primary_language}</strong></div>
        <div><span>Locale</span><strong>{profile.locale}</strong></div>
      </div>

      <div className="agentTraitHeader">
        <span>Stable / slow synthetic traits</span>
        <small>Normalized 0–100 display</small>
      </div>
      <div className="agentTraitGrid">
        {TRAIT_LABELS.map(([key, label]) => (
          <div className="agentTrait" key={key}>
            <span>{label}</span>
            <strong>{percent01(profile.traits[key])}</strong>
            <i aria-hidden="true"><b style={{ width: percent01(profile.traits[key]) }} /></i>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ConversationLedger({ conversations }: ConversationLedgerProps) {
  const [openProfileKey, setOpenProfileKey] = useState<string | null>(null);

  function toggleProfile(profileKey: string) {
    setOpenProfileKey((current) => current === profileKey ? null : profileKey);
  }

  return (
    <section className="resultSection conversationSection" aria-labelledby="conversation-title">
      <PanelDetails />
      <div className="conversationSectionHeader">
        <div>
          <span className="techLabel">Communication log / ranked interactions</span>
          <h2 id="conversation-title">Conversation replay</h2>
          <p>
            Language is rendered from already-computed semantic interactions. Click any agent name to inspect the synthetic traits behind that participant; transcript wording never overwrites numerical opinion state.
          </p>
        </div>
        <span className="mono conversationCount">{conversations.length} SHOWN</span>
      </div>

      <div className="conversationList">
        {conversations.length ? (
          conversations.map((conversation) => {
            const live = conversation.language_source !== "background";
            const profileKeyA = `${conversation.conversation_id}:${conversation.agent_a_id}`;
            const profileKeyB = `${conversation.conversation_id}:${conversation.agent_b_id}`;
            const selectedProfile = openProfileKey === profileKeyA
              ? conversation.agent_a_profile
              : openProfileKey === profileKeyB
                ? conversation.agent_b_profile
                : null;
            const panelId = `agent-profile-${conversation.conversation_id}`;

            return (
              <article className="conversationCard" key={conversation.conversation_id}>
                <div className="conversationMeta">
                  <div className="conversationMetaTopline">
                    <span className="techLabel">ROUND {conversation.round}</span>
                    <LedStatus
                      label={live ? "Model rendered" : "Deterministic"}
                      tone={live ? "red" : "green"}
                      compact
                    />
                  </div>
                  <div className="conversationAgents" aria-controls={selectedProfile ? panelId : undefined}>
                    <AgentProfileButton
                      profile={conversation.agent_a_profile}
                      profileKey={profileKeyA}
                      openProfileKey={openProfileKey}
                      onToggle={toggleProfile}
                    />
                    <span aria-hidden="true">↔</span>
                    <AgentProfileButton
                      profile={conversation.agent_b_profile}
                      profileKey={profileKeyB}
                      openProfileKey={openProfileKey}
                      onToggle={toggleProfile}
                    />
                  </div>
                  <span className="conversationTopics">
                    {conversation.topics.join(" / ") || "general product discussion"}
                  </span>
                  <div className="conversationSignalRow">
                    <span className={`conversationSource ${live ? "conversationSourceLive" : ""}`}>
                      {live ? "Live language" : "Background language"}
                    </span>
                    <span className="mono">IMP {Math.round(conversation.importance * 100)}%</span>
                    <span className="mono">{conversation.llm_selected ? "LLM SELECTED" : "SEMANTIC ONLY"}</span>
                  </div>

                  {selectedProfile ? (
                    <AgentProfilePanel
                      profile={selectedProfile}
                      panelId={panelId}
                      onClose={() => setOpenProfileKey(null)}
                    />
                  ) : null}
                </div>

                <div className="chatThread">
                  {conversation.transcript.map((message, index) => {
                    const isAgentA = message.speaker_id === conversation.agent_a_id;
                    const profile = isAgentA ? conversation.agent_a_profile : conversation.agent_b_profile;
                    const profileKey = isAgentA ? profileKeyA : profileKeyB;
                    return (
                      <div
                        className={`chatMessage ${isAgentA ? "chatMessageA" : "chatMessageB"}`}
                        key={`${conversation.conversation_id}-${message.speaker_id}-${index}`}
                      >
                        <AgentProfileButton
                          profile={profile}
                          profileKey={profileKey}
                          openProfileKey={openProfileKey}
                          onToggle={toggleProfile}
                          compact
                        />
                        <p>{message.text}</p>
                      </div>
                    );
                  })}
                </div>
              </article>
            );
          })
        ) : (
          <p className="emptyLog">No conversations were scheduled in this run.</p>
        )}
      </div>
    </section>
  );
}
