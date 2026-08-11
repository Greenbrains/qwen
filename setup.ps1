# ============================================
# Tutu Travel Agent - Project Setup Script
# ============================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "TUTU TRAVEL AGENT - Creating project structure" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Root directory: $RootDir" -ForegroundColor Green
Write-Host ""

# ============================================
# 1. Create folders
# ============================================
Write-Host "Creating folders..." -ForegroundColor Yellow

$folders = @(
    "agent_core",
    "agent_core\models",
    "agent_core\prompts",
    "agent_core\loaders",
    "agents",
    "agents\workflows",
    "tools",
    "tests",
    "knowledge_base",
    "ui_integration",
    "ui_integration\telegram_bot",
    "ui_integration\web_widget"
)

foreach ($folder in $folders) {
    $fullPath = Join-Path $RootDir $folder
    if (!(Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "  [OK] Created folder: $folder" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] Folder exists: $folder" -ForegroundColor DarkGray
    }
}

Write-Host ""

# ============================================
# 2. Create files
# ============================================
Write-Host "Creating files..." -ForegroundColor Yellow

$files = @(
    "agent_core\__init__.py",
    "agent_core\loaders\__init__.py",
    "agent_core\models\yandexgpt_config.json",
    "agent_core\prompts\travel_assistant.md",
    "agent_core\prompts\mcp_instructions.md",
    "agent_core\loaders\prompt_loader.py",
    "agent_core\loaders\config_loader.py",
    "agents\travel_assistant.yaml",
    "agents\workflows\multicity_planner.yaml",
    "agents\workflows\budget_calculator.yaml",
    "tools\mcp_tutu.config.json",
    "tools\web_search.config.json",
    "tools\code_interpreter.py",
    "tools\image_gen.config.json",
    "tests\__init__.py",
    "tests\test_mcp_server.py",
    "tests\test_agent_creation.py",
    "knowledge_base\travel_hacks.md",
    "knowledge_base\faq_tutu.md",
    "main.py",
    "README.md",
    "PRESENTATION.md",
    ".gitignore"
)

foreach ($file in $files) {
    $fullPath = Join-Path $RootDir $file
    if (!(Test-Path $fullPath)) {
        New-Item -ItemType File -Path $fullPath -Force | Out-Null
        Write-Host "  [OK] Created file: $file" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] File exists: $file" -ForegroundColor DarkGray
    }
}

Write-Host ""

# ============================================
# 3. Fill key files
# ============================================
Write-Host "Filling key files..." -ForegroundColor Yellow

# --- .gitignore ---
$gitignoreLines = @(
    "# Python",
    "__pycache__/",
    "*.py[cod]",
    "*.so",
    ".Python",
    "env/",
    "venv/",
    "build/",
    "dist/",
    "*.egg-info/",
    "",
    "# Secrets",
    ".env",
    ".env.local",
    "secrets/",
    "*.key",
    "*.pem",
    "",
    "# IDE",
    ".vscode/",
    ".idea/",
    "*.swp",
    "*.swo",
    "",
    "# OS",
    ".DS_Store",
    "Thumbs.db",
    "",
    "# Project",
    "*.log"
)
[System.IO.File]::WriteAllLines((Join-Path $RootDir ".gitignore"), $gitignoreLines)
Write-Host "  [OK] .gitignore" -ForegroundColor Green

# --- README.md ---
$readmeLines = @(
    "# Tutu Travel Agent",
    "",
    "AI travel assistant based on Yandex AI Studio and Tutu MCP server.",
    "",
    "## Run tests",
    "python main.py",
    "",
    "## Project Structure",
    "- agent_core/ - agent core (models, prompts, loaders)",
    "- agents/ - agent configs and workflows",
    "- tools/ - tool configs (MCP, Web Search, etc.)",
    "- tests/ - project tests",
    "- knowledge_base/ - RAG knowledge base",
    "- ui_integration/ - UI integrations (Telegram, Web)",
    "",
    "## MCP Server",
    "- URL: https://mcp.tutu.ru/mcp",
    "- Protocol: Streamable HTTP (no auth)"
)
[System.IO.File]::WriteAllLines((Join-Path $RootDir "README.md"), $readmeLines)
Write-Host "  [OK] README.md" -ForegroundColor Green

# --- main.py ---
$mainLines = @(
    '"""',
    'Main entry point for running project tests',
    '"""',
    '',
    'import sys',
    'import os',
    '',
    'sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))',
    '',
    '',
    'def print_banner():',
    '    print("\n" + "=" * 70)',
    '    print("TUTU TRAVEL AGENT - AI Hackathon Project")',
    '    print("=" * 70 + "\n")',
    '',
    '',
    'def run_mcp_tests():',
    '    try:',
    '        from tests.test_mcp_server import run_all_mcp_tests',
    '        return run_all_mcp_tests()',
    '    except ImportError as e:',
    '        print(f"MCP tests module not found: {e}\n")',
    '        return None',
    '',
    '',
    'def main():',
    '    print_banner()',
    '    print("Running project tests...\n")',
    '',
    '    print("Module 1: MCP Server Tests")',
    '    print("-" * 70 + "\n")',
    '    mcp_result = run_mcp_tests()',
    '',
    '    print("\n" + "=" * 70)',
    '    print("FINAL REPORT")',
    '    print("=" * 70 + "\n")',
    '',
    '    if mcp_result is None:',
    '        print("[SKIPPED] MCP Server Tests")',
    '    elif mcp_result:',
    '        print("[PASSED] MCP Server Tests")',
    '    else:',
    '        print("[FAILED] MCP Server Tests")',
    '',
    '',
    'if __name__ == "__main__":',
    '    main()'
)
[System.IO.File]::WriteAllLines((Join-Path $RootDir "main.py"), $mainLines)
Write-Host "  [OK] main.py" -ForegroundColor Green

# --- agent_core/__init__.py ---
$initLines = @(
    '"""',
    'Tutu Travel Agent - Agent Core',
    '"""',
    '',
    '__version__ = "1.0.0"',
    '__all__ = []'
)
[System.IO.File]::WriteAllLines((Join-Path $RootDir "agent_core\__init__.py"), $initLines)
[System.IO.File]::WriteAllText((Join-Path $RootDir "agent_core\loaders\__init__.py"), "")
[System.IO.File]::WriteAllText((Join-Path $RootDir "tests\__init__.py"), "")
Write-Host "  [OK] __init__.py files" -ForegroundColor Green

# --- tools/mcp_tutu.config.json ---
$mcpConfigLines = @(
    '{',
    '  "type": "mcp",',
    '  "server_url": "https://mcp.tutu.ru/mcp",',
    '  "server_label": "tutu_travel",',
    '  "description": "Tutu MCP server for travel search and booking",',
    '  "require_approval": "never"',
    '}'
)
[System.IO.File]::WriteAllLines((Join-Path $RootDir "tools\mcp_tutu.config.json"), $mcpConfigLines)
Write-Host "  [OK] tools/mcp_tutu.config.json" -ForegroundColor Green

Write-Host ""

# ============================================
# 4. Final report
# ============================================
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Project structure created successfully!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Open in VS Code: code ." -ForegroundColor White
Write-Host "  2. Run tests: python main.py" -ForegroundColor White
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
