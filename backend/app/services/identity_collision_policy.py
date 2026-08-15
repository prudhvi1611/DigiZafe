import re

class IdentityCollisionPolicy:
    """
    Deterministic local heuristic for username collision risk.
    Does NOT use external API or global probability.
    """

    @classmethod
    def assess_collision_risk(cls, username: str) -> str:
        """
        Returns: 'high_collision', 'medium_collision', 'low_collision', or 'unknown'
        """
        if not username:
            return "unknown"
            
        username = username.lower()
        length = len(username)
        
        if length < 6:
            return "high_collision"
            
        # Check for simple patterns, e.g. lots of numbers at the end
        if re.search(r'\d{3,}', username):
            # JohnDoe1990 -> medium_collision
            # Let's say if it's very long, maybe low, but numbers make it slightly less distinct than a fully unique phrase.
            if length > 12:
                return "medium_collision"
            return "high_collision"
            
        # Check character diversity
        unique_chars = len(set(username))
        if unique_chars < 5:
            # e.g., aaaaaaa -> high collision
            return "high_collision"
            
        if length > 12:
            return "low_collision"
            
        return "medium_collision"

    @classmethod
    def get_username_evidence_cap(cls, collision_class: str) -> int:
        """
        Max score contribution for the entire 'username_observation' independence group.
        """
        if collision_class == "high_collision":
            return 20
        elif collision_class == "medium_collision":
            return 40
        elif collision_class == "low_collision":
            return 60
        else:
            return 20
