import json
import os
from linux_distros.__arch__ import arch_package_installer
from linux_distros.__debian__ import debian_package_installer
from linux_distros.__fedora__ import fedora_package_installer
from linux_distros.__ubuntu__ import ubuntu_package_installer



def get_linux_distribution():
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.startswith('PRETTY_NAME'):
                    _, distro_info = line.split('=')
                    return distro_info.strip().strip('"')
    except FileNotFoundError:
        return None

def identify_distribution():
    linux_distribution = get_linux_distribution()

    if linux_distribution:
        if 'arch' in linux_distribution.lower():
            return 'arch'
        elif 'debian' in linux_distribution.lower():
            return 'debian'
        elif 'fedora' in linux_distribution.lower():
            return 'fedora'
        elif 'ubuntu' in linux_distribution.lower():
            return 'ubuntu'
        else:
            return 'Unknown Linux distribution'
    else:
        return 'Not running on Linux'


def get_linux_package_manager(linux_distribution, package_name, hide_output):

    current_directory = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(current_directory, "packages.json")

    with open(json_file_path, "r") as json_file:
        instructions_data = json.load(json_file)

    if linux_distribution in instructions_data:
        if linux_distribution == "arch":
            package_data_ref = instructions_data[linux_distribution]
            for data in package_data_ref:
                name = data.get("name", "")
                if package_name in name:
                    values = data.get("values", [])
                    arch_package_installer(values, hide_output)

        elif linux_distribution == "debian":
            package_data_ref = instructions_data[linux_distribution]
            for data in package_data_ref:
                name = data.get("name", "")
                if package_name in name:
                    values = data.get("values", [])
                    debian_package_installer(values, hide_output)

        elif linux_distribution == "fedora":
            package_data_ref = instructions_data[linux_distribution]
            for data in package_data_ref:
                name = data.get("name", "")
                if package_name in name:
                    values = data.get("values", [])
                    fedora_package_installer(values, hide_output)

        elif linux_distribution == "ubuntu":
            package_data_ref = instructions_data[linux_distribution]
            for data in package_data_ref:
                name = data.get("name", "")
                if package_name in name:
                    values = data.get("values", [])
                    ubuntu_package_installer(values, hide_output)
                    
    else:
        print("No installation instructions found for the detected Linux distribution.")
        exit(1)
