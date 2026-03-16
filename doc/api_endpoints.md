# API endpoints

This doc explains the HTTP endpoints, what they do, and how they read or write the SQLite tables.

## Endpoint summary

| Method | Path | Purpose |
| --- | --- | --- |
| GET | / | Serve the UI shell |
| GET | /api/sessions | List recent sessions |
| POST | /api/sessions | Create a new session |
| GET | /api/sessions/{session_id} | Fetch one session with derived fields |
| DELETE | /api/sessions/{session_id} | Delete a session and its config |
| POST | /api/sessions/{session_id}/input | Save title and raw script input |
| POST | /api/sessions/{session_id}/regeneration | Save regeneration prompt |
| POST | /api/sessions/{session_id}/config | Save per-session config |
| GET | /api/sessions/{session_id}/stream?mode=analyze|regenerate | Start analysis and stream SSE events |

## DB interaction map

Arrows show which columns each endpoint writes. Reads are listed separately.

| Endpoint | Reads | Writes |
| --- | --- | --- |
| POST /api/sessions | - | sessions.session_id <- new uuid<br>sessions.title <- payload.title<br>sessions.status <- "idle"<br>sessions.created_at <- now<br>sessions.updated_at <- now |
| GET /api/sessions | sessions.session_id, title, raw_text, status, updated_at | - |
| POST /api/sessions/{id}/input | sessions.session_id | sessions.title <- payload.title<br>sessions.raw_text <- payload.raw_text<br>sessions.updated_at <- now |
| POST /api/sessions/{id}/regeneration | sessions.session_id | sessions.regeneration_prompt <- payload.regeneration_prompt<br>sessions.updated_at <- now |
| POST /api/sessions/{id}/config | sessions.session_id | session_config.session_id <- {id}<br>session_config.config_json <- sanitized config<br>session_config.updated_at <- now |
| GET /api/sessions/{id} | sessions.*<br>session_config.config_json<br>sessions.last_token_usage_json | - |
| DELETE /api/sessions/{id} | sessions.session_id | sessions row deleted<br>session_config row deleted |
| GET /api/sessions/{id}/stream?mode=analyze | sessions.raw_text, title<br>session_config.config_json | sessions.status <- "running"<br>sessions.last_*_json <- result payloads<br>sessions.iterations <- result.iterations<br>sessions.tokens_used <- result.tokens_used<br>sessions.last_error <- null<br>sessions.updated_at <- now |
| GET /api/sessions/{id}/stream?mode=regenerate | sessions.raw_text, title<br>sessions.regeneration_prompt<br>sessions.last_report_json<br>session_config.config_json | sessions.status <- "running"<br>sessions.last_*_json <- result payloads<br>sessions.iterations <- result.iterations<br>sessions.tokens_used <- result.tokens_used<br>sessions.last_error <- null<br>sessions.updated_at <- now |
| GET /api/sessions/{id}/stream (error path) | sessions.raw_text, title<br>session_config.config_json | sessions.status <- "error"<br>sessions.last_error <- error message<br>sessions.updated_at <- now |

Notes:

- sessions.last_*_json stands for last_report_json, last_validation_json, last_engagement_json, last_beat_json, last_emotion_json, last_improvement_json, last_token_usage_json.
- The stream endpoint both starts the run and streams updates. There is no separate start endpoint.

## Run and regeneration flow

### Analyze run

1. POST /api/sessions to create a session.
2. POST /api/sessions/{id}/input to save title and raw text.
3. POST /api/sessions/{id}/config to save model and runtime options.
4. GET /api/sessions/{id}/stream?mode=analyze
   - Starts the analysis worker thread.
   - Streams SSE events: progress, result, error, done.

### Regeneration run

1. POST /api/sessions/{id}/regeneration to save validator guidance.
2. GET /api/sessions/{id}/stream?mode=regenerate
   - Loads the previous report and regeneration prompt.
   - Runs the same pipeline with extra context.
   - Streams SSE events: progress, result, error, done.

## SSE events

The stream endpoint returns text/event-stream with these event types:

- progress: stage updates with iteration and status
- result: final payload with report and stage outputs
- error: error message
- done: terminal event signalling the stream is complete

Payloads are JSON strings in the SSE data field.

## Config JSON fields

Stored in session_config.config_json:

- model
- temperature
- max_iterations
