import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from storage.base import Base

# Mock the database module before importing
with patch('storage.database.engine'), patch('storage.database.a_engine'):
    from storage.org import Org
    from storage.org_member import OrgMember
    from storage.org_service import OrgService
    from storage.role import Role
    from storage.user import User


@pytest.fixture
async def async_engine():
    """Create an async SQLite engine for testing."""
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        poolclass=StaticPool,
        connect_args={'check_same_thread': False},
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session_maker(async_engine):
    """Create an async session maker for testing."""
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_needs_onboarding_returns_false_when_user_has_personal_org(
    async_session_maker,
):
    """User with a personal org does not need onboarding."""
    user_id = uuid.uuid4()
    personal_org_name = f'user_{user_id}_org'

    async with async_session_maker() as session:
        # Create personal org
        org = Org(name=personal_org_name)
        session.add(org)
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=org.id)
        session.add(user)
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is False


@pytest.mark.asyncio
async def test_needs_onboarding_returns_false_when_user_has_active_membership(
    async_session_maker,
):
    """User with active org membership does not need onboarding."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create org (not a personal org)
        org = Org(name='company-org')
        session.add(org)
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=org.id)
        role = Role(name='member', rank=2)
        session.add_all([user, role])
        await session.flush()

        # Create active org membership
        org_member = OrgMember(
            org_id=org.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key',
            status='active',
        )
        session.add(org_member)
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is False


@pytest.mark.asyncio
async def test_needs_onboarding_returns_false_when_user_has_inactive_membership(
    async_session_maker,
):
    """User with inactive org membership does not need onboarding (not a new user)."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create org
        org = Org(name='company-org')
        session.add(org)
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=org.id)
        role = Role(name='member', rank=2)
        session.add_all([user, role])
        await session.flush()

        # Create inactive org membership
        org_member = OrgMember(
            org_id=org.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key',
            status='inactive',
        )
        session.add(org_member)
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is False


@pytest.mark.asyncio
async def test_needs_onboarding_returns_false_when_user_has_pending_invite(
    async_session_maker,
):
    """User with pending org invite does not need onboarding."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create org
        org = Org(name='company-org')
        session.add(org)
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=org.id)
        role = Role(name='member', rank=2)
        session.add_all([user, role])
        await session.flush()

        # Create pending org membership (invite)
        org_member = OrgMember(
            org_id=org.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key',
            status='pending',
        )
        session.add(org_member)
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is False


@pytest.mark.asyncio
async def test_needs_onboarding_returns_false_when_user_has_invited_status(
    async_session_maker,
):
    """User with 'invited' org membership status does not need onboarding."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create org
        org = Org(name='company-org')
        session.add(org)
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=org.id)
        role = Role(name='member', rank=2)
        session.add_all([user, role])
        await session.flush()

        # Create invited org membership
        org_member = OrgMember(
            org_id=org.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key',
            status='invited',
        )
        session.add(org_member)
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is False


@pytest.mark.asyncio
async def test_needs_onboarding_returns_false_when_user_has_null_status_membership(
    async_session_maker,
):
    """User with null status org membership does not need onboarding (has an account)."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create org
        org = Org(name='company-org')
        session.add(org)
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=org.id)
        role = Role(name='member', rank=2)
        session.add_all([user, role])
        await session.flush()

        # Create org membership with null status
        org_member = OrgMember(
            org_id=org.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key',
            status=None,
        )
        session.add(org_member)
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is False


@pytest.mark.asyncio
async def test_needs_onboarding_returns_true_when_user_is_new(async_session_maker):
    """New user with no personal org and no org membership needs onboarding."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create org that is NOT a personal org for this user
        org = Org(name='some-other-org')
        session.add(org)
        await session.flush()

        # Create user with no org memberships
        user = User(id=user_id, current_org_id=org.id)
        session.add(user)
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is True


@pytest.mark.asyncio
async def test_needs_onboarding_checks_personal_org_name_format(async_session_maker):
    """Verify that personal org check uses correct naming format."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create an org with a similar but incorrect name format
        # Using dashes instead of underscores
        wrong_name_org = Org(name=f'user-{user_id}-org')
        session.add(wrong_name_org)
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=wrong_name_org.id)
        session.add(user)
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            # Should return True because the org name doesn't match the expected format
            assert await OrgService.needs_onboarding(user) is True


@pytest.mark.asyncio
async def test_needs_onboarding_with_multiple_memberships(async_session_maker):
    """User with multiple memberships (any status) does not need onboarding."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create two orgs
        org1 = Org(name='company-org-1')
        org2 = Org(name='company-org-2')
        session.add_all([org1, org2])
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=org1.id)
        role = Role(name='member', rank=2)
        session.add_all([user, role])
        await session.flush()

        # Create one inactive and one active membership
        org_member1 = OrgMember(
            org_id=org1.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key-1',
            status='inactive',
        )
        org_member2 = OrgMember(
            org_id=org2.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key-2',
            status='active',
        )
        session.add_all([org_member1, org_member2])
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is False


@pytest.mark.asyncio
async def test_needs_onboarding_with_only_inactive_memberships(async_session_maker):
    """User with only inactive memberships does not need onboarding (not a new user)."""
    user_id = uuid.uuid4()

    async with async_session_maker() as session:
        # Create two orgs
        org1 = Org(name='company-org-1')
        org2 = Org(name='company-org-2')
        session.add_all([org1, org2])
        await session.flush()

        # Create user
        user = User(id=user_id, current_org_id=org1.id)
        role = Role(name='member', rank=2)
        session.add_all([user, role])
        await session.flush()

        # Create two inactive memberships
        org_member1 = OrgMember(
            org_id=org1.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key-1',
            status='inactive',
        )
        org_member2 = OrgMember(
            org_id=org2.id,
            user_id=user.id,
            role_id=role.id,
            llm_api_key='test-key-2',
            status='inactive',
        )
        session.add_all([org_member1, org_member2])
        await session.commit()

    with patch('storage.org_service.a_session_maker', async_session_maker):
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one()
            assert await OrgService.needs_onboarding(user) is False
