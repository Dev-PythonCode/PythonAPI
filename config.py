import os


class Config:
    """Simple configuration holder.

    Reads `DB_CONNECTION` from environment. If not set, provides a placeholder
    connection string so imports don't fail during development.
    """

    DB_CONNECTION = os.environ.get(
        "DB_CONNECTION",
        ""  # Set this to your ODBC connection string in production
    )
