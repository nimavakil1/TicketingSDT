#!/usr/bin/env python3
"""
Update AI system prompt in database from the prompt file
This syncs the database with the latest prompt version from config/prompt/agent_prompt.md
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import init_database, SystemSetting

def update_prompt_in_database():
    """Load prompt from file and update database"""

    # Read the prompt file
    prompt_file = project_root / "config" / "prompt" / "agent_prompt.md"

    if not prompt_file.exists():
        print(f"❌ Error: Prompt file not found at {prompt_file}")
        return False

    print(f"Reading prompt from: {prompt_file}")
    new_prompt = prompt_file.read_text(encoding='utf-8')

    # Extract version info for display
    lines = new_prompt.split('\n')
    version_line = next((l for l in lines if l.startswith('VERSION:')), None)
    updated_line = next((l for l in lines if l.startswith('LAST UPDATED:')), None)

    print(f"Prompt file info:")
    if version_line:
        print(f"  {version_line}")
    if updated_line:
        print(f"  {updated_line}")
    print(f"  Length: {len(new_prompt)} characters")
    print()

    # Update database
    Session = init_database()
    session = Session()
    try:
        setting = session.query(SystemSetting).filter_by(key='ai_system_prompt').first()

        if setting:
            old_version = "Unknown"
            if setting.value:
                old_lines = setting.value.split('\n')
                old_version_line = next((l for l in old_lines if l.startswith('VERSION:')), None)
                if old_version_line:
                    old_version = old_version_line.replace('VERSION:', '').strip()

            print(f"Found existing prompt in database")
            print(f"  Current version: {old_version}")
            print(f"  Updating to new version...")

            setting.value = new_prompt
            print(f"✓ Updated prompt in database")
        else:
            print("No existing prompt found, creating new entry...")
            setting = SystemSetting(key='ai_system_prompt', value=new_prompt)
            session.add(setting)
            print(f"✓ Created new prompt in database")

        session.commit()
        print()
        print("=" * 60)
        print("✓ SUCCESS: Prompt updated in database")
        print("=" * 60)
        print()
        print("The AI will now use the updated prompt for all new tickets.")
        print("No service restart required - changes are effective immediately.")
        return True

    except Exception as e:
        print(f"❌ Error updating database: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = update_prompt_in_database()
    sys.exit(0 if success else 1)
