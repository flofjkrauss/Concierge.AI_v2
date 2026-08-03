from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_database
from database.interface import DatabaseInterface
from domain.services.get_information import get_information
from domain.value_objects.information_topic import InformationTopic
from observability.log_messages import LOG_MSG

router = APIRouter(
    prefix="/api/information",
    tags=["information"],
)


@router.get("/{topic}")
def read_topic(
    topic: str,
    database: Annotated[
        DatabaseInterface,
        Depends(get_database),
    ],
) -> str:
    try:
        normalized_topic = topic.lower().strip()
        if normalized_topic not in InformationTopic:
            LOG_MSG.debug("Illegal information request")
            raise ValueError(f"Topic requested: {topic}. No Information found for this topic.")
        
        return get_information(topic=InformationTopic(normalized_topic), database=database)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error)
        ) from error
