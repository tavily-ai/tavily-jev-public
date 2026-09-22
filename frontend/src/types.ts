export type Verdict = "Alert" | "Watch" | "Ignore";
export type Priority = {
  id: string;
  label: string;
  detail: string;
  importance: "high" | "watch" | "off";
};
export type Company = {
  name: string;
  description: string;
  audience: string;
  priorities: Priority[];
  competitors: { name: string; domain?: string }[];
};
export type Decision = {
  verdict: Verdict;
  confidence: number | null;
  probabilities: Record<string, number>;
  provider: string;
  model?: string;
  latency_ms?: number | null;
};
export type Source = {
  id: string;
  title: string;
  domain: string;
  competitor?: string;
  kind?: string;
  content: string;
  url?: string | null;
  evaluation_error?: string;
  published_date?: string;
  source_type?: string;
  decision?: Decision;
  verdict?: string;
  confidence?: number | null;
  quote?: string;
};
export type Config = {
  company: Company;
  connected: { tavily: boolean; jev: boolean };
};
