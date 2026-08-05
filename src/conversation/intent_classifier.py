"""try to determine user intent from chat messages"""
from conversation.entities.message import Message
from conversation.value_object.intent import Intent


class IntentClassifier:
    def determine(self, message: Message) -> Intent:
        """try to determine which user intent is behind the given message"""
        # place AI modules here
        # do some dark magic
        return Intent.AVAILABILITY_CHECK