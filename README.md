# Test Application - SDE Setup Example

This folder demonstrates the correct setup for a Strategic Development Engine project.

## Folder Structure

```
test_application/
├── .git/                    ← Git repository (initialized)
├── .claude/                 ← Progress tracking folder
│   └── PROGRESS.md         ← Will be created by @Orchestrator
│
└── spec/                   ← Specification templates
    ├── 00_MISSION.md
    ├── 01_REQUIREMENTS.md
    ├── 02_ARCHITECTURE.md
    ├── 03_API_SPEC.md
    ├── 04_DATABASE_SCHEMA.md
    ├── 05_DESIGN_SYSTEM.md
    ├── 06_COMPONENT_SPEC.md
    ├── 07_TESTING_STRATEGY.md
    └── 08_DEPLOYMENT.md
```

## What Was Done

1. ✅ Created `test_application/` folder
2. ✅ Initialized git with `git init`
3. ✅ Created `spec/` and `.claude/` folders
4. ✅ Copied all 9 spec templates from `spec_template/` into `spec/`

## Next Steps to Use This

1. **Navigate to this directory:**
   ```bash
   cd "C:/Users/jquez/Cursor Applications/test_application"
   ```

2. **Start Claude Code:**
   ```bash
   claude-code
   ```

3. **Launch with @Orchestrator:**
   ```
   @Orchestrator, we're starting a new [TYPE] application.

   Stack: [YOUR STACK]

   Key features:
   - [Feature 1]
   - [Feature 2]

   Please kick off @Product_Owner to gather requirements.
   ```

## What Will Happen

- Agents will read/write to the `spec/` folder
- Code will be created in this directory (src/, app/, etc.)
- Progress will be tracked in `.claude/PROGRESS.md`
- The final application will live entirely in this folder

## This is Your Template

For any new project, repeat this exact structure:
1. Create project folder
2. `git init`
3. `mkdir spec .claude`
4. Copy spec templates
5. Start Claude Code
6. Invoke @Orchestrator
