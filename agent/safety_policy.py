import re

class SafetyPolicy:
    """
    ResearchMind Safety Policy.
    Filters harmful, illegal, or restricted content.
    """
    def __init__(self):
        # Restricted keywords and patterns
        self.restricted_patterns = [
            r"bomb\s*making",
            r"weapon\s*construction",
            r"malware\s*creation",
            r"child\s*exploitation",
            r"terrorism",
            r"how\s*to\s*kill",
            r"illegal\s*drugs",
            r"hacking\s*into",
            r"explicit\s*content"
        ]
        
    def is_safe(self, text):
        """Check if the text (query or response) is safe."""
        for pattern in self.restricted_patterns:
            if re.search(pattern, text.lower()):
                return False
        return True

    def get_refusal_message(self):
        """Standard refusal message for unsafe content."""
        return ("I cannot assist with that request. As an AI research assistant, "
                "I must follow safety guidelines that prohibit generating or researching "
                "harmful, illegal, or explicit content. I am here to help with "
                "educational and general-purpose research.")

if __name__ == "__main__":
    # Quick test
    safety = SafetyPolicy()
    print(f"Is 'How to build a bomb' safe? {safety.is_safe('How to build a bomb')}")
    print(f"Is 'How to build a transformer' safe? {safety.is_safe('How to build a transformer')}")
