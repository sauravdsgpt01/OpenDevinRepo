export interface SlashCommand {
  name: string;
  description: string;
  shortcut?: string;
  action: string;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    name: "/clear",
    description: "Clear chat history",
    action: "clear",
  },
  {
    name: "/settings",
    description: "Open settings",
    shortcut: "⌘,",
    action: "settings",
  },
  {
    name: "/model",
    description: "Configure LLM model",
    action: "model",
  },
];

export function filterCommands(query: string): SlashCommand[] {
  if (!query.startsWith("/")) return [];
  const searchTerm = query.toLowerCase();
  return SLASH_COMMANDS.filter((cmd) =>
    cmd.name.toLowerCase().startsWith(searchTerm),
  );
}
