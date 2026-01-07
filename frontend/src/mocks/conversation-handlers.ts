import { http, delay, HttpResponse } from "msw";
import { Conversation, ResultSet } from "#/api/open-hands.types";

// Generate 50 mock conversations for testing pagination
const generateMockConversations = (): Conversation[] => {
  const conversations: Conversation[] = [];
  const projectNames = [
    "API Gateway",
    "User Dashboard",
    "Payment Service",
    "Auth Module",
    "Data Pipeline",
    "ML Model Training",
    "Frontend Redesign",
    "Database Migration",
    "CI/CD Setup",
    "Security Audit",
    "Performance Optimization",
    "Bug Fixes",
    "Feature Development",
    "Code Review",
    "Documentation",
    "Testing Suite",
    "Deployment Script",
    "Monitoring Setup",
    "Logging Service",
    "Cache Layer",
  ];
  const repos = [
    "octocat/hello-world",
    "octocat/earth",
    "myorg/backend",
    "myorg/frontend",
    "myorg/shared-libs",
    null,
  ];
  const statuses: Array<"RUNNING" | "STOPPED"> = ["RUNNING", "STOPPED"];

  for (let i = 1; i <= 50; i += 1) {
    const daysAgo = Math.floor(Math.random() * 30);
    const date = new Date(Date.now() - daysAgo * 24 * 60 * 60 * 1000);
    const isRunning = i <= 3 && Math.random() > 0.5;

    conversations.push({
      conversation_id: i.toString(),
      title: `${projectNames[i % projectNames.length]} #${i}`,
      selected_repository: repos[i % repos.length],
      git_provider: repos[i % repos.length] ? "github" : null,
      selected_branch: repos[i % repos.length] ? "main" : null,
      last_updated_at: date.toISOString(),
      created_at: date.toISOString(),
      status: isRunning ? "RUNNING" : statuses[i % 2],
      runtime_status: isRunning ? "STATUS$READY" : null,
      url: null,
      session_api_key: null,
    });
  }

  // Sort by last_updated_at descending (most recent first)
  return conversations.sort(
    (a, b) =>
      new Date(b.last_updated_at).getTime() -
      new Date(a.last_updated_at).getTime(),
  );
};

const conversations = generateMockConversations();

const CONVERSATIONS = new Map<string, Conversation>(
  conversations.map((c) => [c.conversation_id, c]),
);

// Keep a sorted array for pagination
const SORTED_CONVERSATIONS = conversations;

export const CONVERSATION_HANDLERS = [
  http.get("/api/conversations", async ({ request }) => {
    const url = new URL(request.url);
    const pageId = url.searchParams.get("page_id");
    const limit = parseInt(url.searchParams.get("limit") || "20", 10);

    // Find the starting index based on page_id
    let startIndex = 0;
    if (pageId) {
      const pageIndex = SORTED_CONVERSATIONS.findIndex(
        (c) => c.conversation_id === pageId,
      );
      if (pageIndex !== -1) {
        startIndex = pageIndex;
      }
    }

    // Get the page of results
    const pageResults = SORTED_CONVERSATIONS.slice(
      startIndex,
      startIndex + limit,
    );

    // Determine next_page_id
    const nextIndex = startIndex + limit;
    const nextPageId =
      nextIndex < SORTED_CONVERSATIONS.length
        ? SORTED_CONVERSATIONS[nextIndex].conversation_id
        : null;

    const results: ResultSet<Conversation> = {
      results: pageResults,
      next_page_id: nextPageId,
    };

    // Add a small delay to simulate network latency
    await delay(200);

    return HttpResponse.json(results);
  }),

  http.get("/api/conversations/:conversationId", async ({ params }) => {
    const conversationId = params.conversationId as string;
    const project = CONVERSATIONS.get(conversationId);
    if (project) return HttpResponse.json(project);
    return HttpResponse.json(null, { status: 404 });
  }),

  http.post("/api/conversations", async () => {
    await delay();
    const conversation: Conversation = {
      conversation_id: (Math.random() * 100).toString(),
      title: "New Conversation",
      selected_repository: null,
      git_provider: null,
      selected_branch: null,
      last_updated_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      status: "RUNNING",
      runtime_status: "STATUS$READY",
      url: null,
      session_api_key: null,
    };
    CONVERSATIONS.set(conversation.conversation_id, conversation);
    return HttpResponse.json(conversation, { status: 201 });
  }),

  http.patch(
    "/api/conversations/:conversationId",
    async ({ params, request }) => {
      const conversationId = params.conversationId as string;
      const conversation = CONVERSATIONS.get(conversationId);

      if (conversation) {
        const body = await request.json();
        if (typeof body === "object" && body?.title) {
          CONVERSATIONS.set(conversationId, {
            ...conversation,
            title: body.title,
          });
          return HttpResponse.json(null, { status: 200 });
        }
      }
      return HttpResponse.json(null, { status: 404 });
    },
  ),

  http.delete("/api/conversations/:conversationId", async ({ params }) => {
    const conversationId = params.conversationId as string;
    if (CONVERSATIONS.has(conversationId)) {
      CONVERSATIONS.delete(conversationId);
      return HttpResponse.json(null, { status: 200 });
    }
    return HttpResponse.json(null, { status: 404 });
  }),
];
