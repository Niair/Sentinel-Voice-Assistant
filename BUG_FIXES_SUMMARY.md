# Sentinal Voice Assistant - Project File Structure

```
Sentinal-Voice-Assistant/
├── .git/
├── _assets/
│   └── old_code/
│       ├── langraph_rag_backend.py
│       └── streamlity_rag_frontend.py
├── backend/
│   ├── app/
│   │   ├── database.py
│   │   ├── events.py
│   │   ├── graph.py
│   │   ├── main.py
│   │   ├── mcp.py
│   │   ├── models.py
│   │   └── qdrant_manager.py
│   ├── tests/
│   │   ├── test_database_connection.py
│   │   ├── test_event_bus.py
│   │   └── test_qdrant_comprehensive.py
│   ├── uploads/
│   ├── local_mcp/
│   │   └── test_server.py
│   ├── .venv/
│   └── init_monitoring_db.py
├── frontend/
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── auth.ts
│   │   ├── (chat)/
│   │   │   ├── actions.ts
│   │   │   └── chat/[id]/page.tsx
│   │   ├── api/
│   │   │   ├── chat/route.ts
│   │   │   ├── files/upload/route.ts
│   │   │   ├── history/rename/route.ts
│   │   │   └── history/route.ts
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── artifacts/
│   │   ├── actions.ts
│   │   ├── code/client.tsx
│   │   ├── code/server.ts
│   │   ├── image/client.tsx
│   │   ├── sheet/client.tsx
│   │   ├── sheet/server.ts
│   │   ├── text/client.tsx
│   │   └── text/server.ts
│   ├── components/
│   │   ├── ai-elements/
│   │   │   ├── artifact.tsx
│   │   │   ├── canvas.tsx
│   │   │   ├── chain-of-thought.tsx
│   │   │   ├── checkpoint.tsx
│   │   │   ├── confirmation.tsx
│   │   │   ├── connection.tsx
│   │   │   ├── controls.tsx
│   │   │   ├── conversation.tsx
│   │   │   ├── edge.tsx
│   │   │   ├── image.tsx
│   │   │   ├── inline-citation.tsx
│   │   │   ├── loader.tsx
│   │   │   ├── message.tsx
│   │   │   ├── model-selector.tsx
│   │   │   ├── node.tsx
│   │   │   ├── open-in-chat.tsx
│   │   │   ├── panel.tsx
│   │   │   ├── plan.tsx
│   │   │   ├── prompt-input.tsx
│   │   │   ├── queue.tsx
│   │   │   ├── reasoning.tsx
│   │   │   ├── shimmer.tsx
│   │   │   ├── sources.tsx
│   │   │   ├── suggestion.tsx
│   │   │   ├── task.tsx
│   │   │   ├── tool.tsx
│   │   │   ├── toolbar.tsx
│   │   │   └── web-preview.tsx
│   │   ├── elements/
│   │   │   ├── actions.tsx
│   │   │   ├── branch.tsx
│   │   │   ├── conversation.tsx
│   │   │   ├── image.tsx
│   │   │   ├── inline-citation.tsx
│   │   │   ├── loader.tsx
│   │   │   ├── message.tsx
│   │   │   ├── prompt-input.tsx
│   │   │   ├── reasoning.tsx
│   │   │   ├── response.tsx
│   │   │   ├── source.tsx
│   │   │   ├── suggestion.tsx
│   │   │   ├── task.tsx
│   │   │   ├── tool.tsx
│   │   │   └── web-preview.tsx
│   │   ├── ui/
│   │   │   ├── alert.tsx
│   │   │   ├── alert-dialog.tsx
│   │   │   ├── avatar.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── button.tsx
│   │   │   ├── button-group.tsx
│   │   │   ├── card.tsx
│   │   │   ├── carousel.tsx
│   │   │   ├── collapsible.tsx
│   │   │   ├── command.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── hover-card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── input-group.tsx
│   │   │   ├── label.tsx
│   │   │   ├── progress.tsx
│   │   │   ├── scroll-area.tsx
│   │   │   ├── select.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── sheet.tsx
│   │   │   ├── sidebar.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── textarea.tsx
│   │   │   └── tooltip.tsx
│   │   ├── app-sidebar.tsx
│   │   ├── artifact.tsx
│   │   ├── artifact-actions.tsx
│   │   ├── artifact-close-button.tsx
│   │   ├── artifact-messages.tsx
│   │   ├── auth-form.tsx
│   │   ├── chat.tsx
│   │   ├── chat-header.tsx
│   │   ├── code-editor.tsx
│   │   ├── console.tsx
│   │   ├── create-artifact.tsx
│   │   ├── data-stream-handler.tsx
│   │   ├── data-stream-provider.tsx
│   │   ├── diffview.tsx
│   │   ├── document.tsx
│   │   ├── document-preview.tsx
│   │   ├── document-skeleton.tsx
│   │   ├── greeting.tsx
│   │   ├── icons.tsx
│   │   ├── image-editor.tsx
│   │   ├── message.tsx
│   │   ├── message-actions.tsx
│   │   ├── message-editor.tsx
│   │   ├── message-reasoning.tsx
│   │   ├── messages.tsx
│   │   ├── multimodal-input.tsx
│   │   ├── preview-attachment.tsx
│   │   ├── sheet-editor.tsx
│   │   ├── sidebar-history.tsx
│   │   ├── sidebar-history-item.tsx
│   │   ├── sidebar-toggle.tsx
│   │   ├── sidebar-user-nav.tsx
│   │   ├── sign-out-form.tsx
│   │   ├── submit-button.tsx
│   │   ├── suggested-actions.tsx
│   │   ├── suggestion.tsx
│   │   ├── text-editor.tsx
│   │   ├── theme-provider.tsx
│   │   ├── toast.tsx
│   │   ├── toolbar.tsx
│   │   ├── version-footer.tsx
│   │   ├── visibility-selector.tsx
│   │   └── weather.tsx
│   ├── hooks/
│   │   ├── use-artifact.ts
│   │   ├── use-auto-resume.ts
│   │   ├── use-block.ts
│   │   ├── use-chat-visibility.ts
│   │   ├── use-messages.ts
│   │   └── use-mobile.ts
│   ├── lib/
│   │   ├── ai/
│   │   │   ├── entitlements.ts
│   │   │   ├── models.mock.ts
│   │   │   ├── models.test.ts
│   │   │   ├── models.ts
│   │   │   ├── prompts.ts
│   │   │   ├── providers.ts
│   │   │   └── tools/
│   │   │       ├── create-document.ts
│   │   │       ├── get-weather.ts
│   │   │       ├── request-suggestions.ts
│   │   │       └── update-document.ts
│   │   ├── artifacts/
│   │   │   └── server.ts
│   │   ├── db/
│   │   │   ├── helpers/01-core-to-parts.ts
│   │   │   ├── migrate.ts
│   │   │   ├── queries.ts
│   │   │   ├── schema.ts
│   │   │   └── utils.ts
│   │   ├── editor/
│   │   │   ├── config.ts
│   │   │   ├── diff.js
│   │   │   ├── functions.tsx
│   │   │   ├── react-renderer.tsx
│   │   │   └── suggestions.tsx
│   │   ├── artifacts/server.ts
│   │   ├── constants.ts
│   │   ├── errors.ts
│   │   ├── types.ts
│   │   └── utils.ts
│   ├── .next/
│   ├── drizzle.config.ts
│   ├── next-env.d.ts
│   ├── postcss.config.js
│   ├── test-backend.js
│   └── test-db.js
├── abc.md
├── body.json
├── BUG_FIXES_SUMMARY.md
├── docker-compose.yml
├── env_example.txt
├── filelist.txt
├── implementation_plan.md
├── LICENSE
└── README.md
```

## Directory Overview

### Backend (`/backend`)
- **app/** - Core application logic including database, events, graph, MCP integration, and Qdrant vector store
- **tests/** - Unit tests for database, event bus, and Qdrant functionality
- **local_mcp/** - Local MCP server implementation
- **uploads/** - File upload directory

### Frontend (`/frontend`)
- **app/** - Next.js app router with API routes and pages
- **artifacts/** - Artifact components (code, image, sheet, text)
- **components/** - React components organized by category (ai-elements, elements, ui)
- **hooks/** - Custom React hooks
- **lib/** - Utilities, AI integration, database queries, editor configuration

### Root
- Configuration files (docker-compose, env_example)
- Documentation (README.md, implementation_plan.md)
- Old code in `_assets/` directory
