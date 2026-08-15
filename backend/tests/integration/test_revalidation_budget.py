import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.identity_revalidation_service import IdentityRevalidationService
from app.models.temporal import IdentityReviewItem
from app.models.identity_anchor import IdentityAnchor
from app.models.user import User
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = User(email=f"test_reval_{uuid.uuid4()}@example.com", hashed_password="pw")
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def test_review(db_session: AsyncSession, test_user: User):
    anchor = IdentityAnchor(user_id=test_user.id, status="active", version=1)
    db_session.add(anchor)
    await db_session.commit()

    from app.models.candidate_profile import CandidateProfile, CandidateDiscoveryRun
    from datetime import datetime, timezone

    run = CandidateDiscoveryRun(
        user_id=test_user.id,
        anchor_id=anchor.id,
        anchor_version=1,
        source_tool="test",
        source_tool_version="1.0"
    )
    db_session.add(run)
    await db_session.commit()

    cp = CandidateProfile(
        user_id=test_user.id,
        discovery_run_id=run.id,
        anchor_id=anchor.id,
        anchor_version=1,
        source_input_id=uuid.uuid4(),
        source_input_type="username",
        source_input_value_reference="test",
        platform="github",
        profile_url="https://github.com/test",
        canonical_profile_url="https://github.com/test",
        username_observed="test",
        source_tool="test",
        source_tool_version="1.0",
        first_observed_at=datetime.now(timezone.utc),
        last_observed_at=datetime.now(timezone.utc)
    )
    db_session.add(cp)
    await db_session.commit()

    review = IdentityReviewItem(
        user_id=test_user.id,
        anchor_id=anchor.id,
        candidate_profile_id=cp.id,
        priority="high",
        review_type="temporal_change",
        status="pending",
        reason_code="HIGH_MATERIALITY_CHANGE"
    )
    db_session.add(review)
    await db_session.commit()
    return review

@pytest.mark.asyncio
async def test_manual_revalidation_budget_enforced(db_session: AsyncSession, test_user: User, test_review: IdentityReviewItem):
    pipe_mock = MagicMock()
    # Mock execute() to be an async method that returns the list
    async def mock_execute():
        return [11, True, 11, True]
    pipe_mock.execute = mock_execute
    redis_client = AsyncMock()
    redis_client.pipeline = MagicMock(return_value=pipe_mock)
    
    service = IdentityRevalidationService(db_session, redis_client)
    
    with pytest.raises(ValueError, match="budget"):
        await service.request_revalidation_for_review(test_user.id, test_review.id, is_automatic=False)
