# UPC_GAME

A simple 2D game simulation engine with an API.

**WICHTIG: Jedes Mal, wenn du an diesem Projekt arbeitest, musst du zuerst dein virtuelles Environment aktivieren. Öffne dazu dein Ubuntu-Terminal und führe die folgenden Befehle aus:**

    ```bash
    cd /home/Daniel/UPC_PyGame/UPC_GAME/
    source venv/bin/activate

## Installation

1.  **Prerequisites:**
    * Python 3.x installed on your system.
    * `pip` package installer (should come with Python).

2.  **Create and activate a virtual environment (recommended):**

    It's highly recommended to use a virtual environment to isolate the project dependencies.

    * **Check if you have `venv` installed:**

        ```bash
        python3 -m venv --help
        ```

        If you don't see the help message, you might need to install it:

        ```bash
        sudo apt update
        sudo apt install python3-venv  # On Debian/Ubuntu
        # Or similar command for your distribution (e.g., yum on Fedora/CentOS)
        ```
    * **Create a virtual environment:**

        Navigate to the root directory of this project (`UPC_GAME`) in your terminal and run:

        ```bash
        python3 -m venv venv
        ```

        This will create a folder named `venv` containing the virtual environment.
    * **Activate the virtual environment:**

        * **On Linux:**

            ```bash
            source venv/bin/activate
            ```
        * **On Windows (Command Prompt):**

            ```bash
            venv\Scripts\activate
            ```
        * **On Windows (PowerShell):**

            ```powershell
            .\venv\Scripts\Activate.ps1
            ```

        Your terminal prompt should now be prefixed with `(venv)`.

3.  **Install project dependencies:**

    Navigate to the project root directory (where `requirements.txt` is located) and run:

    ```bash
    pip install -r requirements.txt
    ```

    This will install all the necessary libraries listed in the `requirements.txt` file within your active virtual environment.

## Usage

1.  Ensure your virtual environment is activated (see Installation step 2).
2.  Run the demo script:

    ```bash
    python run_demo.py
    ```

    This will start the FastAPI server and the Pygame visualizer.

## Contributing

We welcome contributions from the community! If you'd like to help improve UPC\_GAME, please follow these guidelines:

1.  **Fork the repository** on GitHub.
2.  **Create a branch** for your changes (e.g., `feature/new-feature` or `bugfix/fix-issue`).
3.  **Make your changes** and ensure they are well-documented and tested.
4.  **Submit a pull request** to the `main` branch.

Please include a clear description of your changes and any relevant context.

**Contributor:** Daniel Müller (Uni Stuttgart)

## License

### The "Do-What-The-Heck-You-Want-To" License (DWTHWTYWT)

Copyright © 2025 Daniel Müller

This license allows you to do whatever the heck you want to with this code, including using it for commercial purposes, modifying it, and distributing it. The only requirement is that you include this license in any copies or derivatives of the code.

**In short: Go nuts! Just don't blame me if it sets your computer on fire.**
