// Embeds the n8n-style forecast pipeline diagram and feeds it live agent status.
import { useEffect, useRef } from "react";
import { api } from "../api/client";
import type { PipelineStatus } from "../types";

export default function PipelinePage() {
  const frameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    let cancelled = false;
    const push = async () => {
      try {
        const status = await api.get<PipelineStatus>("/api/v1/pipeline/status");
        if (cancelled) return;
        frameRef.current?.contentWindow?.postMessage(
          {
            type: "penumbra:pipeline",
            agents: status.agents.map((a) => ({
              id: a.id,
              status: a.status,
              detail: a.status === "ok" && a.items ? `ok · ${a.items} items` : a.status,
            })),
          },
          "*",
        );
      } catch {
        /* backend offline — diagram falls back to standalone animation */
      }
    };
    const id = setInterval(push, 5000);
    const t = setTimeout(push, 1200);
    return () => {
      cancelled = true;
      clearInterval(id);
      clearTimeout(t);
    };
  }, []);

  return (
    <div className="pipeline-page">
      <iframe
        ref={frameRef}
        className="pipeline-frame"
        src="/diagrams/pipeline-flow.html"
        title="PENUMBRA forecast pipeline"
      />
    </div>
  );
}
