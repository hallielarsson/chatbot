import json
import uuid
from sqlite3 import IntegrityError

import aiosqlite

from chat_history.loggers import BaseLogger, get_timestamp
from output_handler import OutputHandler

class HistoryLog(BaseLogger):
    def __init__(self, output_handler: OutputHandler, db_name='logs/chat_db',
                 table_name='chat_history', file_name='chat_history.jsonl'):
        super().__init__(output_handler, db_name, table_name, file_name)
        self.history = self.load_from_file()
        self.archived_history = self.load_from_file()

    async def init(self):
        await self.init_db()
        await self.load_history()

    async def init_db(self):
        """Initialize the database and create the chat history table."""
        try:
            self.connection = await aiosqlite.connect(self.db_name)
            async with self.connection.cursor() as cursor:
                await cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id VARCHAR(36) PRIMARY KEY,
                    role VARCHAR(10),
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    vector_index TEXT
                    )
                """)
                await self.connection.commit()
                await self.output_handler.send_output(f"Table {self.table_name} in {self.db_name} initialises",
                                                 message_type="system")
        except Exception as e:
            await self.output_handler.send_output(
                f"Error initializing database: {str(e)}", message_type="error"
            )

    async def load_history(self):
        """Load chat history from database or file."""
        try:
            self.history =  await self.load_from_db()
        except Exception as e:
            await self.output_handler.send_output(
                f"Error loading from DB: {str(e)}. Loading from file.",
                message_type="system"
            )
            self.history = self.load_from_file()

    async def load_from_db(self):
        """Load history from the database."""
        history = []
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(f"""
                    SELECT id, role, content, timestamp, created, updated, vector_index 
                    FROM {self.table_name}
                """)
                async for row in cursor:
                    # Check if the row has the expected number of columns
                    if len(row) < 6:  # Ensure we have at least 6 columns
                        await self.output_handler.send_output(
                            f"Row returned with insufficient columns: {row}", message_type="warning"
                        )
                        continue  # Skip this row if it's not valid

                    entry = {
                        "id": row[0],
                        # You might want to set this differently, as IDs are typically from the database.
                        "role": row[1],
                        "content": row[2],
                        "timestamp": row[3],
                        "created": row[4],
                        "updated": row[5],
                        "vector_index": row[6]  # Make sure this matches the column order in your table
                    }
                    history.append(entry)
            await self.output_handler.send_output(
                f"Chat history loaded from {self.table_name}."
            )
        except Exception as e:
            await self.output_handler.queue_output(
                f"Error loading from database: {str(e)}", message_type="error"
            )
        self.history = history
        return history

    def load_from_file(self):
        """Load history from a JSON file."""
        history = []
        try:
            with open(self.history_file, 'r') as file:
                for line in file:
                    history.append(json.loads(line))
            self.output_handler.queue_output(
                f"Chat history loaded from {self.history_file}.",
                message_type="system"
            )
        except FileNotFoundError:
            self.output_handler.queue_output(
                f"{self.history_file} not found. Starting with an empty history.",
                message_type="system"
            )
        except json.JSONDecodeError as e:
            self.output_handler.queue_output(
                f"Error decoding JSON from {self.history_file}: {str(e)}",
                message_type="error"
            )
        return history

    async def save_logs(self, logs=None):
        """Save the current chat history to the database and/or file."""
        if logs:
            self.history.extend(logs)
        logs = logs or self.history
        if logs:
            async with self.save_lock:
                try:
                    async with self.connection.cursor() as cursor:
                        for entry in logs:
                            await cursor.execute(f"""
                                INSERT INTO {self.table_name} 
                                (id, role, content, timestamp, created, updated, 
                                vector_index)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (entry["id"], entry["role"], entry["content"],
                                  entry["timestamp"], entry["created"],
                                  entry["updated"], entry["vector_index"]))  # Update to vector_index
                        await self.connection.commit()
                    await self.output_handler.send_output(
                        f"Chat history saved to {self.table_name}."
                    )
                except IntegrityError as e:
                    self.output_handler.queue_output(
                        f"Duplicate ID detected for {entry['id']} {entry['content']}. Skipping this entry.",
                        message_type="warning"
                    )
                except Exception as e:
                    await self.output_handler.send_output(
                        f"Error saving to database: {str(e)}", message_type="error"
                    )

            try:
                with open(self.history_file, 'a') as file:
                    for entry in logs:
                        file.write(json.dumps(entry))
                        file.write('\n')
            except IOError as e:
                await self.output_handler.send_output(
                    f"Error saving to file: {str(e)}", message_type="error"
                )

    async def log_entry(self, role, content, vector_index=None, entry_id=None):
        now = get_timestamp()
        entry_id = entry_id or str(uuid.uuid4())

        entry = {
            "id": entry_id,  # Generate a GUID for each entry
            "role": role,
            "content": content,
            "timestamp": now,
            "created": now,
            "updated": now,  # Set created and updated timestamps
            "vector_index": vector_index if vector_index is not None else ''  # Set vector index or empty
        }
        self.history.append(entry)

        await self.save_logs([entry])
        return entry

    async def get_by_id(self, entry_id: str):
        """Retrieve a chat log entry by its ID."""
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute(f"""
                    SELECT role, content, timestamp, created, updated, vector_index 
                    FROM {self.table_name} WHERE id = ?
                """, (entry_id,))
                row = await cursor.fetchone()
                if row:
                    entry = {
                        "id": entry_id,
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2],
                        "created": row[3],
                        "updated": row[4],
                        "vector_index": row[5]  # Update to vector_index
                    }
                    await self.output_handler.send_output(
                        f"Chat entry retrieved: {entry}", message_type="system"
                    )
                    return entry
                else:
                    await self.output_handler.send_output(
                        f"No chat entry found with ID: {entry_id}", message_type="warning"
                    )
                    return None
        except Exception as e:
            await self.output_handler.send_output(
                f"Error retrieving chat entry by ID: {str(e)}", message_type="error"
            )
            return None
