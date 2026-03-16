# Database schema

This doc lists the SQLite tables used by ScriptAnalysis and the columns in each table.

## Location

- File: .tmp/scriptanalysis.db
- Engine: SQLite
- Timestamps: UTC ISO 8601 strings with a trailing Z

## Table: sessions

Stores the current state and latest run outputs for a session.

| Column | Type | Notes |
| --- | --- | --- |
| session_id | TEXT | Primary key; UUID hex string |
| title | TEXT | Optional title from the UI |
| raw_text | TEXT | Original script or input text |
| status | TEXT | idle, running, complete, review, error |
| regeneration_prompt | TEXT | Optional validator guidance for reruns |
| last_report_json | TEXT | JSON string of final report |
| last_validation_json | TEXT | JSON string of validator output |
| last_engagement_json | TEXT | JSON string of engagement analysis |
| last_beat_json | TEXT | JSON string of beat extraction |
| last_emotion_json | TEXT | JSON string of emotion analysis |
| last_improvement_json | TEXT | JSON string of improvement plan |
| last_token_usage_json | TEXT | JSON string of token usage stats |
| iterations | INTEGER | Number of pipeline iterations |
| tokens_used | INTEGER | Total tokens for the run |
| last_error | TEXT | Error message from failed run |
| created_at | TEXT | UTC timestamp when the session was created |
| updated_at | TEXT | UTC timestamp for last update |

## Table: session_config

Stores per-session configuration from the UI.

| Column | Type | Notes |
| --- | --- | --- |
| session_id | TEXT | Primary key; matches sessions.session_id |
| config_json | TEXT | JSON string of config settings |
| updated_at | TEXT | UTC timestamp for last update |

Config JSON fields:

- model: normalized model name or alias
- temperature: float clamped to 0.0 - 1.0
- max_iterations: integer, minimum 1
