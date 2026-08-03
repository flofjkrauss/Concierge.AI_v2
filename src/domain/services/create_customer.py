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
    database: DatabaseInterface
) -> Customer | None:
    """Create a new customer objekt and store it to database"""

    customer = Customer(
        customer_id=str(uuid4()),
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone="",
        preferred_language=preferred_language
    )

    if customer is None:
        LOG_MSG.debug(
            f"Customer {first_name} {last_name} with Email: {email} could not be created")
    else:
        database.save_customer(customer=customer)
        LOG_MSG.debug(
            f"Customer created: {customer.customer_id}, {customer.full_name}, {customer.email}"
        )

    return customer