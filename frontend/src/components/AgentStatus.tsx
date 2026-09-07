import type { AgentStatus } from "../api";

const STATUS_CONFIG: Record<
  AgentStatus,
  { label: string; color: string; pulse?: boolean }
> = {
  thinking: { label: "Thinking…", color: "var(--accent)", pulse: true },
  tool_call: { label: "Calling tool…", color: "var(--warning)", pulse: true },
  waiting_for_human: {
    label: "Waiting for human approval",
    color: "var(--warning)",
    pulse: true,
  },
  completed: { label: "Done", color: "var(--success)" },
  error: { label: "Error", color: "var(--error)" },
};

interface Props {
  status: AgentStatus;
  intent?: string;
}

export default function AgentStatus({ status, intent }: Props) {
  const cfg = STATUS_CONFIG[status];

  return (
    <div className="agent-status">
      <span
        className={`status-dot${cfg.pulse ? " pulse" : ""}`}
        style={{ background: cfg.color }}
      />
      <span className="status-label">{cfg.label}</span>
      {intent && <span className="status-intent">intent: {intent}</span>}
    </div>
  );
}
