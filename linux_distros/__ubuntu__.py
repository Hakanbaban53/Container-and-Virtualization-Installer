from os import getenv
import subprocess


def ubuntu_package_installer(packages, hide_output):
    subprocess.run(["sudo", "apt", "update"])
    for data in packages:
        value = data.get("value", "")
        try:
            if type == "install-package":
                packages_to_check = value.split()
                subprocess.run(["sudo", "apt", "list", "installed", packages_to_check])
            elif type == "install-package-flatpak":
                subprocess.run(["flatpak", "list", "|", "grep", value])
            else:
                type_of_action(data, hide_output)
        except subprocess.CalledProcessError:
            type_of_action(data, hide_output)


def type_of_action(data, hide_output):
    current_user = getenv("USER")
    target_directory = f"/home/{current_user}/"
    name = data.get("name", "")
    type = data.get("type", "")
    value = data.get("value", "")
    try:
        if hide_output:
            devnull = open("/dev/null", "w")
            stdout = stderr = devnull
        else:
            stdout = stderr = None
        if type == "install-package":
            packages_to_install = value.split()  # Split the package names into a list
            subprocess.run(
                ["sudo", "apt", "-y", "install"] + packages_to_install,
                check=True,
                stderr=stderr,
                stdout=stdout,
            )

        elif type == "get-keys":
            keys = data["script"]
            for command in keys:
                try:
                    subprocess.run(
                        command, shell=True, check=True, stderr=stderr, stdout=stdout
                    )
                    print("Script executed successfully.")
                except subprocess.CalledProcessError as err:
                    print(f"An error occurred: {err}")

        elif type == "local-package":
            subprocess.run(
                [
                    "wget",
                    "--show-progress",
                    "--progress=bar:force",
                    "-O",
                    f"{target_directory}local.package.deb",
                    value,
                ],
                check=True,
            )
            subprocess.run(
                [
                    "sudo",
                    "apt-get",
                    "-y",
                    "--fix-broken",
                    "install",
                    f"{target_directory}local.package.deb",
                ],
                check=True,
                stderr=stderr,
                stdout=stdout,
            )

        elif type == "remove-package":
            packages_to_remove = value.split()  # Split the package names into a list
            subprocess.run(
                ["sudo", "apt", "-y", "remove"] + packages_to_remove,
                check=True,
                stderr=stderr,
                stdout=stdout,
            )

        elif type == "add-repo-flathub":
            subprocess.run(
                ["flatpak", "remote-add", "--if-not-exists", "flathub", value]
            )

        elif type == "install-service":
            subprocess.run(["sudo", "systemctl", "restart", value])
            subprocess.run(["sudo", "systemctl", "enable", value])

        elif type == "add-group":
            subprocess.run(["sudo", "usermod", "-aG", value, current_user])

        elif type == "add-repo-flathub":
            subprocess.run(
                ["sudo", "flatpak", "remote-add", "--if-not-exists", "flathub", value]
            )

        elif type == "install-package-flatpak":
            subprocess.run(
                ["sudo", "flatpak", "install", "-y", value],
                check=True,
                stderr=stderr,
                stdout=stdout,
            )

    except subprocess.CalledProcessError as err:
        print(f"An error occurred: {err}")
