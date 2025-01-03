import json
import os
import subprocess
from typing import List, Dict
from security import safe_command


class AppSubsetManager:
    def __init__(self):
        self.config_file = "app_subsets_config.json"
        self.default_subsets = {
            "home": ["spotify", "telegram", "discord"],
            "office": ["chrome", "outlook", "notepad"],
            "media": ["spotify", "vlc"],
            "development": ["vscode", "github desktop", "terminal"]
        }
        self.load_config()

    def load_config(self) -> None:
        """Load the configuration from the JSON file or create with defaults if it doesn't exist."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.subsets = json.load(f)
            else:
                self.subsets = self.default_subsets
                self.save_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self.subsets = self.default_subsets

    def save_config(self) -> None:
        """Save the current configuration to the JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.subsets, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def verify_app_exists(self, app_name: str) -> bool:
        """
        Verify if an app exists by attempting to find it using PowerShell script.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ps_script_path = os.path.join(script_dir, "Start-FromWinStartMenuApp-CheckOnly.ps1")

        try:

            ps_command = [
                'powershell',
                '-ExecutionPolicy', 'Bypass',
                '-File', ps_script_path,
                app_name
            ]

            result = safe_command.run(subprocess.run, ps_command,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            return result.returncode == 0 and "Found" in result.stdout
        except Exception as e:
            print(f"Error verifying app {app_name}: {e}")
            return False

    def create_subset(self, subset_name: str, apps: List[str]) -> Dict[str, str]:
        """Create a new subset of applications."""
        subset_name = subset_name.lower()
        valid_apps = []
        invalid_apps = []

        for app in apps:
            app = app.lower()
            if self.verify_app_exists(app):
                valid_apps.append(app)
            else:
                invalid_apps.append(app)

        if valid_apps:
            self.subsets[subset_name] = valid_apps
            self.save_config()

            response = {
                "status": "success",
                "message": f"Created subset '{subset_name}' with applications: {', '.join(valid_apps)}"
            }
            if invalid_apps:
                response["warning"] = f"The following apps were not found and weren't added: {', '.join(invalid_apps)}"
            return response
        else:
            return {
                "status": "error",
                "message": f"No valid applications provided. Invalid apps: {', '.join(invalid_apps)}"
            }

    def delete_subset(self, subset_name: str) -> Dict[str, str]:
        """Delete an existing subset."""
        subset_name = subset_name.lower()
        if subset_name in self.subsets:
            del self.subsets[subset_name]
            self.save_config()
            return {
                "status": "success",
                "message": f"Subset '{subset_name}' has been deleted"
            }
        return {
            "status": "error",
            "message": f"Subset '{subset_name}' not found"
        }

    def get_subset_apps(self, subset_name: str) -> List[str]:
        """Get the list of applications in a subset."""
        return self.subsets.get(subset_name.lower(), [])

    def list_subsets(self) -> Dict[str, List[str]]:
        """List all available subsets and their applications."""
        return self.subsets

    def modify_subset(self, subset_name: str, action: str, apps: List[str]) -> Dict[str, str]:
        """Modify an existing subset by adding or removing applications."""
        subset_name = subset_name.lower()
        if subset_name not in self.subsets:
            return {
                "status": "error",
                "message": f"Subset '{subset_name}' not found"
            }

        if action == "add":
            valid_apps = []
            invalid_apps = []
            for app in apps:
                app = app.lower()
                if self.verify_app_exists(app):
                    if app not in self.subsets[subset_name]:
                        valid_apps.append(app)
                        self.subsets[subset_name].append(app)
                else:
                    invalid_apps.append(app)

            self.save_config()
            response = {
                "status": "success",
                "message": f"Added applications to '{subset_name}': {', '.join(valid_apps)}"
            }
            if invalid_apps:
                response["warning"] = f"The following apps were not found: {', '.join(invalid_apps)}"
            return response

        elif action == "remove":
            removed_apps = []
            not_found_apps = []
            for app in apps:
                app = app.lower()
                if app in self.subsets[subset_name]:
                    self.subsets[subset_name].remove(app)
                    removed_apps.append(app)
                else:
                    not_found_apps.append(app)

            self.save_config()
            response = {
                "status": "success",
                "message": f"Removed applications from '{subset_name}': {', '.join(removed_apps)}"
            }
            if not_found_apps:
                response["warning"] = f"The following apps were not in the subset: {', '.join(not_found_apps)}"
            return response

        return {
            "status": "error",
            "message": "Invalid action. Use 'add' or 'remove'"
        }
