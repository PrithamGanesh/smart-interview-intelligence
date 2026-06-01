"""Base service layer with N+1 query prevention patterns."""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.database.models import Resume, JobDescription, MatchResult

logger = logging.getLogger(__name__)


class BaseService:
    """Base service with common database query patterns."""
    
    @staticmethod
    async def get_resumes_with_relations(
        session: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        tenant_id: Optional[str] = None,
    ) -> tuple[list[Resume], int]:
        """Get resumes with all relations pre-loaded (prevents N+1).
        
        Uses selectinload to fetch all relationships in 1-2 queries instead of N+1.
        
        Args:
            session: Async database session
            offset: Pagination offset
            limit: Pagination limit
            tenant_id: Optional tenant filter
            
        Returns:
            Tuple of (resumes, total_count)
        """
        try:
            # Build query with eager loading
            stmt = select(Resume).options(
                selectinload(Resume.tenant) if hasattr(Resume, 'tenant') else select(Resume),
                selectinload(Resume.match_results) if hasattr(Resume, 'match_results') else select(Resume),
            )
            
            # Filter by tenant if provided
            if tenant_id:
                stmt = stmt.where(Resume.tenant_id == tenant_id)
            
            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)
            
            # Execute query
            result = await session.execute(stmt)
            resumes = result.scalars().unique().all()
            
            # Get total count
            count_stmt = select(func.count(Resume.id))
            if tenant_id:
                count_stmt = count_stmt.where(Resume.tenant_id == tenant_id)
            
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0
            
            logger.debug(f"Fetched {len(resumes)} resumes, total: {total}")
            return resumes, total
            
        except Exception as e:
            logger.error(f"Error fetching resumes: {e}")
            raise
    
    
    @staticmethod
    async def get_jobs_with_relations(
        session: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        tenant_id: Optional[str] = None,
    ) -> tuple[list[JobDescription], int]:
        """Get jobs with all relations pre-loaded.
        
        Args:
            session: Async database session
            offset: Pagination offset
            limit: Pagination limit
            tenant_id: Optional tenant filter
            
        Returns:
            Tuple of (jobs, total_count)
        """
        try:
            # Build query with eager loading
            stmt = select(JobDescription).options(
                selectinload(JobDescription.tenant) if hasattr(JobDescription, 'tenant') else select(JobDescription),
                selectinload(JobDescription.match_results) if hasattr(JobDescription, 'match_results') else select(JobDescription),
            )
            
            # Filter by tenant
            if tenant_id:
                stmt = stmt.where(JobDescription.tenant_id == tenant_id)
            
            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)
            
            # Execute
            result = await session.execute(stmt)
            jobs = result.scalars().unique().all()
            
            # Get total count
            count_stmt = select(func.count(JobDescription.id))
            if tenant_id:
                count_stmt = count_stmt.where(JobDescription.tenant_id == tenant_id)
            
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0
            
            logger.debug(f"Fetched {len(jobs)} jobs, total: {total}")
            return jobs, total
            
        except Exception as e:
            logger.error(f"Error fetching jobs: {e}")
            raise
    
    
    @staticmethod
    async def get_match_results_for_job(
        session: AsyncSession,
        job_id: str,
        offset: int = 0,
        limit: int = 100,
        min_score: Optional[float] = None,
    ) -> tuple[list[MatchResult], int]:
        """Get ranked match results for a job (eager-loaded).
        
        Args:
            session: Async database session
            job_id: Job ID to get matches for
            offset: Pagination offset
            limit: Pagination limit
            min_score: Minimum score filter
            
        Returns:
            Tuple of (matches, total_count)
        """
        try:
            # Build query with eager loading
            stmt = select(MatchResult).where(
                MatchResult.job_id == job_id
            ).options(
                selectinload(MatchResult.resume) if hasattr(MatchResult, 'resume') else select(MatchResult),
                selectinload(MatchResult.job) if hasattr(MatchResult, 'job') else select(MatchResult),
            )
            
            # Filter by minimum score
            if min_score is not None:
                stmt = stmt.where(MatchResult.fit_score >= min_score)
            
            # Order by score descending
            stmt = stmt.order_by(MatchResult.fit_score.desc())
            
            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)
            
            # Execute
            result = await session.execute(stmt)
            matches = result.scalars().unique().all()
            
            # Get total count
            count_stmt = select(func.count(MatchResult.id)).where(
                MatchResult.job_id == job_id
            )
            if min_score is not None:
                count_stmt = count_stmt.where(MatchResult.fit_score >= min_score)
            
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0
            
            logger.debug(f"Fetched {len(matches)} matches for job {job_id}, total: {total}")
            return matches, total
            
        except Exception as e:
            logger.error(f"Error fetching match results: {e}")
            raise
