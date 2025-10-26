#!/usr/bin/env python3
"""
Unit tests for SettingsHandler class.
Tests the settings handler structure and logic.
"""
import os
import sys

# Set required environment variables before importing
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["here_api_key"] = "test"
os.environ["event_id"] = ""
os.environ["dataupdate_id"] = "amzn1.ask.data.update"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["DYNAMODB_TABLE_NAME"] = "test-table"

def test_settings_handler_structure():
    """Test that SettingsHandler has the expected structure"""
    print("Testing SettingsHandler structure...")
    
    # Check storage/settings_handler.py for class definitions
    with open("storage/settings_handler.py", "r") as f:
        settings_content = f.read()
    
    # Check for SettingsHandler base class
    assert "class SettingsHandler(object):" in settings_content, "SettingsHandler class not found"
    print("✓ SettingsHandler base class exists")
    
    # Check for AlexaSettingsHandler implementation
    assert "class AlexaSettingsHandler(SettingsHandler):" in settings_content, "AlexaSettingsHandler class not found"
    print("✓ AlexaSettingsHandler class exists")
    
    with open("lambda_function.py", "r") as f:
        content = f.read()
    
    # Check for base class methods (with or without type hints)
    assert "def get_location(self)" in settings_content, "get_location method not found"
    assert "def set_location(self, location" in settings_content, "set_location method not found"
    assert "def get_rate(self)" in settings_content, "get_rate method not found"
    assert "def set_rate(self, rate" in settings_content, "set_rate method not found"
    assert "def get_pitch(self)" in settings_content, "get_pitch method not found"
    assert "def set_pitch(self, pitch" in settings_content, "set_pitch method not found"
    assert "def get_metrics(self)" in settings_content, "get_metrics method not found"
    assert "def set_metrics(self, metrics" in settings_content, "set_metrics method not found"
    print("✓ All settings handler methods defined")
    
    # Check that AlexaSettingsHandler uses attributes_manager
    assert "self.attr_mgr = handler_input.attributes_manager" in settings_content, "attributes_manager not used"
    assert "persistent_attrs = self.attr_mgr.persistent_attributes" in settings_content, "persistent_attributes not used"
    assert "self.attr_mgr.save_persistent_attributes()" in settings_content, "save_persistent_attributes not called"
    print("✓ AlexaSettingsHandler uses attributes_manager")
    
    # Check that Skill class accepts settings_handler
    assert "def __init__(self, handler_input, cache_handler=None, settings_handler=None):" in content, \
        "Skill doesn't accept settings_handler parameter"
    print("✓ Skill class accepts settings_handler parameter")
    
    # Check that Skill uses settings_handler
    assert "self.settings_handler = settings_handler" in content, "settings_handler not stored in Skill"
    assert "self.settings_handler.get_location()" in content, "settings_handler.get_location() not used"
    assert "self.settings_handler.set_location(" in content, "settings_handler.set_location() not used"
    assert "self.settings_handler.get_rate()" in content, "settings_handler.get_rate() not used"
    assert "self.settings_handler.set_rate(" in content, "settings_handler.set_rate() not used"
    assert "self.settings_handler.get_pitch()" in content, "settings_handler.get_pitch() not used"
    assert "self.settings_handler.set_pitch(" in content, "settings_handler.set_pitch() not used"
    assert "self.settings_handler.get_metrics()" in content, "settings_handler.get_metrics() not used"
    assert "self.settings_handler.set_metrics(" in content, "settings_handler.set_metrics() not used"
    print("✓ Skill uses settings_handler methods")
    
    # Check that BaseIntentHandler creates settings_handler
    assert "settings_handler = AlexaSettingsHandler(handler_input)" in content, \
        "BaseIntentHandler doesn't create settings_handler"
    assert ("Skill(handler_input, get_cache_handler(), settings_handler)" in content or
            "skill = Skill(handler_input," in content), \
        "settings_handler not passed to Skill"
    print("✓ BaseIntentHandler creates and passes settings_handler")
    
    # Check that old user settings methods are removed from Skill
    assert "_load_user_settings" not in content or "def _load_user_settings(self):" not in content, \
        "Old _load_user_settings method still exists in Skill"
    assert "_save_user_settings" not in content or "def _save_user_settings(self):" not in content, \
        "Old _save_user_settings method still exists in Skill"
    print("✓ Old user settings methods removed from Skill")
    
    print("\n✅ All SettingsHandler structure tests passed!")
    return True

def test_settings_separation():
    """Verify settings logic is separated from Skill class"""
    print("\nTesting settings separation from Skill class...")
    
    with open("lambda_function.py", "r") as f:
        content = f.read()
    
    # Verify Skill class no longer directly accesses persistent_attrs
    # (should only be in AlexaSettingsHandler)
    skill_class_start = content.find("class Skill(WeatherBase):")
    if skill_class_start == -1:
        skill_class_start = content.find("class Skill(Base):")
    skill_class_end = content.find("\nclass ", skill_class_start + 1)
    if skill_class_end == -1:
        skill_class_end = content.find("\n# ============================================================================", skill_class_start)
    skill_class_content = content[skill_class_start:skill_class_end]
    
    # Check that Skill doesn't directly manipulate persistent attributes
    assert "attr_mgr.persistent_attributes" not in skill_class_content, \
        "Skill class still directly accesses persistent_attributes"
    assert "save_persistent_attributes()" not in skill_class_content, \
        "Skill class still calls save_persistent_attributes()"
    print("✓ Skill class no longer directly accesses persistent attributes")
    
    # Check that properties delegate to settings_handler
    assert "self.settings_handler.get_location()" in skill_class_content, \
        "user_location property doesn't delegate to settings_handler"
    assert "self.settings_handler.set_location(" in skill_class_content, \
        "user_location setter doesn't delegate to settings_handler"
    print("✓ Skill properties delegate to settings_handler")
    
    print("\n✅ Settings separation tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_settings_handler_structure()
        test_settings_separation()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
