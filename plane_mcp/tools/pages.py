"""Page-related tools for Plane MCP Server.

Bypasses plane-sdk for Pages because the v1 API (/api/v1/) does not
implement Pages endpoints (returns 404). Uses the legacy /api/ endpoint
which supports full CRUD via session authentication.

The legacy /api/ uses Django session auth (not API key). Set the
PLANE_SESSION_ID env var with a valid session cookie value.

See: https://github.com/makeplane/plane/issues/4108
     https://github.com/makeplane/plane/issues/8598
"""

import os
from typing import Any

import requests
from fastmcp import FastMCP

from plane_mcp.client import get_plane_client_context


def _pages_request(
    method: str,
    endpoint: str,
    json_data: dict[str, Any] | None = None,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Make HTTP request to Plane's legacy /api/ endpoint for pages.

    The v1 API does not support Pages. The legacy /api/ endpoint
    (used by the Plane frontend) supports full CRUD but requires
    session authentication instead of API key.

    Requires PLANE_SESSION_ID env var (Django session cookie value).
    """
    client, workspace_slug = get_plane_client_context()

    base_url = client.config.base_path.removesuffix("/api/v1")

    session_id = os.getenv("PLANE_SESSION_ID", "")
    if not session_id:
        raise ValueError(
            "PLANE_SESSION_ID env var required for Pages API. "
            "The legacy /api/ endpoint uses session auth, not API key."
        )

    session_cookie_name = os.getenv("PLANE_SESSION_COOKIE_NAME", "session-id")

    headers: dict[str, str] = {"Content-Type": "application/json"}
    cookies = {session_cookie_name: session_id}

    url = f"{base_url}/api/workspaces/{workspace_slug}/{endpoint.lstrip('/')}"

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        cookies=cookies,
        json=json_data,
        timeout=30.0,
    )
    response.raise_for_status()

    if response.status_code == 204:
        return None
    return response.json()


def register_page_tools(mcp: FastMCP) -> None:
    """Register all page-related tools with the MCP server."""

    # --- Project Pages ---

    @mcp.tool()
    def list_project_pages(
        project_id: str,
    ) -> list[dict[str, Any]]:
        """
        List all pages in a project.

        Args:
            project_id: UUID of the project

        Returns:
            List of page objects
        """
        result = _pages_request("GET", f"projects/{project_id}/pages/")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        return [result] if result else []

    @mcp.tool()
    def create_project_page(
        project_id: str,
        name: str,
        description_html: str = "",
        access: int | None = None,
        color: str | None = None,
        is_locked: bool | None = None,
        parent: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a page in a project.

        Args:
            project_id: UUID of the project
            name: Page title
            description_html: Page content in HTML format
            access: 0 = private (default), 1 = public
            color: Hex color (e.g. "#FF6B35")
            is_locked: Whether editing is locked
            parent: UUID of parent page (for nested/hierarchical pages)

        Returns:
            Created page object
        """
        data: dict[str, Any] = {"name": name, "description_html": description_html}
        if access is not None:
            data["access"] = access
        if color is not None:
            data["color"] = color
        if is_locked is not None:
            data["is_locked"] = is_locked
        if parent is not None:
            data["parent"] = parent

        return _pages_request("POST", f"projects/{project_id}/pages/", json_data=data)

    @mcp.tool()
    def retrieve_project_page(
        project_id: str,
        page_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve a project page by ID.

        Args:
            project_id: UUID of the project
            page_id: UUID of the page

        Returns:
            Page object with full content
        """
        return _pages_request("GET", f"projects/{project_id}/pages/{page_id}/")

    @mcp.tool()
    def update_project_page(
        project_id: str,
        page_id: str,
        name: str | None = None,
        description_html: str | None = None,
        access: int | None = None,
        color: str | None = None,
        is_locked: bool | None = None,
        parent: str | None = None,
    ) -> dict[str, Any]:
        """
        Update a project page (partial update via PATCH).

        Args:
            project_id: UUID of the project
            page_id: UUID of the page
            name: New page title
            description_html: New page content in HTML
            access: 0 = private, 1 = public
            color: Hex color
            is_locked: Whether editing is locked
            parent: UUID of parent page

        Returns:
            Updated page object
        """
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if description_html is not None:
            data["description_html"] = description_html
        if access is not None:
            data["access"] = access
        if color is not None:
            data["color"] = color
        if is_locked is not None:
            data["is_locked"] = is_locked
        if parent is not None:
            data["parent"] = parent

        return _pages_request("PATCH", f"projects/{project_id}/pages/{page_id}/", json_data=data)

    @mcp.tool()
    def archive_project_page(
        project_id: str,
        page_id: str,
    ) -> dict[str, Any]:
        """
        Archive a project page. Required before deletion.

        Args:
            project_id: UUID of the project
            page_id: UUID of the page

        Returns:
            Confirmation with page_id
        """
        _pages_request("POST", f"projects/{project_id}/pages/{page_id}/archive/")
        return {"status": "archived", "page_id": page_id}

    @mcp.tool()
    def unarchive_project_page(
        project_id: str,
        page_id: str,
    ) -> dict[str, Any]:
        """
        Unarchive a previously archived project page.

        Args:
            project_id: UUID of the project
            page_id: UUID of the page

        Returns:
            Confirmation with page_id
        """
        _pages_request("DELETE", f"projects/{project_id}/pages/{page_id}/archive/")
        return {"status": "unarchived", "page_id": page_id}

    @mcp.tool()
    def delete_project_page(
        project_id: str,
        page_id: str,
    ) -> dict[str, Any]:
        """
        Delete a project page permanently. The page must be archived first.

        Args:
            project_id: UUID of the project
            page_id: UUID of the page

        Returns:
            Confirmation with page_id
        """
        _pages_request("DELETE", f"projects/{project_id}/pages/{page_id}/")
        return {"status": "deleted", "page_id": page_id}

    # --- Workspace Pages ---

    @mcp.tool()
    def list_workspace_pages() -> list[dict[str, Any]]:
        """
        List all workspace-level pages.

        Returns:
            List of page objects
        """
        result = _pages_request("GET", "pages/")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        return [result] if result else []

    @mcp.tool()
    def create_workspace_page(
        name: str,
        description_html: str = "",
        access: int | None = None,
        color: str | None = None,
        is_locked: bool | None = None,
    ) -> dict[str, Any]:
        """
        Create a workspace-level page.

        Args:
            name: Page title
            description_html: Page content in HTML format
            access: 0 = private (default), 1 = public
            color: Hex color
            is_locked: Whether editing is locked

        Returns:
            Created page object
        """
        data: dict[str, Any] = {"name": name, "description_html": description_html}
        if access is not None:
            data["access"] = access
        if color is not None:
            data["color"] = color
        if is_locked is not None:
            data["is_locked"] = is_locked

        return _pages_request("POST", "pages/", json_data=data)

    @mcp.tool()
    def retrieve_workspace_page(
        page_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve a workspace page by ID.

        Args:
            page_id: UUID of the page

        Returns:
            Page object with full content
        """
        return _pages_request("GET", f"pages/{page_id}/")

    @mcp.tool()
    def update_workspace_page(
        page_id: str,
        name: str | None = None,
        description_html: str | None = None,
        access: int | None = None,
        color: str | None = None,
        is_locked: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update a workspace page (partial update via PATCH).

        Args:
            page_id: UUID of the page
            name: New page title
            description_html: New content in HTML
            access: 0 = private, 1 = public
            color: Hex color
            is_locked: Whether editing is locked

        Returns:
            Updated page object
        """
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if description_html is not None:
            data["description_html"] = description_html
        if access is not None:
            data["access"] = access
        if color is not None:
            data["color"] = color
        if is_locked is not None:
            data["is_locked"] = is_locked

        return _pages_request("PATCH", f"pages/{page_id}/", json_data=data)

    @mcp.tool()
    def delete_workspace_page(
        page_id: str,
    ) -> dict[str, Any]:
        """
        Delete a workspace page permanently. Must be archived first.

        Args:
            page_id: UUID of the page

        Returns:
            Confirmation with page_id
        """
        _pages_request("DELETE", f"pages/{page_id}/")
        return {"status": "deleted", "page_id": page_id}
