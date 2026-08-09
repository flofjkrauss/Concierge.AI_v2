"""Service for retrieving a booking."""
from uuid import uuid4

from database.interface import DatabaseInterface
from domain.entities.customer import Customer
from observability import LOG_MSG


def create_customer(
    first_name: str,
    last_name: str,
    email: str,
    preferred_language: str,
    database: DatabaseInterface,
    phone: str = ""
) -> Customer | None:
    """Create a new customer objekt and store it to database"""
    
    customer = database.identify_customer(first_name=first_name,
                                            last_name=last_name,
                                            email=email)
    if customer is None:
        if database.mail_is_in_use(email=email):
            LOG_MSG.error(f"Customer could not be created. Email {email} is already in use.")
            return None
        
        LOG_MSG.debug(f"Customer could not be identified: {first_name} {last_name} {email}")
        customer = Customer(
            customer_id=str(uuid4()),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            preferred_language=preferred_language
        )

        if customer is None:
            LOG_MSG.error(
                f"Customer {first_name} {last_name} with Email: {email} could not be created")
        else:
            database.save_customer(customer=customer)
            LOG_MSG.debug(
                f"Customer created: {customer.customer_id}, {customer.full_name}, {customer.email}"
            )
    LOG_MSG.debug(f"Customer identified: {first_name} {last_name} {email} {customer.customer_id}")
    return customer

def get_customer(customer_id: str, database: DatabaseInterface) -> Customer | None:
    return database.get_customer(customer_id=customer_id)