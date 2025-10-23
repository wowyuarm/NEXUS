# 01: Setup and Run

This guide provides a complete walkthrough for setting up the YX NEXUS development environment and running the application locally.

## I. Prerequisites

Before you begin, ensure you have the following installed on your system:

-   **Git**: For version control.
-   **Python**: Version 3.10 or higher.
-   **Node.js**: Version 18 or higher, along with `pnpm` (recommended package manager).
-   **MongoDB**: A running instance of MongoDB. You can use a local installation or a free cloud instance from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register).

## II. Initial Setup

### Step 1: Clone the Repository

Clone the project to your local machine:
```bash
git clone <your-repository-url>
cd NEXUS
```

### Step 2: Create a Feature Branch (For Non-Trivial Changes)

**Branch Strategy**: 
- **Simple changes** (documentation updates, minor fixes) can be committed directly to `main`
- **Feature development, bug fixes, refactoring** require a dedicated feature branch

For feature branches:

```bash
# Check current branch (should be 'main')
git branch --show-current

# Create your feature branch
git checkout -b [type]/[descriptive-name]
# Examples:
#   git checkout -b feat/my-new-feature
#   git checkout -b fix/bug-description
#   git checkout -b docs/update-readme

# Verify you're on the new branch
git branch --show-current
```

**Branch naming conventions**:
- `feat/[name]` - for new features
- `fix/[name]` - for bug fixes
- `refactor/[name]` - for refactoring
- `docs/[name]` - for documentation
- `test/[name]` - for tests

Use lowercase with hyphens (kebab-case), keep it concise (3-5 words max).

### Step 3: Configure Environment Variables

The project uses a `.env` file in the root directory to manage secret keys and environment-specific configurations.

1.  Create a `.env` file by copying the example file:
    ```bash
    cp .env.example .env
    ```
2.  Open the newly created `.env` file and fill in the required values:

    -   `GEMINI_API_KEY`: Your API key for Google Gemini. Obtain this from [Google AI Studio](https://aistudio.google.com/app/apikey).
    -   `MONGO_URI`: Your MongoDB connection string. For MongoDB Atlas, this can be found in your cluster's "Connect" dialog.
    -   `TAVILY_API_KEY`: Your API key for the Tavily search service, used by the `web_search` tool. Obtain this from the [Tavily AI website](https://tavily.com/).

## III. Backend Setup (NEXUS)

The backend is a Python application. We will set up a dedicated virtual environment for it.

### Step 4: Create and Activate Virtual Environment

From the project's root directory (`NEXUS/`):
```bash
# Create the virtual environment
python -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate
```

### Step 5: Install Python Dependencies

With the virtual environment activated, install all required packages:
```bash
pip install -r requirements.txt
```
This will install all application and testing dependencies.

### Step 6: Run the Backend

You can now start the NEXUS backend server:
```bash
python -m nexus.main
```
If successful, you will see logs indicating that the services have been initialized, the `NexusBus` is running, and the FastAPI server is listening on `http://127.0.0.1:8000`.

## IV. Frontend Setup (AURA)

The frontend is a React application built with Vite.

### Step 7: Install Node.js Dependencies

Navigate to the `aura` directory and install the dependencies using `pnpm`:
```bash
cd aura
pnpm install
```

### Step 8: Configure Frontend Environment

The AURA frontend reads its configuration from its own `.env` file.

1.  Create the `.env` file in the `aura/` directory:
    ```bash
    cp .env.example .env
    ```
2.  The default values `VITE_AURA_WS_URL=ws://localhost:8000/api/v1/ws` and `VITE_AURA_API_URL=http://localhost:8000/api/v1` are typically correct for local development and do not need to be changed.

### Step 9: Run the Frontend

Start the Vite development server:
```bash
pnpm dev
```
If successful, the AURA interface will be available at `http://localhost:5173` (or another port if 5173 is in use).

## V. Verification

Once both the backend and frontend are running:

1.  Open your web browser and navigate to `http://localhost:5173`.
2.  You should see the initial AURA screen with the centered `YX NEXUS` title and input box.
3.  Open your browser's developer console. You should see a log message indicating a successful WebSocket connection to NEXUS.
4.  Type a message (e.g., "Hello") and send it. You should see the full interactive response from the AI.

Congratulations, your local NEXUS & AURA ecosystem is now fully operational.