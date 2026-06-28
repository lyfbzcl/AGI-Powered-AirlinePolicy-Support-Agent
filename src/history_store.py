import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from handoff import CUSTOMER_HANDOFF_MESSAGE


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "conversations.sqlite3"
DEFAULT_TITLE = "New conversation"


def utc_now() -> str:
    """Return a stable UTC timestamp for persisted records."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def open_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with dictionary-like rows."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path: Path = DB_PATH) -> None:
    """Create the conversation history tables if they do not exist."""
    with open_connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS turns (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS turn_sources (
                id TEXT PRIMARY KEY,
                turn_id TEXT NOT NULL,
                rank INTEGER NOT NULL,
                source TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (turn_id) REFERENCES turns(id)
            );

            CREATE TABLE IF NOT EXISTS handoff_requests (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                turn_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                handoff_packet TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                FOREIGN KEY (turn_id) REFERENCES turns(id)
            );

            CREATE TABLE IF NOT EXISTS handoff_messages (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                sender_type TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES handoff_requests(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_turns_conversation
                ON turns(conversation_id, turn_index);

            CREATE INDEX IF NOT EXISTS idx_turn_sources_turn
                ON turn_sources(turn_id, rank);

            CREATE INDEX IF NOT EXISTS idx_handoff_requests_status
                ON handoff_requests(status, created_at);

            CREATE INDEX IF NOT EXISTS idx_handoff_messages_request
                ON handoff_messages(request_id, created_at, id);
            """
        )
        turn_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(turns)").fetchall()
        }
        optional_columns = {
            "action": "TEXT",
            "reason_code": "TEXT",
            "confidence_reason": "TEXT",
            "escalation_reason": "TEXT",
            "missing_fields": "TEXT",
            "handoff_packet": "TEXT",
            "verification_result": "TEXT",
            "query_analysis": "TEXT",
        }
        for column, column_type in optional_columns.items():
            if column not in turn_columns:
                connection.execute(f"ALTER TABLE turns ADD COLUMN {column} {column_type}")

        connection.execute(
            """
            INSERT OR IGNORE INTO handoff_requests (
                id,
                conversation_id,
                turn_id,
                status,
                reason_code,
                handoff_packet,
                created_at,
                updated_at
            )
            SELECT
                lower(hex(randomblob(16))),
                conversation_id,
                id,
                'pending',
                COALESCE(reason_code, ''),
                COALESCE(handoff_packet, '{}'),
                created_at,
                created_at
            FROM turns
            WHERE action = 'escalate'
            """
        )
        connection.execute(
            """
            UPDATE turns
            SET answer = ?
            WHERE action = 'escalate'
              AND (answer IS NULL OR trim(answer) = '')
            """,
            (CUSTOMER_HANDOFF_MESSAGE,),
        )


def make_title(question: str) -> str:
    """Generate a compact conversation title from the first question."""
    compact = " ".join(question.strip().split())
    if not compact:
        return DEFAULT_TITLE
    return compact[:50]


def create_conversation(title: Optional[str] = None, db_path: Path = DB_PATH) -> str:
    """Create a conversation and return its ID."""
    init_db(db_path)
    conversation_id = uuid.uuid4().hex
    now = utc_now()
    final_title = title.strip() if title and title.strip() else DEFAULT_TITLE

    with open_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO conversations (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, final_title, now, now),
        )

    return conversation_id


def rename_conversation(
    conversation_id: str,
    title: str,
    db_path: Path = DB_PATH,
) -> None:
    """Rename an existing conversation."""
    cleaned_title = " ".join(title.strip().split())
    if not cleaned_title:
        raise ValueError("Conversation title cannot be empty.")
    if len(cleaned_title) > 50:
        raise ValueError("Conversation title cannot exceed 50 characters.")

    init_db(db_path)
    with open_connection(db_path) as connection:
        updated = connection.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (cleaned_title, utc_now(), conversation_id),
        )
        if updated.rowcount == 0:
            raise ValueError(f"Conversation not found: {conversation_id}")


def delete_conversation(conversation_id: str, db_path: Path = DB_PATH) -> None:
    """Delete a conversation and all of its turns and source records."""
    init_db(db_path)
    with open_connection(db_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if exists is None:
            raise ValueError(f"Conversation not found: {conversation_id}")

        connection.execute(
            """
            DELETE FROM handoff_messages
            WHERE conversation_id = ?
            """,
            (conversation_id,),
        )
        connection.execute(
            "DELETE FROM handoff_requests WHERE conversation_id = ?",
            (conversation_id,),
        )
        connection.execute(
            """
            DELETE FROM turn_sources
            WHERE turn_id IN (
                SELECT id FROM turns WHERE conversation_id = ?
            )
            """,
            (conversation_id,),
        )
        connection.execute(
            "DELETE FROM turns WHERE conversation_id = ?",
            (conversation_id,),
        )
        connection.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,),
        )


def list_conversations(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """List conversations ordered by most recent activity."""
    init_db(db_path)
    with open_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                conversations.id,
                conversations.title,
                conversations.created_at,
                conversations.updated_at,
                COUNT(turns.id) AS turn_count
            FROM conversations
            LEFT JOIN turns ON turns.conversation_id = conversations.id
            GROUP BY conversations.id
            ORDER BY conversations.updated_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_conversation(conversation_id: str, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Return one conversation with turns and retrieved source chunks."""
    init_db(db_path)
    with open_connection(db_path) as connection:
        conversation = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()

        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")

        turn_rows = connection.execute(
            """
            SELECT
                id,
                question,
                answer,
                created_at,
                turn_index,
                action,
                reason_code,
                confidence_reason,
                escalation_reason,
                missing_fields,
                handoff_packet,
                verification_result,
                query_analysis
            FROM turns
            WHERE conversation_id = ?
            ORDER BY turn_index ASC
            """,
            (conversation_id,),
        ).fetchall()

        turns: list[dict[str, Any]] = []
        for turn in turn_rows:
            source_rows = connection.execute(
                """
                SELECT rank, source, chunk_id, text
                FROM turn_sources
                WHERE turn_id = ?
                ORDER BY rank ASC
                """,
                (turn["id"],),
            ).fetchall()

            turn_data = dict(turn)
            for json_field in (
                "missing_fields",
                "handoff_packet",
                "verification_result",
                "query_analysis",
            ):
                raw_value = turn_data.get(json_field)
                if raw_value:
                    try:
                        turn_data[json_field] = json.loads(raw_value)
                    except json.JSONDecodeError:
                        pass
            turn_data["sources"] = [dict(row) for row in source_rows]

            handoff_row = connection.execute(
                """
                SELECT id, status, reason_code, created_at, updated_at
                FROM handoff_requests
                WHERE turn_id = ?
                """,
                (turn["id"],),
            ).fetchone()
            if handoff_row:
                message_rows = connection.execute(
                    """
                    SELECT id, sender_type, sender_name, message, created_at
                    FROM handoff_messages
                    WHERE request_id = ?
                    ORDER BY created_at ASC, id ASC
                    """,
                    (handoff_row["id"],),
                ).fetchall()
                turn_data["human_support"] = {
                    **dict(handoff_row),
                    "messages": [dict(row) for row in message_rows],
                }
            else:
                turn_data["human_support"] = None
            turns.append(turn_data)

    result = dict(conversation)
    result["turns"] = turns
    return result


def get_recent_turns(
    conversation_id: str, limit: int = 6, db_path: Path = DB_PATH
) -> list[dict[str, Any]]:
    """Return the most recent turns in chronological order."""
    conversation = get_conversation(conversation_id, db_path=db_path)
    if limit <= 0:
        return []
    return conversation["turns"][-limit:]


def get_active_handoff_request(
    conversation_id: str,
    db_path: Path = DB_PATH,
) -> Optional[dict[str, Any]]:
    """Return the newest unresolved handoff for a conversation, if one exists."""
    init_db(db_path)
    with open_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, conversation_id, turn_id, status, reason_code, created_at, updated_at
            FROM handoff_requests
            WHERE conversation_id = ?
              AND status IN ('pending', 'in_progress')
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (conversation_id,),
        ).fetchone()
    return dict(row) if row else None


def add_turn(
    conversation_id: str,
    question: str,
    answer: str,
    retrieved_chunks: list[dict[str, str]],
    decision_result: Optional[dict[str, Any]] = None,
    db_path: Path = DB_PATH,
) -> str:
    """Append one QA turn and its retrieved sources to a conversation."""
    init_db(db_path)
    turn_id = uuid.uuid4().hex
    now = utc_now()

    with open_connection(db_path) as connection:
        conversation = connection.execute(
            "SELECT title FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")

        next_index = connection.execute(
            "SELECT COALESCE(MAX(turn_index), 0) + 1 FROM turns WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()[0]

        decision = decision_result or {}
        missing_info = decision.get("missing_info", {})
        action = decision.get("action", "answer")
        reason_code = decision.get("reason_code", "")
        confidence_reason = decision.get("confidence_reason", "")
        escalation_reason = decision.get("escalation_reason", "")
        missing_fields = missing_info.get("missing_fields", [])
        handoff_packet = decision.get("handoff_packet", {})
        verification_result = decision.get("verification", {})
        query_analysis = decision.get("query_analysis", {})

        connection.execute(
            """
            INSERT INTO turns (
                id,
                conversation_id,
                question,
                answer,
                created_at,
                turn_index,
                action,
                reason_code,
                confidence_reason,
                escalation_reason,
                missing_fields,
                handoff_packet,
                verification_result,
                query_analysis
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                turn_id,
                conversation_id,
                question,
                answer,
                now,
                next_index,
                action,
                reason_code,
                confidence_reason,
                escalation_reason,
                json.dumps(missing_fields),
                json.dumps(handoff_packet, ensure_ascii=False),
                json.dumps(verification_result, ensure_ascii=False),
                json.dumps(query_analysis, ensure_ascii=False),
            ),
        )

        for rank, chunk in enumerate(retrieved_chunks, start=1):
            connection.execute(
                """
                INSERT INTO turn_sources (id, turn_id, rank, source, chunk_id, text)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    turn_id,
                    rank,
                    chunk.get("source", "unknown"),
                    chunk.get("chunk_id", "unknown"),
                    chunk.get("text", ""),
                ),
            )

        if action == "escalate":
            connection.execute(
                """
                INSERT INTO handoff_requests (
                    id,
                    conversation_id,
                    turn_id,
                    status,
                    reason_code,
                    handoff_packet,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex,
                    conversation_id,
                    turn_id,
                    "pending",
                    reason_code,
                    json.dumps(handoff_packet, ensure_ascii=False),
                    now,
                    now,
                ),
            )

        title = conversation["title"]
        if title == DEFAULT_TITLE:
            title = make_title(question)

        connection.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, now, conversation_id),
        )

    return turn_id


def list_handoff_requests(
    status: Optional[str] = "pending",
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """List support handoff requests with conversation and triggering-turn context."""
    init_db(db_path)
    filters: list[str] = []
    params: list[Any] = []
    if status and status != "all":
        filters.append("handoff_requests.status = ?")
        params.append(status)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    with open_connection(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                handoff_requests.id,
                handoff_requests.conversation_id,
                handoff_requests.turn_id,
                handoff_requests.status,
                handoff_requests.reason_code,
                handoff_requests.created_at,
                handoff_requests.updated_at,
                conversations.title,
                turns.question,
                (
                    SELECT COUNT(*)
                    FROM handoff_messages
                    WHERE handoff_messages.request_id = handoff_requests.id
                ) AS message_count
            FROM handoff_requests
            JOIN conversations
                ON conversations.id = handoff_requests.conversation_id
            JOIN turns
                ON turns.id = handoff_requests.turn_id
            {where_clause}
            ORDER BY
                CASE handoff_requests.status
                    WHEN 'pending' THEN 0
                    WHEN 'in_progress' THEN 1
                    ELSE 2
                END,
                handoff_requests.updated_at DESC
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_handoff_request(
    request_id: str,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    """Return a handoff request, its full conversation, and support replies."""
    init_db(db_path)
    with open_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT
                handoff_requests.id,
                handoff_requests.conversation_id,
                handoff_requests.turn_id,
                handoff_requests.status,
                handoff_requests.reason_code,
                handoff_requests.handoff_packet,
                handoff_requests.created_at,
                handoff_requests.updated_at,
                conversations.title
            FROM handoff_requests
            JOIN conversations
                ON conversations.id = handoff_requests.conversation_id
            WHERE handoff_requests.id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Handoff request not found: {request_id}")

        result = dict(row)
        raw_packet = result.get("handoff_packet")
        try:
            result["handoff_packet"] = json.loads(raw_packet or "{}")
        except json.JSONDecodeError:
            result["handoff_packet"] = {}

        message_rows = connection.execute(
            """
            SELECT id, sender_type, sender_name, message, created_at
            FROM handoff_messages
            WHERE request_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (request_id,),
        ).fetchall()

    result["conversation"] = get_conversation(result["conversation_id"], db_path)
    result["messages"] = [dict(message) for message in message_rows]
    return result


def set_handoff_status(
    request_id: str,
    status: str,
    db_path: Path = DB_PATH,
) -> None:
    """Update a handoff request status."""
    allowed_statuses = {"pending", "in_progress", "resolved"}
    if status not in allowed_statuses:
        raise ValueError(f"Unsupported handoff status: {status}")

    init_db(db_path)
    now = utc_now()
    with open_connection(db_path) as connection:
        updated = connection.execute(
            """
            UPDATE handoff_requests
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, now, request_id),
        )
        if updated.rowcount == 0:
            raise ValueError(f"Handoff request not found: {request_id}")


def add_handoff_reply(
    request_id: str,
    message: str,
    agent_name: str,
    resolve: bool = False,
    db_path: Path = DB_PATH,
) -> str:
    """Persist a customer-service reply and update the request status."""
    cleaned_message = message.strip()
    cleaned_agent = " ".join(agent_name.strip().split()) or "Customer Service"
    if not cleaned_message:
        raise ValueError("Reply cannot be empty.")

    init_db(db_path)
    message_id = uuid.uuid4().hex
    now = utc_now()
    with open_connection(db_path) as connection:
        request = connection.execute(
            """
            SELECT conversation_id
            FROM handoff_requests
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()
        if request is None:
            raise ValueError(f"Handoff request not found: {request_id}")

        connection.execute(
            """
            INSERT INTO handoff_messages (
                id,
                request_id,
                conversation_id,
                sender_type,
                sender_name,
                message,
                created_at
            )
            VALUES (?, ?, ?, 'agent', ?, ?, ?)
            """,
            (
                message_id,
                request_id,
                request["conversation_id"],
                cleaned_agent,
                cleaned_message,
                now,
            ),
        )
        connection.execute(
            """
            UPDATE handoff_requests
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            ("resolved" if resolve else "in_progress", now, request_id),
        )
        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, request["conversation_id"]),
        )
    return message_id


def add_handoff_customer_message(
    conversation_id: str,
    message: str,
    db_path: Path = DB_PATH,
) -> Optional[str]:
    """Add a customer message to the active handoff without invoking the AI."""
    cleaned_message = message.strip()
    if not cleaned_message:
        raise ValueError("Message cannot be empty.")

    init_db(db_path)
    message_id = uuid.uuid4().hex
    now = utc_now()
    with open_connection(db_path) as connection:
        request = connection.execute(
            """
            SELECT id
            FROM handoff_requests
            WHERE conversation_id = ?
              AND status IN ('pending', 'in_progress')
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (conversation_id,),
        ).fetchone()
        if request is None:
            return None

        connection.execute(
            """
            INSERT INTO handoff_messages (
                id,
                request_id,
                conversation_id,
                sender_type,
                sender_name,
                message,
                created_at
            )
            VALUES (?, ?, ?, 'customer', 'Customer', ?, ?)
            """,
            (
                message_id,
                request["id"],
                conversation_id,
                cleaned_message,
                now,
            ),
        )
        connection.execute(
            """
            UPDATE handoff_requests
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, request["id"]),
        )
        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, conversation_id),
        )
    return message_id


def export_conversation_json(conversation_id: str, db_path: Path = DB_PATH) -> str:
    """Return a JSON representation of a conversation for debugging or backup."""
    conversation = get_conversation(conversation_id, db_path=db_path)
    return json.dumps(conversation, indent=2, ensure_ascii=False)
