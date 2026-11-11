from app.routes.upload import router as upload_router
from app.routes.contacts import router as contacts_router
from app.routes.target_companies import router as target_companies_router
from app.routes.resurrection import router as resurrection_router
from app.routes.generate import router as generate_router
from app.routes.queue import router as queue_router
from app.routes.ranking import router as ranking_router
from app.routes.followers import router as followers_router
from app.routes.analytics import router as analytics_router
from app.routes.auth import router as auth_router
from app.routes.inbox import router as inbox_router
from app.routes.settings import router as settings_router
from app.routes.jobs import router as jobs_router
from app.routes.posts import router as posts_router
from app.routes.follow_ups import router as follow_ups_router

__all__ = ["upload_router", "contacts_router", "target_companies_router", "resurrection_router", "generate_router", "queue_router", "ranking_router", "followers_router", "analytics_router", "auth_router", "inbox_router", "settings_router", "jobs_router", "posts_router", "follow_ups_router"]
