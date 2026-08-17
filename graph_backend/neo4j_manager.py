import socket
import subprocess
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

NEO4J_HOST = "127.0.0.1"
NEO4J_PORT = 7687
NEO4J_DBMS_ID = "f6249800-a52d-42fa-ab64-b46934cdd157"
NEO4J_CLI = Path(r"C:\Users\user\AppData\Local\neo4j-cli\neo4j-cli.exe")

# Neo4j Desktop 2 installation path.
# Verify this path on your machine.
NEO4J_DESKTOP = r"C:\Users\user\AppData\Local\Programs\Neo4j Desktop 2\Neo4j Desktop 2.exe"

def is_neo4j_running():
    """Check whether Neo4j Bolt is available."""

    try:
        with socket.create_connection(
            (NEO4J_HOST, NEO4J_PORT),
            timeout=1
        ):
            return True

    except OSError:
        return False


def start_neo4j_desktop():
    logger.info("Starting Neo4j Desktop...")

    subprocess.Popen(
        [NEO4J_DESKTOP],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    logger.info("Neo4j Desktop launched.")


def start_neo4j_dbms():
    """Start the configured Neo4j DBMS through Neo4j CLI."""

    logger.info(
        "Starting Neo4j DBMS: %s",
        NEO4J_DBMS_ID
    )

    result = subprocess.run(
        [
            str(NEO4J_CLI),
            "--rw",
            "desktop",
            "dbms",
            "start",
            NEO4J_DBMS_ID,
        ],
        capture_output=True,
        text=True,
    )

    logger.info("Neo4j CLI stdout:\n%s", result.stdout)
    logger.info("Neo4j CLI stderr:\n%s", result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            "Neo4j DBMS failed to start.\n"
            f"Exit code: {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def wait_for_neo4j(timeout=60):
    """Wait until Neo4j Bolt becomes available."""

    logger.info(
        "Waiting for Neo4j Bolt on %s:%s...",
        NEO4J_HOST,
        NEO4J_PORT
    )

    for _ in range(timeout):

        if is_neo4j_running():
            logger.info("Neo4j is ready.")
            return True

        time.sleep(1)

    return False


def ensure_neo4j_running():
    """
    Ensure Neo4j is running before the application starts.

    Flow:

        Check Bolt
            ↓
        Already running?
            ↓
        Yes → continue
            ↓
        No
            ↓
        Start Desktop
            ↓
        Start DBMS
            ↓
        Wait for Bolt
            ↓
        Continue
    """

    # ---------------------------------------------------------
    # 1. Already running
    # ---------------------------------------------------------

    if is_neo4j_running():

        logger.info(
            "Neo4j is already running on %s:%s",
            NEO4J_HOST,
            NEO4J_PORT
        )

        return


    # ---------------------------------------------------------
    # 2. Start Neo4j Desktop
    # ---------------------------------------------------------

    start_neo4j_desktop()


    # ---------------------------------------------------------
    # 3. Start DBMS
    # ---------------------------------------------------------

    if not is_neo4j_running():

        start_neo4j_dbms()


    # ---------------------------------------------------------
    # 4. Wait for Bolt
    # ---------------------------------------------------------

    if not wait_for_neo4j(timeout=60):

        raise RuntimeError(
            "Neo4j failed to become available on "
            f"{NEO4J_HOST}:{NEO4J_PORT} within 60 seconds."
        )

    logger.info("Neo4j startup completed successfully.")