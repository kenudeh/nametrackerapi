from enum import Enum


# Enum for Tools type
class CategoryTypeChoices(Enum):
    CODE_GENERATORS = ('code_generators', 'Code_generators')
    IDES = ('ides', 'IDEs')
    DOCUMENTATION = ('documentation', 'Documentation')
    
    @classmethod
    def choices(cls):
        return [(choice.value[0], choice.value[1]) for choice in cls]
    


# Enum for ToolSuggestion
class ToolStatusChoices(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    @classmethod
    def choices(cls):
        return [(key.value, key.name.capitalize()) for key in cls ]
    
    
class SubscriptionTypeChoices(Enum):
    BASIC = 'basic'
    PREMIUM = 'premium'
    GOLD = 'gold'
    
    @classmethod
    def choices(cls):
        return [(key.value, key.name.capitalize()) for key in cls ]