"""Automatic virtual folder placement engine."""

from __future__ import annotations


class FolderEngine:
    """Places notes into virtual folders based on categories and relationships."""

    def determine_folders(self, categories: list[str], tags: list[str]) -> list[str]:
        """Generate virtual folder paths from categories and top tags."""
        folders: list[str] = []

        for category in categories:
            folders.append(category)

        # Sub-folders from top tags within each category
        for category in categories:
            for tag in tags[:3]:
                folder_path = f"{category} / {tag.title()}"
                if folder_path not in folders:
                    folders.append(folder_path)

        if not folders:
            folders.append("Uncategorized")

        return folders
