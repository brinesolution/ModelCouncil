import { LedStatus } from "@/components/industrial/led-status";
import { PanelDetails } from "@/components/industrial/panel-details";
import type { SimulationConversation } from "@/types/results";

interface ConversationLedgerProps {
  conversations: SimulationConversation[];
}

export function ConversationLedger({ conversations }: ConversationLedgerProps) {
  return (
    <section className="resultSection conversationSection" aria-labelledby="conversation-title">
      <PanelDetails />
      <div className="conversationSectionHeader">
        <div>
          <span className="techLabel">Communication log / ranked interactions</span>
          <h2 id="conversation-title">Conversation replay</h2>
          <p>
            Language is rendered from already-computed semantic interactions. Transcript wording never overwrites numerical opinion state.
          </p>
        </div>
        <span className="mono conversationCount">{conversations.length} SHOWN</span>
      </div>

      <div className="conversationList">
        {conversations.length ? (
          conversations.map((conversation) => {
            const live = conversation.language_source !== "background";
            return (
              <article className="conversationCard" key={conversation.conversation_id}>
                <div className="conversationMeta">
                  <div className="conversationMetaTopline">
                    <span className="techLabel">ROUND {conversation.round}</span>
                    <LedStatus
                      label={live ? "DeepSeek" : "Deterministic"}
                      tone={live ? "red" : "green"}
                      compact
                    />
                  </div>
                  <strong>
                    Agent {conversation.agent_a_id} ↔ Agent {conversation.agent_b_id}
                  </strong>
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
                </div>

                <div className="chatThread">
                  {conversation.transcript.map((message, index) => {
                    const isAgentA = message.speaker_id === conversation.agent_a_id;
                    return (
                      <div
                        className={`chatMessage ${isAgentA ? "chatMessageA" : "chatMessageB"}`}
                        key={`${conversation.conversation_id}-${message.speaker_id}-${index}`}
                      >
                        <span className="chatSpeaker">AGENT {message.speaker_id}</span>
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
