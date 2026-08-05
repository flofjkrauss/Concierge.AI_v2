"""extract informations from user messages"""
from datetime import date

from conversation.entities.information import Information
from conversation.entities.message import Message
from conversation.value_object.information_fields import InformationField


class InformationExtractor:
    def extract(self, message: Message) -> list[Information]:
        """try to extract information fields from given user message"""

        # TODO: apply module for intent extraction here
        # do some dark magic again

        # the following is just for testing and has to be remained later
        first_name = Information(
            information_field=InformationField.FIRST_NAME,
            content="Venom"
        )
        email = Information(
                    information_field=InformationField.EMAIL,
                    content="thedeadlyprotector@venom.all"
                )
        check_in = Information(
                    information_field=InformationField.CHECK_IN,
                    content=date(2026, 10, 10)
                )
        return [first_name, email, check_in]