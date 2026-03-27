"""
MiroFish REST API Client

Python wrapper for all MiroFish endpoints. Configurable via MIROFISH_URL env var.
"""

import os
import time
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class MiroFishClient:
    """Client for the MiroFish swarm intelligence REST API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.environ.get("MIROFISH_URL", "http://localhost:5001")).rstrip("/")
        self.session = requests.Session()

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _post(self, path: str, **kwargs) -> dict:
        resp = self.session.post(self._url(path), **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _post_with_retry(self, path: str, max_retries: int = 3, **kwargs) -> dict:
        """POST with exponential backoff retry on 429 and 5xx errors."""
        for attempt in range(max_retries + 1):
            try:
                return self._post(path, **kwargs)
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 0
                if status_code == 429 or status_code >= 500:
                    if attempt < max_retries:
                        wait = 2 ** attempt * 5  # 5s, 10s, 20s
                        logger.warning(
                            "HTTP %d on %s — retrying in %ds (attempt %d/%d)",
                            status_code, path, wait, attempt + 1, max_retries,
                        )
                        time.sleep(wait)
                        continue
                raise

    def _get(self, path: str, **kwargs) -> dict:
        resp = self.session.get(self._url(path), **kwargs)
        resp.raise_for_status()
        return resp.json()

    # --- Health ---

    def health(self) -> dict:
        """Check MiroFish health. Returns: {"status": "ok", "service": "MiroFish Backend"}"""
        return self._get("/health")

    # --- Project Management ---

    def list_projects(self, limit: int = 50) -> dict:
        """List all projects."""
        return self._get("/api/graph/project/list", params={"limit": limit})

    def get_project(self, project_id: str) -> dict:
        """Get project details."""
        return self._get(f"/api/graph/project/{project_id}")

    def delete_project(self, project_id: str) -> dict:
        """Delete a project."""
        resp = self.session.delete(self._url(f"/api/graph/project/{project_id}"))
        resp.raise_for_status()
        return resp.json()

    # --- Step 1: Upload Files & Generate Ontology ---

    def generate_ontology(
        self,
        simulation_requirement: str,
        file_path: str | None = None,
        file_content: tuple[str, bytes, str] | None = None,
        project_name: str = "SwarmBet Prediction",
        additional_context: str = "",
    ) -> dict:
        """Upload file(s) and generate ontology definition.

        Args:
            simulation_requirement: Description of the simulation goal (required).
            file_path: Path to a seed document file (PDF/MD/TXT).
            file_content: Tuple of (filename, content_bytes, mimetype) for inline upload.
            project_name: Name for the project.
            additional_context: Extra context for ontology generation.

        Returns: {"success": True, "data": {"project_id": "...", "ontology": {...}, ...}}
        """
        data = {
            "simulation_requirement": simulation_requirement,
            "project_name": project_name,
            "additional_context": additional_context,
        }

        files = {}
        if file_path:
            path = Path(file_path)
            files["files"] = (path.name, open(path, "rb"))
        elif file_content:
            fname, fbytes, ftype = file_content
            files["files"] = (fname, fbytes, ftype)

        return self._post_with_retry("/api/graph/ontology/generate", data=data, files=files if files else None)

    def upload_text(self, simulation_requirement: str, content: str,
                    filename: str = "seed_data.md",
                    project_name: str = "SwarmBet Prediction",
                    additional_context: str = "") -> dict:
        """Upload text content as seed data and generate ontology."""
        return self.generate_ontology(
            simulation_requirement=simulation_requirement,
            file_content=(filename, content.encode("utf-8"), "text/markdown"),
            project_name=project_name,
            additional_context=additional_context,
        )

    # --- Step 2: Build Knowledge Graph ---

    def build_graph(self, project_id: str) -> dict:
        """Build knowledge graph from ontology.

        Returns: {"success": True, "data": {"task_id": "...", "graph_id": "..."}}
        """
        return self._post_with_retry("/api/graph/build", json={"project_id": project_id})

    def get_task_status(self, task_id: str) -> dict:
        """Check a graph build task status."""
        return self._get(f"/api/graph/task/{task_id}")

    # --- Step 3: Simulation ---

    def create_simulation(self, project_id: str, graph_id: str, **kwargs) -> dict:
        """Create a simulation for a project.

        Returns: {"success": True, "data": {"simulation_id": "..."}}
        """
        payload = {"project_id": project_id, "graph_id": graph_id, **kwargs}
        return self._post("/api/simulation/create", json=payload)

    def prepare_simulation(self, simulation_id: str) -> dict:
        """Generate agent profiles for the simulation."""
        return self._post("/api/simulation/prepare", json={"simulation_id": simulation_id})

    def get_prepare_status(self, simulation_id: str) -> dict:
        """Check simulation preparation status."""
        return self._post("/api/simulation/prepare/status", json={"simulation_id": simulation_id})

    def start_simulation(self, simulation_id: str) -> dict:
        """Start running the swarm simulation."""
        return self._post_with_retry("/api/simulation/start", json={"simulation_id": simulation_id})

    def get_run_status(self, simulation_id: str) -> dict:
        """Check simulation run status."""
        return self._get(f"/api/simulation/{simulation_id}/run-status")

    def get_simulation(self, simulation_id: str) -> dict:
        """Get full simulation details."""
        return self._get(f"/api/simulation/{simulation_id}")

    def poll_status(self, simulation_id: str, interval: float = 5.0, timeout: float = 1800.0) -> dict:
        """Poll simulation run status until completed or failed.

        Args:
            simulation_id: The simulation to poll.
            interval: Seconds between polls (default 5s).
            timeout: Max seconds to wait (default 10 min).

        Returns: Final status dict.
        Raises: TimeoutError if simulation doesn't complete in time.
        """
        start = time.time()
        while True:
            status = self.get_run_status(simulation_id)
            data = status.get("data", status)
            run_status = data.get("runner_status", data.get("status", data.get("run_status", "unknown")))
            if run_status in ("completed", "finished", "failed", "error"):
                return status
            if time.time() - start > timeout:
                raise TimeoutError(
                    f"Simulation {simulation_id} did not complete within {timeout}s. "
                    f"Last status: {status}"
                )
            time.sleep(interval)

    # --- Reports & Chat ---

    def generate_report(self, simulation_id: str) -> dict:
        """Generate a prediction report from completed simulation.

        Uses retry logic — report generation is prone to 429 rate limits.
        """
        return self._post_with_retry("/api/report/generate", json={"simulation_id": simulation_id})

    def get_report_status(self, simulation_id: str) -> dict:
        """Check report generation status.

        Args:
            simulation_id: The simulation whose report status to check.
        """
        return self._post("/api/report/generate/status", json={"simulation_id": simulation_id})

    def get_report(self, report_id: str) -> dict:
        """Get a generated report."""
        return self._get(f"/api/report/{report_id}")

    def chat(self, simulation_id: str, message: str) -> dict:
        """Chat with the report agent to extract specific insights."""
        return self._post("/api/report/chat", json={
            "simulation_id": simulation_id,
            "message": message,
        })

    # --- Convenience ---

    def run_full_simulation(
        self,
        name: str,
        description: str,
        seed_content: str,
        extraction_prompt: str | None = None,
        verbose: bool = False,
    ) -> dict:
        """Run the full pipeline: ontology → graph → simulate → report → extract.

        Args:
            name: Project name.
            description: The question being analyzed (used as simulation_requirement).
            seed_content: Markdown text of seed data.
            extraction_prompt: What to ask the report agent. Defaults to consensus extraction.
            verbose: Print progress updates.

        Returns: {
            "project_id": str,
            "simulation_id": str,
            "report": dict,
            "prediction": dict,
            "status": dict,
        }
        """
        if extraction_prompt is None:
            extraction_prompt = (
                "What percentage of agents believe the outcome is YES? "
                "What was the consensus shift over simulation rounds? "
                "Rate confidence as LOW, MEDIUM, or HIGH. "
                "List the top 3 key insights that drove the consensus."
            )

        def log(msg):
            if verbose:
                print(msg)

        # Step 1: Upload seed data and generate ontology
        log("  → Uploading seed data & generating ontology...")
        ontology_result = self.upload_text(
            simulation_requirement=description,
            content=seed_content,
            project_name=name,
        )
        project_id = ontology_result["data"]["project_id"]
        log(f"  → Project created: {project_id}")

        # Step 2: Build knowledge graph
        log("  → Building knowledge graph...")
        build_result = self.build_graph(project_id)
        task_id = build_result["data"]["task_id"]
        graph_id = build_result["data"].get("graph_id")

        # Poll graph build if needed
        if task_id:
            start = time.time()
            while time.time() - start < 300:
                task = self.get_task_status(task_id)
                task_data = task.get("data", task)
                if task_data.get("status") in ("completed", "finished", "done"):
                    graph_id = task_data.get("graph_id", graph_id)
                    break
                if task_data.get("status") in ("failed", "error"):
                    return {"project_id": project_id, "error": f"Graph build failed: {task_data}"}
                time.sleep(3)

        # Fallback: if graph_id is still None, retrieve it from the project list API
        if not graph_id:
            log("  → graph_id not in task status, querying project list...")
            try:
                projects = self.list_projects(limit=50)
                for proj in projects.get("data", []):
                    if proj.get("project_id") == project_id:
                        graph_id = proj.get("graph_id")
                        break
            except Exception as e:
                log(f"  → Warning: failed to query project list: {e}")

        if not graph_id:
            return {"project_id": project_id, "error": "Graph build completed but graph_id could not be retrieved"}

        log(f"  → Graph built: {graph_id}")

        # Step 3: Create & prepare simulation
        log("  → Creating simulation...")
        sim = self.create_simulation(project_id, graph_id)
        simulation_id = sim["data"]["simulation_id"]

        log("  → Preparing agent profiles...")
        self.prepare_simulation(simulation_id)

        # Poll preparation status (allow time for async prep to start)
        time.sleep(5)
        prep_ready = False
        start = time.time()
        while time.time() - start < 300:
            prep = self.get_prepare_status(simulation_id)
            prep_data = prep.get("data", prep)
            prep_status = prep_data.get("status", "unknown")
            log(f"    prepare status: {prep_status}")
            if prep_status in ("ready", "completed", "prepared"):
                prep_ready = True
                break
            if prep_status in ("failed", "error"):
                return {"project_id": project_id, "simulation_id": simulation_id, "error": f"Preparation failed: {prep_data}"}
            time.sleep(3)

        if not prep_ready:
            return {
                "project_id": project_id,
                "simulation_id": simulation_id,
                "error": f"Preparation timed out after 300s (last status: {prep_status}). "
                         "This usually means the NVIDIA API is rate-limited (429). "
                         "Wait a few minutes and try again.",
            }

        # Step 4: Start simulation
        log("  → Starting swarm simulation...")
        self.start_simulation(simulation_id)
        log("  → Polling simulation status...")
        status = self.poll_status(simulation_id)

        status_data = status.get("data", status)
        run_status = status_data.get("runner_status", status_data.get("status", "unknown"))
        if run_status in ("failed", "error"):
            return {
                "project_id": project_id,
                "simulation_id": simulation_id,
                "status": status,
                "report": None,
                "prediction": None,
                "error": "Simulation failed",
            }

        # Step 5: Generate report and extract prediction (with retry for rate limits)
        log("  → Generating report...")
        report = self.generate_report(simulation_id)  # already uses _post_with_retry
        log("  → Extracting prediction via chat...")
        prediction = self._post_with_retry("/api/report/chat", json={
            "simulation_id": simulation_id,
            "message": extraction_prompt,
        })

        return {
            "project_id": project_id,
            "simulation_id": simulation_id,
            "status": status,
            "report": report,
            "prediction": prediction,
        }
