from __future__ import annotations


class CompatibilityService:
    DEVICE_KEYS = {
        "iphone": "compat_iphone_text",
        "android": "compat_android_text",
        "not_sure": "compat_not_sure_text",
    }

    def get_text_key(self, device_type: str) -> str:
        return self.DEVICE_KEYS.get(device_type, "compat_not_sure_text")
