import os
import subprocess
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VMwareInstaller:
    PKGVER = "17.5.2"
    BUILDVER = "23775571"
    TOOLS_VERSION = "12.4.0-23259341"
    DKMS_MODULE = "vmware-host-modules"
    CARCH = "x86_64"
    BASE_URL = f"https://softwareupdate.vmware.com/cds/vmw-desktop/ws/{PKGVER}/{BUILDVER}/linux/packages"
    BUNDLE_URL = f"https://softwareupdate.vmware.com/cds/vmw-desktop/ws/{PKGVER}/{BUILDVER}/linux/core/VMware-Workstation-{PKGVER}-{BUILDVER}.{CARCH}.bundle.tar"
    BUNDLE_FILENAME = f"VMware-Workstation-{PKGVER}-{BUILDVER}.{CARCH}.bundle.tar"
    CACHE_DIR = f"~/.cache/vcandy/VMware"
    EXTRACTED_DIR = os.path.join(CACHE_DIR, "extracted_components")
    COMPONENT_FILENAMES = [
        f"vmware-tools-linux-{TOOLS_VERSION}.{CARCH}.component.tar",
        f"vmware-tools-linuxPreGlibc25-{TOOLS_VERSION}.{CARCH}.component.tar",
        f"vmware-tools-netware-{TOOLS_VERSION}.{CARCH}.component.tar",
        f"vmware-tools-solaris-{TOOLS_VERSION}.{CARCH}.component.tar",
        f"vmware-tools-windows-{TOOLS_VERSION}.{CARCH}.component.tar",
        f"vmware-tools-winPre2k-{TOOLS_VERSION}.{CARCH}.component.tar",
        f"vmware-tools-winPreVista-{TOOLS_VERSION}.{CARCH}.component.tar",
    ]

    def __init__(self, hide, action, linux_distro):
        self.hide = hide
        self.action = action
        self.linux_distro = linux_distro
        self.COMPONENT_URLS = [f"{self.BASE_URL}/{filename}" for filename in self.COMPONENT_FILENAMES]

        if self.action == "install":
            self.install_vmware()
        elif self.action == "remove":
            self.uninstall_vmware()

        if self.linux_distro == "fedora":
            self.DEPENDENCIES = [
                "kernel-devel",
                "kernel-headers",
                "gcc",
                "dkms",
                "make",
                "patch",
                "net-tools",
            ]   
        elif self.linux_distro in {"debian", "ubuntu"}:
            self.DEPENDENCIES = [
                "linux-headers-generic",
                "build-essential",
                "gcc",
                "dkms",
                "make",
                "patch",
                "net-tools",
            ]

    @staticmethod
    def run_command(command):
        """Run a shell command and print its output."""
        try:
            result = subprocess.run(command, shell=True, text=True, capture_output=True)
            result.check_returncode()
            logging.info(result.stdout)
        except subprocess.CalledProcessError as e:
            logging.error(f"Command failed: {command}")
            logging.error(e.stderr)

    def download_file(self, url, filename):
        """Download a file from a URL using wget."""
        logging.info(f"Downloading {filename} from {url}...")
        self.run_command(f"wget -O {os.path.join(self.CACHE_DIR, filename)} {url}")
        logging.info(f"Downloaded {filename}.")

    def extract_tar(self, filename):
        """Extract a tar file."""
        logging.info(f"Extracting {filename} to {self.EXTRACTED_DIR}...")
        self.run_command(f"tar -xf {os.path.join(self.CACHE_DIR, filename)} -C {self.EXTRACTED_DIR}")
        self.run_command(f"find {self.EXTRACTED_DIR} -name '*.xml' -type f -delete")

    def sparse_checkout(self, repo_url, branch, folder_to_clone, clone_location):
            commands = [
                f"git clone --no-checkout -b {branch} {repo_url} {clone_location}",
                f"cd {clone_location}",
                "git sparse-checkout init --cone",
                f"git sparse-checkout set {folder_to_clone}",
                "git checkout"
            ]
            
            for command in commands:
                self.run_command(command)
            
            logging.info(f"Folder {folder_to_clone} has been cloned to {clone_location}/{folder_to_clone}")

    def install_vmware_modules(self):
        logging.info("Cloning vmware-host-modules repository...")
        self.run_command(f"git clone -b workstation-17.5.1 https://github.com/mkubecek/vmware-host-modules {self.CACHE_DIR}/vmware-host-modules")

        os.chdir("{self.CACHE_DIR}/vmware-host-modules")
        logging.info("Making and copying vmmon.tar and vmnet.tar...")
        self.run_command("make tarballs")
        self.run_command("sudo cp -v vmmon.tar vmnet.tar /usr/lib/vmware/modules/source/")

        logging.info("Extracting vmmon.tar and vmnet.tar...")
        os.chdir("/usr/lib/vmware/modules/source/")
        self.run_command("sudo tar -xvf vmmon.tar")
        self.run_command("sudo tar -xvf vmnet.tar")

        logging.info("Creating directories for DKMS...")
        self.run_command(f"sudo mkdir -p /usr/src/{self.DKMS_MODULE}-{self.PKGVER}")

        logging.info("Moving source files to DKMS directory...")
        self.run_command(f"sudo cp -r vmmon-only /usr/src/{self.DKMS_MODULE}-{self.PKGVER}/")
        self.run_command(f"sudo cp -r vmnet-only /usr/src/{self.DKMS_MODULE}-{self.PKGVER}/")

        logging.info("Getting the DKMS modules")
        self.sparse_checkout("https://github.com/Hakanbaban53/Container-and-Virtualization-Installer", "Adding_the_vmware_worksitation_support_fedora" "vmware_dkms_files", f"{self.CACHE_DIR}/vmware_dkms_files")

        logging.info("Copying Makefile to DKMS directory...")
        self.run_command(f"sudo cp -r {self.CACHE_DIR}/vmware_dkms_files/Makefile /usr/src/{self.DKMS_MODULE}-{self.PKGVER}/")

        logging.info("Creating DKMS configuration for vmware-host-modules...")
        with open(f"{self.CACHE_DIR}/vmware_dkms_files/dkms.conf", "r") as template_file:
            dkms_conf_template = template_file.read()

        dkms_conf_vmware_host_modules = dkms_conf_template.format(
            PACKAGE_NAME=self.DKMS_MODULE,
            PACKAGE_VERSION=self.PKGVER
        )
        
        temp_conf_path = f"/tmp/{self.DKMS_MODULE}-{self.PKGVER}-dkms.conf"
        with open(temp_conf_path, "w") as conf_file:
            conf_file.write(dkms_conf_vmware_host_modules)
        
        self.run_command(f"sudo mv {temp_conf_path} /usr/src/{self.DKMS_MODULE}-{self.PKGVER}/dkms.conf")
        logging.info(f"DKMS configuration file created at /usr/src/{self.DKMS_MODULE}-{self.PKGVER}/dkms.conf")

        logging.info("Applying patches...")
        self.run_command(f"sudo patch -p2 -d /usr/src/{self.DKMS_MODULE}-{self.PKGVER}/vmmon-only < {self.CACHE_DIR}/vmware_dkms_files/vmmon.patch --force")
        self.run_command(f"sudo patch -p2 -d /usr/src/{self.DKMS_MODULE}-{self.PKGVER}/vmnet-only < {self.CACHE_DIR}/vmware_dkms_files/vmnet.patch --force")

        logging.info("Adding and building vmware-host-modules module with DKMS...")
        self.run_command(f"sudo dkms add -m {self.DKMS_MODULE} -v {self.PKGVER}")
        self.run_command(f"sudo dkms build -m {self.DKMS_MODULE} -v {self.PKGVER}")
        self.run_command(f"sudo dkms install -m {self.DKMS_MODULE} -v {self.PKGVER}")

        logging.info("Running vmware-modconfig to install all modules...")
        self.run_command("sudo vmware-modconfig --console --install-all")

        os.chdir("-")  # Return to previous directory

    def create_service_files(self):
        services = {
            'vmware-networks-configuration.service': """
[Unit]
Description=VMware Networks Configuration Generation
ConditionPathExists=!/etc/vmware/networking

[Service]
UMask=0077
ExecStart=/usr/bin/vmware-networks --postinstall vmware-player,0,1
Type=oneshot
RemainAfterExit=yes
""",
            'vmware-usbarbitrator.path': """
[Unit]
Description=Monitor to Load-On-Demand the VMware USB Arbitrator

[Path]
PathExistsGlob=/var/run/vmware/*/*

[Install]
WantedBy=paths.target
""",
            'vmware-usbarbitrator.service': """
[Unit]
Description=VMware USB Arbitrator

[Service]
ExecStart=/usr/lib/vmware/bin/vmware-usbarbitrator -f

[Install]
WantedBy=multi-user.target
"""
        }

        for filename, content in services.items():
            with open(f"/tmp/{filename}", 'w') as file:
                file.write(content)
            logging.info(f"Created {filename}.")
            self.run_command(f"sudo mv /tmp/{filename} /etc/systemd/system/{filename}")

    def install_dependencies(self):
        logging.info("Installing dependencies...")
        
        if self.linux_distro == "fedora":
            self.run_command(f"sudo dnf install -y {' '.join(self.DEPENDENCIES)}")
        elif self.linux_distro in {"debian", "ubuntu"}:
            self.run_command(f"sudo apt install -y {' '.join(self.DEPENDENCIES)}")

    def enable_services(self):
        logging.info("Enabling and starting VMware services...")
        services = [
            "vmware-networks-configuration.service",
            "vmware-usbarbitrator.path",
            "vmware-usbarbitrator.service"
        ]
        for service in services:
            self.run_command(f"sudo systemctl enable --now {service}")

    def add_user_to_vmware_group(self):
        user = os.getlogin()
        logging.info(f"Adding {user} to the vmware group...")
        self.run_command(f"sudo usermod -aG vmware {user}")

    def install_vmware(self):
        logging.info("Step 1: Downloading the VMware Workstation installer and components...")
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self.download_file(self.BUNDLE_URL, self.BUNDLE_FILENAME)
        for url, filename in zip(self.COMPONENT_URLS, self.COMPONENT_FILENAMES):
            self.download_file(url, filename)

        logging.info("Step 2: Extracting the bundle file...")
        self.run_command(f"tar -xf {os.path.join(self.CACHE_DIR, self.BUNDLE_FILENAME)}")

        os.makedirs(self.EXTRACTED_DIR, exist_ok=True)
        for filename in self.COMPONENT_FILENAMES:
            self.extract_tar(filename)

        logging.info("Step 3: Making the installer executable...")
        bundle_installer = f"VMware-Workstation-{self.PKGVER}-{self.BUILDVER}.{self.CARCH}.bundle"
        self.run_command(f"chmod +x {os.path.join(self.CACHE_DIR, bundle_installer)}")

        logging.info("Step 4: Running the VMware Workstation installer with extracted components...")
        extracted_components = [os.path.join(self.EXTRACTED_DIR, filename) for filename in os.listdir(self.EXTRACTED_DIR)]
        install_command = f"sudo {os.path.join(self.CACHE_DIR, bundle_installer)} --console --required --eulas-agreed " + " ".join(
            [f'--install-component "{os.path.abspath(filename)}"' for filename in extracted_components]
        )
        self.run_command(install_command)

        logging.info("Step 5: Installing necessary dependencies...")
        self.install_dependencies()

        logging.info("Step 6: Compiling kernel modules...")
        self.install_vmware_modules()

        logging.info("Step 7: Creating systemd service files...")
        self.create_service_files()

        logging.info("Step 8: Enabling and starting VMware services...")
        self.enable_services()

        logging.info("Step 9: Adding the user to the vmware group...")
        self.add_user_to_vmware_group()

        logging.info(f"VMware installation and setup on {self.linux_distro} is complete.")

    def uninstall_vmware(self):
        logging.info("Uninstalling VMware Workstation...")

        logging.info("Stopping and disabling VMware services...")
        services = [
            "vmware-networks-configuration.service",
            "vmware-usbarbitrator.path",
            "vmware-usbarbitrator.service"
        ]
        for service in services:
            self.run_command(f"sudo systemctl stop {service}")
            self.run_command(f"sudo systemctl disable {service}")

        logging.info("Removing systemd service files...")
        for service in services:
            service_file = f"/etc/systemd/system/{service}"
            if os.path.exists(service_file):
                self.run_command(f"sudo rm {service_file}")

        logging.info("Removing VMware modules from DKMS...")
        self.run_command(f"sudo dkms remove -m {self.DKMS_MODULE} -v {self.PKGVER} --all")

        logging.info("Running the uninstallation script...")
        uninstall_script = "/usr/bin/vmware-installer"
        if os.path.exists(uninstall_script):
            self.run_command(f'echo "yes" | sudo {uninstall_script} --uninstall-product vmware-workstation')

        logging.info("Removing extracted components directory...")
        if os.path.exists(self.EXTRACTED_DIR):
            shutil.rmtree(self.EXTRACTED_DIR)

        logging.info(f"VMware uninstallation on {self.linux_distro} is complete.")
