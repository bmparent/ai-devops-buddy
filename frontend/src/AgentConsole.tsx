import React, { useEffect, useState } from 'react';

interface EventItem {
  role: string;
  action: string;
  confidence: number;
  tokens: number;
  elapsed_ms: number;
}

export function AgentConsole({ taskId }: { taskId: string }) {
  const [events, setEvents] = useState<EventItem[]>([]);
  useEffect(() => {
    const evtSource = new EventSource(`/stream/agent/${taskId}`);
    evtSource.onmessage = (e) => {
      const item = JSON.parse(e.data) as EventItem;
      setEvents((prev) => [...prev, item]);
    };
    return () => evtSource.close();
  }, [taskId]);
  return (
    <div>
      <h3>Agent Timeline</h3>
      <ul>
        {events.map((e, i) => (
          <li key={i}>
            {e.role} - {e.action} - conf {e.confidence} - tokens {e.tokens} - {e.elapsed_ms}ms
          </li>
        ))}
      </ul>
    </div>
  );
}
