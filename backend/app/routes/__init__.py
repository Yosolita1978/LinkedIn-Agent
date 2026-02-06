from app.routes.upload import router as upload_router
from app.routes.contacts import router as contacts_router
from app.routes.target_companies import router as target_companies_router
from app.routes.resurrection import router as resurrection_router
from app.routes.generate import router as generate_router
from app.routes.queue import router as queue_router

__all__ = ["upload_router", "contacts_router", "target_companies_router", "resurrection_router", "generate_router", "queue_router"]
