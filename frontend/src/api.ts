// Keep provider copy consistent with the UI, including older running servers.
function displayMessage(message: string) {
  return message
    .replace(/\b(?:Jev\s*\/\s*)?TypeSafe(?:\s+AI)?\b/gi, "jev")
    .replace(/\bJev\b/g, "jev");
}

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch(`/api/${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(
      typeof e.detail === "string"
        ? displayMessage(e.detail)
        : "Please check the fields and try again.",
    );
  }
  return r.json();
}
export async function stream(
  path: string,
  body: unknown,
  onEvent: (event: any) => void,
  signal: AbortSignal,
) {
  const r = await fetch(`/api/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(
      typeof e.detail === "string"
        ? displayMessage(e.detail)
        : "The request could not start. Check the input and try again.",
    );
  }
  const reader = r.body!.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  let completed = false;
  while (true) {
    const { done, value } = await reader.read();
    pending += decoder.decode(value, { stream: !done });
    const lines = pending.split("\n");
    pending = lines.pop() || "";
    for (const line of lines)
      if (line.trim()) {
        const event = JSON.parse(line);
        if (typeof event.message === "string")
          event.message = displayMessage(event.message);
        if (event.type === "error") throw new Error(event.message);
        if (event.type === "complete") completed = true;
        onEvent(event);
      }
    if (done) break;
  }
  if (!completed)
    throw new Error(
      "The connection ended before completion. Please run again.",
    );
}
