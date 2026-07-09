import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActionResult:
    action_type: str
    target: str
    link: str
    message: str
    requires_user_confirmation: bool
    privacy_note: str


class ActionAgent:
    """
    Parses short voice instructions into privacy-preserving device actions.

    This agent does not store commands, contacts, phone numbers, messages, or
    browser history. It only returns links/intents for the current request.
    """

    def __init__(self):
        self.privacy_note = (
            "No command history, contact details, messages, or device data are "
            "stored by this API. The client should open the returned link only "
            "after the user confirms the action."
        )

    def handle_voice_command(
        self,
        command: str,
        phone_number: Optional[str] = None,
        message: Optional[str] = None,
        contact_name: Optional[str] = None,
    ) -> ActionResult:
        clean_command = self._normalize(command)

        if self._is_whatsapp_command(clean_command):
            number = phone_number or self._extract_phone_number(command)
            text = message or self._extract_message(command)
            return self._build_whatsapp_action(number, text, contact_name)

        if self._is_call_command(clean_command):
            number = phone_number or self._extract_phone_number(command)
            return self._build_call_action(number, contact_name)

        if self._is_browser_command(clean_command):
            target = self._extract_browser_target(command)
            return self._build_browser_action(target)

        raise ValueError(
            "I can handle browser, phone call, and WhatsApp chat commands. "
            "Try: 'open google.com', 'call +919876543210', or "
            "'WhatsApp +919876543210 saying I am on the way'."
        )

    def _build_browser_action(self, target: str) -> ActionResult:
        if not target:
            raise ValueError("Please include the website or search query to open.")

        target = target.strip()
        if self._looks_like_url(target):
            link = target if re.match(r"^https?://", target, re.I) else f"https://{target}"
        else:
            link = "https://www.google.com/search?q=" + urllib.parse.quote_plus(target)

        return ActionResult(
            action_type="open_browser",
            target=target,
            link=link,
            message=f"Ready to open: {target}",
            requires_user_confirmation=False,
            privacy_note=self.privacy_note,
        )

    def _build_call_action(
        self, phone_number: Optional[str], contact_name: Optional[str]
    ) -> ActionResult:
        if not phone_number:
            raise ValueError("Please provide a phone number for the call.")

        number = self._sanitize_phone_number(phone_number)
        return ActionResult(
            action_type="phone_call",
            target=contact_name or number,
            link=f"tel:{number}",
            message="Ready to open the dialer. Please confirm the call on your device.",
            requires_user_confirmation=True,
            privacy_note=self.privacy_note,
        )

    def _build_whatsapp_action(
        self,
        phone_number: Optional[str],
        message: Optional[str],
        contact_name: Optional[str],
    ) -> ActionResult:
        if not phone_number:
            raise ValueError("Please provide a WhatsApp phone number.")

        number = self._sanitize_phone_number(phone_number).lstrip("+")
        link = f"https://wa.me/{number}"
        if message:
            link += "?text=" + urllib.parse.quote(message.strip())

        return ActionResult(
            action_type="whatsapp_chat",
            target=contact_name or f"+{number}",
            link=link,
            message=(
                "Ready to open WhatsApp. Please review and send the message yourself."
                if message
                else "Ready to open WhatsApp chat."
            ),
            requires_user_confirmation=True,
            privacy_note=self.privacy_note,
        )

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip().lower()

    def _is_whatsapp_command(self, text: str) -> bool:
        return "whatsapp" in text or "whats app" in text or "chat on whatsapp" in text

    def _is_call_command(self, text: str) -> bool:
        return bool(re.search(r"\b(call|dial|phone)\b", text))

    def _is_browser_command(self, text: str) -> bool:
        return bool(re.search(r"\b(open|search|browse|go to|visit)\b", text))

    def _extract_browser_target(self, command: str) -> str:
        target = re.sub(
            r"^\s*(open|search for|search|browse|go to|visit)\s+",
            "",
            command,
            flags=re.I,
        )
        return target.strip()

    def _extract_phone_number(self, text: str) -> Optional[str]:
        match = re.search(r"(\+?\d[\d\s().-]{7,}\d)", text or "")
        return match.group(1) if match else None

    def _extract_message(self, text: str) -> Optional[str]:
        match = re.search(r"\b(?:saying|say|message|text)\b\s+(.+)$", text or "", re.I)
        return match.group(1).strip() if match else None

    def _sanitize_phone_number(self, phone_number: str) -> str:
        cleaned = re.sub(r"[^\d+]", "", phone_number or "")
        if not re.match(r"^\+?\d{8,15}$", cleaned):
            raise ValueError("Use an international phone number, for example +919876543210.")
        return cleaned

    def _looks_like_url(self, text: str) -> bool:
        return bool(re.match(r"^(https?://)?([a-z0-9-]+\.)+[a-z]{2,}(/.*)?$", text, re.I))
