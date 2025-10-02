# Bug Fixes and Updates

## Version 1.0.1 - Configuration Type Conversion Fix

### Issue
When deploying to a server and loading configuration from `.env` file, Pydantic was receiving string values from environment variables but expecting specific types (integers for `deployment_phase`, floats for numeric values). This caused validation errors like:

```
Input should be 1, 2 or 3 [type=literal_error, input_value='1', input_type=str]
```

### Root Cause
- `python-dotenv` loads all environment variables as strings
- Pydantic 2.x with `Literal` types is strict about type matching
- The old `@validator` decorator syntax is deprecated in Pydantic 2.x
- No automatic type conversion was happening for string → int/float

### Changes Made

#### 1. Updated `config/settings.py`

**Changed imports:**
```python
# Old
from pydantic import Field, validator

# New
from pydantic import Field, field_validator
from typing import Literal, Union
```

**Changed deployment_phase type:**
```python
# Old
deployment_phase: Literal[1, 2, 3] = Field(...)

# New
deployment_phase: int = Field(...)

# Added validator
@field_validator('deployment_phase')
@classmethod
def validate_deployment_phase(cls, v: Union[str, int]) -> int:
    """Convert deployment phase to int and validate"""
    try:
        phase = int(v)
        if phase not in [1, 2, 3]:
            raise ValueError("Deployment phase must be 1, 2, or 3")
        return phase
    except (ValueError, TypeError):
        raise ValueError("Deployment phase must be 1, 2, or 3")
```

**Added integer field validator:**
```python
@field_validator('default_owner_id', 'supplier_reminder_hours', 'ai_max_tokens', 'email_poll_interval_seconds', mode='before')
@classmethod
def validate_integers(cls, v: Union[str, int]) -> int:
    """Convert string integers from env vars to int"""
    try:
        return int(v)
    except (ValueError, TypeError):
        raise ValueError(f"Must be a valid integer")
```

**Added float field validator:**
```python
@field_validator('ai_temperature', 'confidence_threshold', mode='before')
@classmethod
def validate_floats(cls, v: Union[str, float]) -> float:
    """Convert string floats from env vars to float"""
    try:
        return float(v)
    except (ValueError, TypeError):
        raise ValueError(f"Must be a valid number")
```

**Updated AI provider validator:**
```python
# Old
@validator('ai_provider')
def validate_ai_provider(cls, v, values):
    # ... validation logic ...

# New
@field_validator('ai_provider', mode='after')
@classmethod
def validate_ai_provider(cls, v: str, info) -> str:
    """Ensure appropriate API key is set for selected provider"""
    # Note: This validation is relaxed to allow initial setup
    # The AI engine will fail gracefully if keys are missing
    return v
```

**Added model config:**
```python
model_config = SettingsConfigDict(
    env_file='.env',
    env_file_encoding='utf-8',
    case_sensitive=False,
    validate_default=True  # NEW: Validate default values
)
```

#### 2. Created `test_config.py`
Added a configuration test script to verify settings load correctly with proper types.

#### 3. Updated `.env.example`
Added clarification about numeric values.

### Testing

Run the configuration test:
```bash
python test_config.py
```

Expected output:
```
✅ Configuration loaded successfully!

Current settings:
  AI Provider: openai
  AI Model: gpt-4
  Deployment Phase: 1 (type: int)
  Confidence Threshold: 0.75
  ...

✅ All type validations passed!
```

### Migration Guide

If you have an existing `.env` file, no changes are needed. The new validators automatically convert string values to the correct types.

Your `.env` can have values like this (all work now):
```env
DEPLOYMENT_PHASE=1          # Works
DEPLOYMENT_PHASE="1"        # Also works (quotes removed automatically)
AI_TEMPERATURE=0.7          # Works
CONFIDENCE_THRESHOLD=0.75   # Works
```

### Affected Files
- `config/settings.py` - Fixed type conversion and validation
- `.env.example` - Added clarifying comment
- `test_config.py` - NEW: Configuration test script

### Compatibility
- ✅ Pydantic 2.x (using new `field_validator` syntax)
- ✅ Python 3.11+
- ✅ python-dotenv
- ✅ Backwards compatible with existing `.env` files

### Additional Notes

#### Why Not Use Literal[1, 2, 3]?
Using `Literal[1, 2, 3]` with Pydantic and environment variables is problematic because:
1. Environment variables are always strings
2. Pydantic's Literal validator is strict about type matching
3. String "1" ≠ Integer 1 for Literal validation

The solution uses `int` with a custom validator that:
1. Accepts both string and int inputs
2. Converts to int
3. Validates the value is in [1, 2, 3]

#### Why Relax AI Provider Validation?
The original validator checked if API keys were set when selecting a provider. This was moved to the AI engine initialization because:
1. Allows configuration to load during setup
2. More graceful error messages
3. Doesn't block other components from working

### Future Improvements
- [ ] Add more comprehensive configuration validation
- [ ] Create integration tests for all settings
- [ ] Add runtime configuration hot-reload capability
- [ ] Better error messages with hints for fixing

### Deployment Checklist
When deploying this update to your server:

1. ✅ Pull latest code: `git pull`
2. ✅ No `.env` changes needed (existing values work)
3. ✅ Test configuration: `python test_config.py`
4. ✅ Restart service: `sudo systemctl restart ai-support-agent`
5. ✅ Verify logs: `tail -f logs/support_agent.log`

### Support
If you still encounter configuration errors:

1. Check Python version: `python --version` (should be 3.11+)
2. Verify dependencies: `pip install -r requirements.txt`
3. Test configuration: `python test_config.py`
4. Check .env syntax (no spaces around `=`)
5. Ensure numeric values have no quotes (or use single/double quotes consistently)

Example good `.env` entries:
```env
DEPLOYMENT_PHASE=1           ✅ Good
DEPLOYMENT_PHASE="1"         ✅ Good (auto-converted)
DEPLOYMENT_PHASE='1'         ✅ Good (auto-converted)
DEPLOYMENT_PHASE= 1          ❌ Bad (space before value)
DEPLOYMENT_PHASE=one         ❌ Bad (not a number)
```

---

**Version**: 1.0.1
**Date**: October 2, 2025
**Status**: ✅ Fixed and Tested
