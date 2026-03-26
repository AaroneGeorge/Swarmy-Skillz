"""
MiroFish REST API Client

Python wrapper for all MiroFish endpoints. Configurable via MIROFISH_URL env var.
"""

import os
import time
import requests
from pathlib import Path


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

        return self._post("/api/graph/ontology/generate", data=data, files=files if files else None)

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
        return self._post("/api/graph/build", json={"project_id": project_id})

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
        return self._post("/api/simulation/start", json={"simulation_id": simulation_id})

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
        """Generate a prediction report from completed simulation."""
        return self._post("/api/report/generate", json={"simulation_id": simulation_id})

    def get_report_status(self, report_id: str) -> dict:
        """Check report generation status."""
        return self._post("/api/report/generate/status", json={"report_id": report_id})

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
        log(f"  → Graph built: {graph_id}")

        # Step 3: Create & prepare simulation
        log("  → Creating simulation...")
        sim = self.create_simulation(project_id, graph_id)
        simulation_id = sim["data"]["simulation_id"]

        log("  → Preparing agent profiles...")
        self.prepare_simulation(simulation_id)

        # Poll preparation status (allow time for async prep to start)
        time.sleep(5)
        start = time.time()
        while time.time() - start < 300:
            prep = self.get_prepare_status(simulation_id)
            prep_data = prep.get("data", prep)
            prep_status = prep_data.get("status", "unknown")
            log(f"    prepare status: {prep_status}")
            if prep_status in ("ready", "completed", "prepared"):
                break
            if prep_status in ("failed", "error"):
                return {"project_id": project_id, "simulation_id": simulation_id, "error": f"Preparation failed: {prep_data}"}
            time.sleep(3)

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

        # Step 5: Generate report and extract prediction
        log("  → Generating report...")
        report = self.generate_report(simulation_id)
        log("  → Extracting prediction via chat...")
        prediction = self.chat(simulation_id, extraction_prompt)

        return {
            "project_id": project_id,
            "simulation_id": simulation_id,
            "status": status,
            "report": report,
            "prediction": prediction,
        }
