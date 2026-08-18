export type LlmProviderKind = "cloud" | "local";

export interface LlmModelDescriptor {
  id: string;
  label: string;
  size_bytes: number | null;
  parameter_size: string | null;
  quantization: string | null;
}

export interface LlmProviderDescriptor {
  id: string;
  label: string;
  kind: LlmProviderKind;
  available: boolean;
  reachable: boolean;
  status_message: string;
  models: LlmModelDescriptor[];
}

export interface LlmProviderCatalog {
  providers: LlmProviderDescriptor[];
}

export interface LlmSelection {
  provider: LlmProviderDescriptor;
  model: LlmModelDescriptor;
}
